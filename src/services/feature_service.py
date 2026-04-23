import pandas as pd
import numpy as np
import holidays

class FeatureService:
    @staticmethod
    def reindex_to_daily(df):
        df['date'] = pd.to_datetime(df['date'])
        all_products = df['product_id'].unique()
        date_range = pd.date_range(df['date'].min(), df['date'].max(), freq='D')
        
        full_index = pd.MultiIndex.from_product(
            [date_range, all_products], names=['date', 'product_id']
        )
        
        metadata = df[['product_id', 'store_id', 'category', 'supplier_id', 'lead_time_days']].drop_duplicates('product_id')
        df_reindexed = df.set_index(['date', 'product_id']).reindex(full_index, fill_value=0).reset_index()
        
        df_reindexed = df_reindexed.drop(columns=['store_id', 'category', 'supplier_id', 'lead_time_days'], errors='ignore')
        df_reindexed = pd.merge(df_reindexed, metadata, on='product_id', how='left')
        df_reindexed['is_imputed'] = df_reindexed['units_sold'] == 0
        
        return df_reindexed

    @staticmethod
    def simulate_stock(group, initial_stock=100, reorder_point=20, reorder_qty=80):
        stock = initial_stock
        stocks = []
        for sold in group['units_sold']:
            stock = max(0, stock - sold)
            if stock <= reorder_point:
                stock += reorder_qty
            stocks.append(stock)
        group['stock_qty'] = stocks
        return group

    @staticmethod
    def calculate_rolling_features(df):
        df = df.sort_values(['product_id', 'date'])
        df['avg_sales_7d'] = df.groupby('product_id')['units_sold'].transform(lambda x: x.rolling(window=7, min_periods=1).mean())
        df['avg_sales_30d'] = df.groupby('product_id')['units_sold'].transform(lambda x: x.rolling(window=30, min_periods=1).mean())
        df['sales_trend_7d'] = df.groupby('product_id')['units_sold'].transform(
            lambda x: x.rolling(window=7, min_periods=1).apply(lambda y: np.polyfit(range(len(y)), y, 1)[0] if len(y) > 1 else 0)
        )
        df['stock_coverage'] = df['stock_qty'] / df['avg_sales_7d'].replace(0, 0.001)
        return df

    @staticmethod
    def add_calendar_features(df):
        id_holidays = holidays.Indonesia(years=[2014, 2015])
        df['date'] = pd.to_datetime(df['date'])
        df['day_of_week'] = df['date'].dt.dayofweek
        df['is_weekend'] = df['day_of_week'].isin([5, 6])
        df['is_holiday'] = df['date'].apply(lambda x: x.date() in id_holidays)
        return df
