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
        lost_sales = []
        pending_deliveries = [] # List of (delivery_date, qty)
        
        lead_time = int(group['lead_time_days'].iloc[0]) if 'lead_time_days' in group.columns else 3
        
        for idx, row in group.iterrows():
            current_date = row['date']
            
            # 1. Cek kiriman yang sampai hari ini
            deliveries_today = [qty for d_date, qty in pending_deliveries if d_date <= current_date]
            stock += sum(deliveries_today)
            pending_deliveries = [(d_date, qty) for d_date, qty in pending_deliveries if d_date > current_date]
            
            # 2. Kurangi stok & Catat Lost Sales (Celah #1 Audit)
            sold_requested = row['units_sold']
            actual_sold = min(stock, sold_requested)
            lost = max(0, sold_requested - actual_sold)
            
            stock = max(0, stock - sold_requested)
            
            # 3. Cek apakah perlu reorder
            if stock <= reorder_point and not pending_deliveries:
                arrival_date = current_date + pd.Timedelta(days=lead_time)
                pending_deliveries.append((arrival_date, reorder_qty))
            
            stocks.append(stock)
            lost_sales.append(lost)
            
        group['stock_qty'] = stocks
        group['lost_sales'] = lost_sales
        return group

    @staticmethod
    def calculate_rolling_features(df):
        df = df.sort_values(['product_id', 'date'])
        df = df.set_index('date')
        
        # Rolling averages
        df['avg_sales_7d'] = df.groupby('product_id')['units_sold'].transform(
            lambda x: x.rolling(window='7D', min_periods=1).mean()
        )
        df['avg_sales_30d'] = df.groupby('product_id')['units_sold'].transform(
            lambda x: x.rolling(window='30D', min_periods=1).mean()
        )
        
        # Perbaikan Celah #2 Audit: Filter False INCREASING pada data sparse
        def get_trend(y):
            if len(y) > 1:
                non_zero_days = (y > 0).sum()
                if non_zero_days < 2: # Butuh minimal 2 titik data asli untuk tren
                    return 0.0
                return round(np.polyfit(range(len(y)), y, 1)[0], 4)
            return 0.0

        df['sales_trend_7d'] = df.groupby('product_id')['units_sold'].transform(
            lambda x: x.rolling(window='7D', min_periods=1).apply(get_trend)
        )
        
        df = df.reset_index()
        # Coverage dihitung di sini agar sinkron dengan stock_qty final (Bug #4)
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
