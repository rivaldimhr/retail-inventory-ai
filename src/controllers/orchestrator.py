import pandas as pd
from src.repositories.data_repository import DataRepository, ModelRepository
from src.data_pipeline.pipeline import clean_and_reindex
from src.data_pipeline.features import simulate_stock, calculate_rolling_features, add_calendar_features
from src.services.ml_service import MLService

class OrchestratorController:
    """
    Controller utama yang mengatur alur kerja dari data mentah hingga prediksi.
    Menerapkan pola MVC/SLR untuk skalabilitas.
    """
    
    @staticmethod
    def run_data_pipeline():
        print("Starting Data Pipeline...")
        
        # Load
        df_raw = DataRepository.load_raw_data()
        
        # Preprocess + Reindex (digabung ke clean_and_reindex)
        df = clean_and_reindex(df_raw)
        
        # Simulate stock FIRST, then calculate features based on that stock
        df = df.groupby('product_id', group_keys=False).apply(simulate_stock)
        df = calculate_rolling_features(df)
        df = add_calendar_features(df)
        
        # Save
        DataRepository.save_processed_data(df)
        print("Data Pipeline Completed.")
        return df

    @staticmethod
    def run_ml_workflow():
        print("Starting ML Workflow...")
        
        # Load
        df = DataRepository.load_processed_data()
        
        # Train
        model = MLService.train(df)
        ModelRepository.save_model(model)
        
        # Predict
        forecast = MLService.predict_latest(df, model)
        ModelRepository.save_forecast(forecast)
        
        print("ML Workflow Completed.")
        return forecast

if __name__ == "__main__":
    df = OrchestratorController.run_data_pipeline()
    OrchestratorController.run_ml_workflow()