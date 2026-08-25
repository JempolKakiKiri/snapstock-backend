import joblib
import sys
import os
import json
import pandas as pd
from statsforecast import StatsForecast

def main():
    if len(sys.argv) < 2:
        print(json.dumps({"status": "error", "message": "Missing input data"}))
        sys.exit(1)

    try:
        input_data = json.loads(sys.argv[1])
        history = input_data.get('history', [])
        current_stock = input_data.get('current_stock', 0)
        
        if not history:
            print(json.dumps({"status": "error", "message": "History is empty"}))
            return
            
        df = pd.DataFrame(history)
        df['ds'] = pd.to_datetime(df['date']).dt.normalize()
        df['y'] = df['qty'].astype(float)
        
        # Resample to daily to fill missing dates with 0 (krusial untuk TSB intermittent demand)
        df = df.groupby('ds')['y'].sum().reset_index()
        # Ensure contiguous date range
        full_idx = pd.date_range(df['ds'].min(), df['ds'].max())
        df = df.set_index('ds').reindex(full_idx, fill_value=0).reset_index()
        df.columns = ['ds', 'y']
        df['unique_id'] = 'item' # Wajib untuk StatsForecast
        
        # Load the TSB model parameters

        model_path = os.path.join(os.path.dirname(__file__), "final_model_TSB.joblib")
        model_dict = joblib.load(model_path)
        tsb_model = model_dict['model']
        
        # Initialize StatsForecast wrapper
        sf = StatsForecast(
            models=[tsb_model],
            freq='D',
            n_jobs=1
        )
        
        # Predict next 90 days
        forecast = sf.forecast(h=90, df=df)
        
        # Accumulate forecasted daily demand until stock runs out
        preds = forecast['TSB'].values
        runout_days = None
        cumulative_demand = 0
        
        for i, demand in enumerate(preds):
            cumulative_demand += max(0, demand) # Abaikan hasil prediksi negatif (jika ada)
            if cumulative_demand >= current_stock:
                runout_days = i + 1
                break
                
        # Jika dalam 90 hari stok belum habis
        if runout_days is None:
            runout_days = ">90"

        print(json.dumps({
            "status": "success",
            "runout_days": runout_days
        }))
        
    except Exception as e:
        print(json.dumps({"status": "error", "message": str(e)}))

if __name__ == "__main__":
    main()
