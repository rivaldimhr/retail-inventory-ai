import os

class Config:
    ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    DATA_DIR = os.path.join(ROOT_DIR, "data")
    
    RAW_DATA_PATH = os.path.join(DATA_DIR, "Groceries_dataset.csv")
    PROCESSED_DATA_PATH = os.path.join(DATA_DIR, "processed_features.csv")
    MODEL_PATH = os.path.join(DATA_DIR, "demand_model.pkl")
    FORECAST_PATH = os.path.join(DATA_DIR, "forecast_results.json")

config = Config()
