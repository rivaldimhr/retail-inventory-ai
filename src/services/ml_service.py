import pandas as pd
import xgboost as xgb
from datetime import datetime

class MLService:
    FEATURE_COLS = ['day_of_week', 'is_weekend', 'is_holiday', 'avg_sales_7d', 'avg_sales_30d', 'sales_trend_7d', 'stock_qty']
    TARGET_COL = 'units_sold'

    @staticmethod
    def train(df):
        X = df[MLService.FEATURE_COLS]
        y = df[MLService.TARGET_COL]
        model = xgb.XGBRegressor(n_estimators=100, learning_rate=0.1, max_depth=5)
        model.fit(X, y)
        return model

    @staticmethod
    def predict_latest(df, model):
        latest_data = df.sort_values('date').groupby('product_id').tail(1)
        predictions = []
        
        for _, row in latest_data.iterrows():
            X_input = pd.DataFrame([row[MLService.FEATURE_COLS]])
            forecast_val = float(model.predict(X_input)[0])
            
            trend = "STABLE"
            if row['sales_trend_7d'] > 0.01: trend = "INCREASING"
            elif row['sales_trend_7d'] < -0.01: trend = "DECREASING"

            predictions.append({
                "product_id": row['product_id'],
                "store_id": row['store_id'],
                "category": row['category'],
                "current_stock": int(row['stock_qty']),
                "avg_daily_demand_forecast": round(forecast_val, 2),
                "stock_coverage_days": round(row['stock_coverage'], 1),
                "trend_direction": trend,
                "risk_flags": {
                    "stockout_risk": bool(row['stock_coverage'] < row['lead_time_days']),
                    "overstock_risk": bool(row['stock_coverage'] > 30)
                }
            })
        
        return {
            "generated_at": datetime.now().isoformat(),
            "predictions": predictions
        }
