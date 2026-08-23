import joblib
import sys
import json
import pandas as pd

def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Tolong berikan data fitur dalam format JSON string sebagai argumen."}))
        sys.exit(1)

    try:
        input_data = json.loads(sys.argv[1])
        
        model_dict = joblib.load("ml/scripts/best_trainable_model_lightgbm.joblib")
        model = model_dict['model']
        feature_cols = model_dict['feature_cols']
        df = pd.DataFrame([input_data])
        
        
        try:
            X = df[feature_cols]
        except KeyError as e:
            missing = set(feature_cols) - set(df.columns)
            print(json.dumps({"error": f"Fitur tidak lengkap. Kehilangan kolom: {list(missing)}"}))
            sys.exit(1)

        
        prediction = model.predict(X)
        
        result = {
            "status": "success",
            "prediction": float(prediction[0]),
            "trained_through": str(model_dict.get('trained_through', 'N/A'))
        }
        print(json.dumps(result))

    except Exception as e:
        print(json.dumps({"error": str(e)}))
        sys.exit(1)

if __name__ == "__main__":
    main()
