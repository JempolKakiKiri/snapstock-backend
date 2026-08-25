import joblib
import sys

def inspect_model(filepath):
    try:
        print(f"Loading model from: {filepath}")
        model = joblib.load(filepath)
        print(f"Model Type: {type(model)}")

        # Check for feature names in LightGBM booster or sklearn pipeline/estimator
        if hasattr(model, 'feature_name_'):
            features = model.feature_name_() if callable(model.feature_name_) else model.feature_name_
            print("\nFound features via 'feature_name_':")
            print(features)
        elif hasattr(model, 'feature_names_in_'):
            print("\nFound features via 'feature_names_in_':")
            print(model.feature_names_in_)
        else:
            print("\nCould not automatically determine feature names from the model object.")
            print("Available attributes:")
            print([attr for attr in dir(model) if not attr.startswith('_')])
            
    except Exception as e:
        print(f"Error: {e}")
        print("Pastikan package 'joblib', 'scikit-learn', dan 'lightgbm' sudah terinstal.")

if __name__ == "__main__":
    inspect_model("ml/scripts/best_trainable_model_lightgbm.joblib")
