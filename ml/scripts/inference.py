# Reload and run the recommended (Chronos-2, zero-shot) forecasting model.

# Usage:
#     from chronos import Chronos2Pipeline
#     import torch, json, pandas as pd

#     config = json.load(open("config.json"))
#     pipe = Chronos2Pipeline.from_pretrained(config["pretrained_id"], device_map="cuda", dtype=torch.bfloat16)

#     # history: DataFrame with columns item_id, timestamp, target (units_sold),
#     # trimmed to the last config["context_window_days"] days per product.
#     forecast = pipe.predict_df(
#         history, prediction_length=config["forecast_horizon_days"], batch_size=256,
#         id_column="item_id", timestamp_column="timestamp", target="target",
#     )
#     # forecast["predictions"] is the point forecast; combine with current_stock
#     # via cumulative sum (see notebooks/retail_sales_forecasting_stockout.ipynb, Phase 11)
#     # to get the estimated stock-out date.
