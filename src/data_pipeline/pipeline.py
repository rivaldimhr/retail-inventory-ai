import pandas as pd
import os
from features import create_time_series_features, add_contextual_features, validate_schema

def reindex_to_daily_calendar(df):
    """
    Isi tanggal yang tidak ada transaksi dengan 0 agar rolling window akurat.
    """
    df['date'] = pd.to_datetime(df['date'])
    all_products = df['product_id'].unique()
    date_range = pd.date_range(df['date'].min(), df['date'].max(), freq='D')
    
    # Buat full grid product x date
    full_index = pd.MultiIndex.from_product(
        [date_range, all_products], names=['date', 'product_id']
    )
    
    # Simpan metadata unik sebelum reindex
    metadata = df[['product_id', 'store_id', 'category', 'supplier_id', 'lead_time_days']].drop_duplicates('product_id')
    
    df_reindexed = df.set_index(['date', 'product_id']).reindex(full_index, fill_value=0).reset_index()
    
    # Kembalikan metadata yang hilang
    df_reindexed = df_reindexed.drop(columns=['store_id', 'category', 'supplier_id', 'lead_time_days'])
    df_reindexed = pd.merge(df_reindexed, metadata, on='product_id', how='left')
    
    # Tandai baris hasil imputasi
    df_reindexed['is_imputed'] = df_reindexed['units_sold'] == 0
    
    return df_reindexed

def simulate_stock_with_restock(group, initial_stock=100, reorder_point=20, reorder_qty=80):
    """
    Simulasi stok dengan restock otomatis (Bug #2 Fix).
    """
    stock = initial_stock
    stocks = []
    for sold in group['units_sold']:
        stock = max(0, stock - sold)
        if stock <= reorder_point:
            stock += reorder_qty
        stocks.append(stock)
    group['stock_qty'] = stocks
    return group

def run_pipeline(input_path, output_path):
    print(f"Loading data from {input_path}...")
    df_raw = pd.read_csv(input_path)
    
    # Preprocessing
    df_raw['Date'] = pd.to_datetime(df_raw['Date'], format='%d-%m-%Y')
    df = df_raw.groupby(['Date', 'itemDescription']).size().reset_index(name='units_sold')
    df.columns = ['date', 'product_id', 'units_sold']
    
    # Data Enrichment Awal (sebelum reindex)
    df['store_id'] = 'STR-001'
    df['category'] = 'General'
    df['supplier_id'] = 'SUPP-001'
    df['lead_time_days'] = 3
    
    # Bug #1 Fix: Reindex ke kalender harian
    print("Reindexing to daily calendar...")
    df = reindex_to_daily_calendar(df)
    
    # Bug #2 Fix: Simulasi stok realistis
    print("Simulating realistic stock cycles...")
    df = df.groupby('product_id', group_keys=False).apply(simulate_stock_with_restock)
    
    # Feature Engineering
    df = create_time_series_features(df)
    df = add_contextual_features(df)
    
    # Validation
    validate_schema(df)
    
    # Save Output
    print(f"Saving processed features to {output_path}...")
    df.to_csv(output_path, index=False)
    print("Pipeline Workload A (Refactored) completed successfully.")

if __name__ == "__main__":
    DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data")
    input_csv = os.path.join(DATA_DIR, "Groceries_dataset.csv")
    output_csv = os.path.join(DATA_DIR, "processed_features.csv")
    
    run_pipeline(input_csv, output_csv)
