"""
Calibrate TSB's smoothing parameters against warung demand, and measure what
the calibration is worth in days of runout error.

The shipped model is TSB(alpha_d=0.2, alpha_p=0.2), chosen on an M5 backtest --
US supermarket data. This asks the question that matters for the product: on
Indonesian warung demand, is 0.2/0.2 the right pair, and how much does getting
it wrong cost the shopkeeper?

Two metrics, deliberately:

    MASE / RMSSE   forecast error, scaled by in-sample naive error. The usual
                   answer, and the one that is comparable across series with
                   wildly different volumes.
    runout MAE     how many days out the stock-out date is. This is what the
                   dashboard actually shows, and a model can win on MASE while
                   losing here -- cumulative demand forgives errors that cancel.

Rolling-origin backtest, never a random split: forecasting is evaluated by
predicting a future that the fit has not seen.

    python tune_tsb.py            # full grid, writes results/tsb_grid.csv
    python tune_tsb.py --quick    # coarse grid, for a smoke test

Needs only statsforecast, pandas, numpy -- the same venv the inference script
uses. No GPU, no download.
"""

from __future__ import annotations

import argparse
import collections
import json
import math
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
from statsforecast import StatsForecast
from statsforecast.models import TSB, CrostonSBA, SeasonalNaive

# ── the shop ────────────────────────────────────────────────────────────────
# Demand archetypes and seasonality are the generator from the research
# notebook, reproduced here so this script stands alone in the delivered repo.

SEED, DAYS, HORIZON, N_FOLDS, LEAD = 42, 180, 14, 3, 3

# Forecast error is scored over HORIZON (supplier lead time + review period --
# the window a restock decision actually spans). The runout date is scored over
# a longer window, because a shelf stocked for three weeks does not empty inside
# two: scored at 14 days most SKUs simply survive the horizon, and the metric
# would measure the horizon rather than the model.
RUNOUT_HORIZON = 45

ARCHETYPES = {
    'fast':         dict(p_sell=0.97, r=9.0, p=0.55),
    'steady':       dict(p_sell=0.78, r=4.0, p=0.55),
    'intermittent': dict(p_sell=0.34, r=2.5, p=0.60),
    'lumpy':        dict(p_sell=0.22, r=1.1, p=0.28),
    'slow':         dict(p_sell=0.07, r=1.5, p=0.70),
}

WEEKDAY_MULT = [1.00, 1.00, 1.02, 1.05, 1.15, 1.35, 1.28]   # Mon..Sun

# How many SKUs of each archetype. Proportions follow the warung catalogue in
# the research notebook rather than being drawn evenly -- an even split would
# over-represent fast movers and flatter every method.
MIX = {'fast': 20, 'steady': 40, 'intermittent': 60, 'lumpy': 50, 'slow': 30}


def payday_mult(day_of_month: int) -> float:
    """Indonesian gajian clusters at month end and the first days after."""
    return 1.30 if (day_of_month >= 25 or day_of_month <= 2) else 1.0


def generate_demand(days=DAYS, seed=SEED):
    """True demand -- what customers wanted, which a shop never records."""
    rng = np.random.default_rng(seed)
    start = date(2025, 1, 1)
    catalogue = [(f'{arch}_{i}', arch)
                 for arch, n in MIX.items() for i in range(n)]

    rows = []
    for sku, arch in catalogue:
        cfg = ARCHETYPES[arch]
        for offset in range(days):
            day = start + timedelta(days=offset)
            season = WEEKDAY_MULT[day.weekday()] * payday_mult(day.day)
            if rng.random() > min(cfg['p_sell'] * season, 0.99):
                continue
            qty = int(round(rng.negative_binomial(cfg['r'], cfg['p']) * season))
            if qty > 0:
                rows.append({'ds': day, 'unique_id': sku,
                             'archetype': arch, 'demand': qty})
    return pd.DataFrame(rows), catalogue, start


def simulate_shop(demand, catalogue, start, days=DAYS, seed=SEED, review_days=21):
    """
    Turn demand into what a shop's records would actually contain.

    A shop records what it *sold*, capped by what was on the shelf. When stock
    hits zero it records a sale of zero -- not the demand it could not serve.
    We forecast on `sold` because that is what a deployed system can observe,
    and the censoring is part of the problem, not something to wish away.
    """
    rng = np.random.default_rng(seed)
    lookup = collections.defaultdict(dict)
    for r in demand.itertuples():
        lookup[r.unique_id][r.ds] = r.demand

    span = [start + timedelta(days=i) for i in range(days)]
    ledger = []
    for sku, arch in catalogue:
        series = lookup.get(sku, {})
        mean_daily = sum(series.values()) / days
        lead = int(rng.integers(1, LEAD + 2))
        reorder = max(1, math.ceil(mean_daily * (lead + 4)))
        order_up_to = max(2, math.ceil(mean_daily * review_days))
        on_hand, incoming = order_up_to, collections.Counter()

        for day in span:
            on_hand += incoming.pop(day, 0)
            want = series.get(day, 0)
            sold = min(want, on_hand)
            on_hand -= sold
            if on_hand <= reorder and not incoming:
                incoming[day + timedelta(days=lead)] += max(1, order_up_to - on_hand)
            ledger.append({'unique_id': sku, 'ds': day, 'archetype': arch,
                           'y': sold, 'demand': want, 'closing': on_hand})
    return pd.DataFrame(ledger)


# ── metrics ─────────────────────────────────────────────────────────────────

def naive_scale(train: pd.DataFrame) -> dict:
    """In-sample naive MAE per series -- the MASE/RMSSE denominator.

    Not MAPE: it divides by actual demand, and these series are mostly zeros.
    """
    scale = {}
    for uid, g in train.groupby('unique_id'):
        d = np.abs(np.diff(g.sort_values('ds').y.values))
        scale[uid] = d.mean() if len(d) and d.mean() > 0 else 1.0
    return scale


def runout_day(daily, stock: float) -> float | None:
    """First day on which cumulative demand consumes the stock on hand."""
    total = 0.0
    for i, q in enumerate(daily, start=1):
        total += max(0.0, float(q))
        if total >= stock:
            return i
    return None            # survives the whole horizon


def score(fc: pd.DataFrame, actual: pd.DataFrame, column: str,
          scale: dict, stock: dict, cutoff) -> dict:
    """Forecast error and runout error for one model, over one fold.

    The two are scored on different windows on purpose -- see RUNOUT_HORIZON.
    """
    merged = fc.merge(actual, on=['unique_id', 'ds'], how='inner')
    error_window = merged[merged.ds <= cutoff + pd.Timedelta(f'{HORIZON}D')]

    abs_err, sq_err, runout_err, missed = [], [], [], 0
    for uid, g in merged.groupby('unique_id'):
        g = g.sort_values('ds')
        s = scale.get(uid, 1.0)

        window = g[g.ds <= cutoff + pd.Timedelta(f'{HORIZON}D')]
        err = window[column].values - window['y'].values
        if len(err):
            abs_err.append(np.abs(err).mean() / s)
            sq_err.append((err ** 2).mean() / (s ** 2))

        on_hand = stock.get(uid)
        if on_hand is None or on_hand <= 0:
            continue
        truth = runout_day(g['y'].values, on_hand)
        if truth is None:
            continue        # the shelf survives the window; nothing to date
        predicted = runout_day(g[column].values, on_hand)
        if predicted is None:
            # The model says this SKU never runs out, and it does. That is a
            # real miss, not a missing value -- charged at the window edge
            # rather than quietly dropped, which would reward the timid.
            missed += 1
            runout_err.append(RUNOUT_HORIZON - truth)
            continue
        runout_err.append(abs(predicted - truth))

    return {
        'MASE': float(np.mean(abs_err)),
        'RMSSE': float(np.sqrt(np.mean(sq_err))),
        'WAPE': float(np.abs(error_window[column] - error_window['y']).sum()
                      / max(error_window['y'].sum(), 1e-9)),
        'runout_MAE_days': float(np.mean(runout_err)) if runout_err else float('nan'),
        'runout_n': len(runout_err),
        'runout_missed': missed,
    }


# ── the experiment ──────────────────────────────────────────────────────────

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--quick', action='store_true', help='coarse grid')
    ap.add_argument('--seeds', type=int, default=3,
                    help='independent shops to average over')
    ap.add_argument('--out', default='results', help='output directory')
    args = ap.parse_args()

    grid = ([0.1, 0.2, 0.4] if args.quick
            else [0.05, 0.1, 0.15, 0.2, 0.3, 0.4, 0.5])

    models = [TSB(alpha_d=d, alpha_p=p, alias=f'TSB_{d}_{p}')
              for d in grid for p in grid]
    models += [CrostonSBA(alias='CrostonSBA'), SeasonalNaive(season_length=7)]
    print(f'{len(models)} models x {N_FOLDS} rolling-origin folds x '
          f'{args.seeds} seeds (error horizon {HORIZON}d, '
          f'runout horizon {RUNOUT_HORIZON}d)\n')

    records = []
    # Several independent shops, not one. On a single draw the top of this grid
    # separates by less than a thousandth of a MASE point, which is noise; a
    # ranking that survives independent shops is a finding, one that does not
    # is an artefact of the generator's seed.
    for seed in range(SEED, SEED + args.seeds):
        demand, catalogue, start = generate_demand(seed=seed)
        ledger = simulate_shop(demand, catalogue, start, seed=seed)
        lost = (ledger.demand - ledger.y).sum()
        print(f'seed {seed}: {len(demand):,} demand lines | fill rate '
              f'{1 - lost / ledger.demand.sum():.1%}')

        panel = ledger[['unique_id', 'ds', 'y']].copy()
        panel['ds'] = pd.to_datetime(panel['ds'])
        last = panel.ds.max()

        for fold in range(N_FOLDS):
            # Origins step back by the error horizon; the last origin still
            # leaves a full RUNOUT_HORIZON of unseen data to date against.
            back = RUNOUT_HORIZON + HORIZON * (N_FOLDS - 1 - fold)
            cutoff = last - pd.Timedelta(f'{back}D')
            train = panel[panel.ds <= cutoff]
            actual = panel[(panel.ds > cutoff) &
                           (panel.ds <= cutoff + pd.Timedelta(f'{RUNOUT_HORIZON}D'))]

            # Stock on hand at the origin, from the shop's own ledger -- the
            # same number the dashboard passes to the model in production.
            at_cutoff = ledger[pd.to_datetime(ledger.ds) == cutoff]
            stock = dict(zip(at_cutoff.unique_id, at_cutoff.closing))

            sf = StatsForecast(models=models, freq='D', n_jobs=-1)
            fc = sf.forecast(df=train, h=RUNOUT_HORIZON).reset_index()
            scale = naive_scale(train)

            for m in models:
                row = score(fc[['unique_id', 'ds', m.alias]], actual,
                            m.alias, scale, stock, cutoff)
                row.update(model=m.alias, fold=fold + 1, seed=seed,
                           cutoff=str(cutoff.date()))
                records.append(row)
            print(f'  fold {fold + 1}/{N_FOLDS}  origin {cutoff.date()}  done')

    df = pd.DataFrame(records)
    agg = (df.groupby('model')[['MASE', 'RMSSE', 'WAPE', 'runout_MAE_days']]
             .mean().sort_values('MASE'))

    # How often each model tops the grid, seed by seed. A parameter pair that
    # wins on the mean but never wins a seed has not really won anything.
    wins = (df.groupby(['seed', 'model']).MASE.mean()
              .groupby('seed').idxmin().map(lambda t: t[1])
              .value_counts())
    agg['seeds_won'] = agg.index.map(wins).fillna(0).astype(int)

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    df.to_csv(out / 'tsb_grid_per_fold.csv', index=False)
    agg.to_csv(out / 'tsb_grid.csv')

    shipped = 'TSB_0.2_0.2'
    best = agg.index[0]
    print(f'\n=== TSB parameter grid, mean over {args.seeds} seeds x '
          f'{N_FOLDS} folds x {sum(MIX.values())} SKUs ===')
    print(agg.head(15).round(4).to_string())
    if len(agg) > 15:
        print(f'... {len(agg) - 15} more rows in {out / "tsb_grid.csv"}')
    print(f'\nbest by MASE:      {best}')
    print(f'shipped default:   {shipped}')
    if shipped in agg.index:
        d = agg.loc[shipped, 'MASE'] - agg.loc[best, 'MASE']
        print(f'gap:               {d:+.4f} MASE '
              f'({d / agg.loc[shipped, "MASE"]:+.1%} relative)')
        print(f'runout MAE:        shipped {agg.loc[shipped, "runout_MAE_days"]:.2f} d '
              f'vs best {agg.loc[best, "runout_MAE_days"]:.2f} d')

    best_runout = agg['runout_MAE_days'].idxmin()
    print(f'best by runout MAE: {best_runout} '
          f'({agg.loc[best_runout, "runout_MAE_days"]:.2f} days)')
    if best_runout != best:
        print('  note: the two metrics disagree -- lowest forecast error is not '
              'the lowest runout error. Report both.')

    (out / 'tsb_grid_summary.json').write_text(json.dumps({
        'seed': SEED, 'skus': sum(MIX.values()), 'days': DAYS,
        'horizon_days': HORIZON, 'folds': N_FOLDS, 'grid': grid,
        'best_by_mase': best, 'best_by_runout_mae': best_runout,
        'shipped': shipped,
        'results': agg.round(6).to_dict(orient='index'),
    }, indent=2))
    print(f'\nwrote {out / "tsb_grid.csv"} and {out / "tsb_grid_summary.json"}')


if __name__ == '__main__':
    main()
