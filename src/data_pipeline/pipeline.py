import pandas as pd

def clean_and_reindex(df_raw):
    """
    Membersihkan data mentah dan mengubahnya menjadi kalender harian yang utuh
    """
    # Agregasi penjualan harian
    df_raw['Date'] = pd.to_datetime(df_raw['Date'], format='%d-%m-%Y')
    df = df_raw.groupby(['Date', 'itemDescription']).size().reset_index(name='units_sold')
    df.columns = ['date', 'product_id', 'units_sold']
    
    # Penambahan metadata dasar
    df['store_id'] = 'STR-001'
    df['category'] = 'General'
    df['supplier_id'] = 'SUPP-001'
    df['lead_time_days'] = 3
    
    # Pembuatan kalender harian penuh (Reindexing)
    all_products = df['product_id'].unique()
    date_range = pd.date_range(df['date'].min(), df['date'].max(), freq='D')
    
    # Membuat kerangka kalender tanpa ada hari yang terlewat
    full_index = pd.MultiIndex.from_product(
        [date_range, all_products], names=['date', 'product_id']
    )
    
    # Menggabungkan kerangka kalender dengan data penjualan asli
    metadata = df[['product_id', 'store_id', 'category', 'supplier_id', 'lead_time_days']].drop_duplicates('product_id')
    df_reindexed = df.set_index(['date', 'product_id']).reindex(full_index, fill_value=0).reset_index()
    
    # Membersihkan kolom duplikat dan menandai data yang kosong
    df_reindexed = df_reindexed.drop(columns=['store_id', 'category', 'supplier_id', 'lead_time_days'], errors='ignore')
    df_reindexed = pd.merge(df_reindexed, metadata, on='product_id', how='left')
    df_reindexed['is_imputed'] = df_reindexed['units_sold'] == 0
    
    return df_reindexed