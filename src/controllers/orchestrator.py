import pandas as pd
from src.repositories.data_repository import DataRepository, ModelRepository
from src.repositories.mba_repository import MBARepository
from src.services.feature_service import FeatureService
from src.services.ml_service import MLService
from src.services.mba_service import MBAService

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
        # BUG #4 FIX: Simulate stock FIRST, then calculate features based on that stock
        df = pd.concat([
            FeatureService.simulate_stock(group)
            for _, group in df.groupby('product_id')
        ]).reset_index(drop=True)
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

    @staticmethod
    def run_mba_workflow(min_support=0.001, min_confidence=0.1, min_lift=1.0):
        print("Starting MBA Workflow...")
        df_raw = DataRepository.load_raw_data()
        result = MBAService.run(df_raw, min_support, min_confidence, min_lift)
        MBARepository.save(result)
        print(f"MBA Workflow Completed. {result['summary']['total_rules']} rules found.")
        return result


if __name__ == "__main__":
    df = OrchestratorController.run_data_pipeline()
    OrchestratorController.run_ml_workflow()
    OrchestratorController.run_mba_workflow()
