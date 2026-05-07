import pandas as pd
import json
import pickle
import os
import time
from src.config.config import config

class DataRepository:
# ... (rest of DataRepository)
    @staticmethod
    def load_raw_data():
        return pd.read_csv(config.RAW_DATA_PATH)

    @staticmethod
    def save_processed_data(df):
        df.to_csv(config.PROCESSED_DATA_PATH, index=False)

    @staticmethod
    def load_processed_data():
        return pd.read_csv(config.PROCESSED_DATA_PATH)

class ModelRepository:
    @staticmethod
    def save_model(model_obj):
        with open(config.MODEL_PATH, 'wb') as f:
            pickle.dump(model_obj, f)

    @staticmethod
    def load_model():
        with open(config.MODEL_PATH, 'rb') as f:
            return pickle.load(f)

    @staticmethod
    def save_forecast(forecast_data):
        with open(config.FORECAST_PATH, 'w') as f:
            json.dump(forecast_data, f, indent=2)

    @staticmethod
    def load_forecast():
        if not os.path.exists(config.FORECAST_PATH):
            return None
            
        # Timestamp Check: Cegah data stale > 24 jam
        file_age_hours = (time.time() - os.path.getmtime(config.FORECAST_PATH)) / 3600
        if file_age_hours > 24:
            # Data dianggap usang, perlu rerun pipeline
            return {"error": "Forecast data outdated", "age_hours": round(file_age_hours, 1)}

        with open(config.FORECAST_PATH, 'r') as f:
            return json.load(f)
