import pandas as pd
from src.repositories.data_repository import DataRepository, ModelRepository
from src.services.feature_service import FeatureService
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
        
        # Preprocess
        df_raw['Date'] = pd.to_datetime(df_raw['Date'], format='%d-%m-%Y')
        df = df_raw.groupby(['Date', 'itemDescription']).size().reset_index(name='units_sold')
        df.columns = ['date', 'product_id', 'units_sold']
        
        # Initial Enrichment
        df['store_id'] = 'STR-001'
        df['category'] = 'General'
        df['supplier_id'] = 'SUPP-001'
        df['lead_time_days'] = 3
        
        # Services
        df = FeatureService.reindex_to_daily(df)
        df = df.groupby('product_id', group_keys=False).apply(FeatureService.simulate_stock)
        df = FeatureService.calculate_rolling_features(df)
        df = FeatureService.add_calendar_features(df)
        
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
    # Script entrypoint sederhana untuk testing controller
    df = OrchestratorController.run_data_pipeline()
    OrchestratorController.run_ml_workflow()
