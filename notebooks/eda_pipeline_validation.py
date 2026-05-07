import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os

# Konfigurasi Path & Warna
RAW_DATA_PATH = "data/Groceries_dataset.csv"
PROCESSED_DATA_PATH = "data/processed_features.csv"
OUTPUT_DIR = "notebooks/eda_output/"
COLORS = {'merah': '#E53935', 'abu_tua': '#424242', 'abu_muda': '#BDBDBD'}

def prepare_data():
    df_raw = pd.read_csv(RAW_DATA_PATH)
    df_proc = pd.read_csv(PROCESSED_DATA_PATH)
    df_proc['date'] = pd.to_datetime(df_proc['date'])
    df_raw['Date'] = pd.to_datetime(df_raw['Date'], format='%d-%m-%Y')
    return df_raw, df_proc

def create_chart_1(df_proc):
    plt.figure(figsize=(10, 6))
    stock_0_pct = (df_proc['stock_qty'] == 0).mean() * 100
    
    plt.hist(df_proc['stock_coverage'].replace([np.inf, -np.inf], 100).clip(0, 50), 
             bins=50, color=COLORS['abu_tua'], edgecolor='white')
    plt.axvline(x=3, color=COLORS['merah'], linestyle='--', label='Threshold Lead Time (3d)')
    
    plt.title(f"Chart 1: Distribusi Stock Coverage\n(Persentase Stock == 0: {stock_0_pct:.1f}%)", fontsize=14)
    plt.xlabel("Stock Coverage (Days)")
    plt.ylabel("Frequency")
    plt.legend()
    
    insight = "Insight: Tingginya frekuensi di x=0 memvalidasi Bug #2 (Simulasi stok menyebabkan 60%+ baris kehabisan stok)."
    plt.figtext(0.5, 0.01, insight, ha="center", fontsize=10, bbox={"facecolor":"orange", "alpha":0.2, "pad":5})
    plt.tight_layout(rect=[0, 0.05, 1, 1])
    plt.savefig(os.path.join(OUTPUT_DIR, "chart1_stock_coverage.png"))
    plt.close()

def create_chart_2(df_raw):
    # Hitung gap antar transaksi per produk
    df_raw = df_raw.sort_values(['itemDescription', 'Date'])
    df_raw['gap'] = df_raw.groupby('itemDescription')['Date'].diff().dt.days
    
    gaps = df_raw.dropna(subset=['gap'])
    mean_gaps = gaps.groupby('itemDescription')['gap'].mean()
    
    fast_moving = mean_gaps[mean_gaps < 3].index
    slow_moving = mean_gaps[mean_gaps >= 3].index
    
    plt.figure(figsize=(10, 6))
    plt.hist(gaps[gaps['itemDescription'].isin(fast_moving)]['gap'], bins=30, alpha=0.7, 
             color=COLORS['abu_tua'], label='Fast-moving (<3d gap)', density=True)
    plt.hist(gaps[gaps['itemDescription'].isin(slow_moving)]['gap'], bins=30, alpha=0.5, 
             color=COLORS['merah'], label='Slow-moving (>=3d gap)', density=True)
    
    plt.axvline(x=7, color='black', linestyle=':', label='Rolling Window (7 rows)')
    
    plt.title("Chart 2: Distribusi Gap Transaksi Antar Hari", fontsize=14)
    plt.xlabel("Gap (Days)")
    plt.ylabel("Density")
    plt.legend()
    
    insight = "Insight: Banyak gap > 7 hari pada slow-moving. Bug #1 terkonfirmasi: rolling(7) baris != 7 hari kalender."
    plt.figtext(0.5, 0.01, insight, ha="center", fontsize=10, bbox={"facecolor":"orange", "alpha":0.2, "pad":5})
    plt.tight_layout(rect=[0, 0.05, 1, 1])
    plt.savefig(os.path.join(OUTPUT_DIR, "chart2_transaction_gaps.png"))
    plt.close()

def create_chart_3(df_proc):
    plt.figure(figsize=(10, 6))
    trend = df_proc['sales_trend_7d']
    noise_pct = (trend.abs() < 1e-10).mean() * 100
    
    # Klasifikasi
    increasing = (trend >= 0.01).mean() * 100
    stable = (trend.abs() < 0.01).mean() * 100
    decreasing = (trend <= -0.01).mean() * 100
    
    plt.hist(trend.clip(-1, 1), bins=50, color=COLORS['abu_tua'], log=True)
    
    plt.title(f"Chart 3: Kualitas Sinyal Tren (Noise: {noise_pct:.2f}%)\nIncr: {increasing:.1f}% | Stable: {stable:.1f}% | Decr: {decreasing:.1f}%", fontsize=14)
    plt.xlabel("Sales Trend Value (Slope)")
    plt.ylabel("Frequency (Log Scale)")
    
    insight = "Insight: Bug #3 terdeteksi (noise floating point). Mayoritas tren 'Stable' bisa menyulitkan LLM memberi saran variatif."
    plt.figtext(0.5, 0.01, insight, ha="center", fontsize=10, bbox={"facecolor":"orange", "alpha":0.2, "pad":5})
    plt.tight_layout(rect=[0, 0.05, 1, 1])
    plt.savefig(os.path.join(OUTPUT_DIR, "chart3_trend_signal.png"))
    plt.close()

def create_chart_4(df_proc):
    # Snapshot terbaru per produk
    snapshot = df_proc.sort_values('date').groupby('product_id').last()
    
    risk_cols = ['stockout_risk', 'overstock_risk', 'deadstock_risk', 'promo_opportunity']
    if 'stockout_risk' not in snapshot.columns:
        snapshot['stockout_risk'] = snapshot['stock_coverage'] < 3
        snapshot['overstock_risk'] = snapshot['stock_coverage'] > 30 # Adjusted threshold
        snapshot['deadstock_risk'] = (snapshot['avg_sales_30d'] == 0)
        snapshot['promo_opportunity'] = (snapshot['sales_trend_7d'] < 0) & (snapshot['stock_qty'] > 50)
    
    # Check for lost sales
    has_lost_sales = (snapshot['lost_sales'] > 0).sum() if 'lost_sales' in snapshot.columns else 0

    fig, axes = plt.subplots(2, 2, figsize=(12, 10))
    axes = axes.flatten()
    
    for i, col in enumerate(risk_cols):
        counts = snapshot[col].value_counts().reindex([True, False], fill_value=0)
        axes[i].bar(['True', 'False'], counts, color=[COLORS['merah'], COLORS['abu_muda']])
        axes[i].set_title(f"Flag: {col}")
        
        if col == 'stockout_risk':
            pct = (snapshot[col].mean() * 100)
            axes[i].annotate(f"{pct:.1f}% flagged", xy=(0, counts[True]/2), ha='center', color='white', fontweight='bold')

    plt.suptitle("Chart 4: Ringkasan Risk Flag (Snapshot Terbaru)", fontsize=16)
    insight = "Insight: LLM akan dibanjiri alert 'Stockout' (Bug #2). Data ini tidak sehat untuk pengambilan keputusan otomatis."
    plt.figtext(0.5, 0.02, insight, ha="center", fontsize=11, bbox={"facecolor":"orange", "alpha":0.2, "pad":5})
    plt.tight_layout(rect=[0, 0.05, 1, 0.95])
    plt.savefig(os.path.join(OUTPUT_DIR, "chart4_risk_flags.png"))
    plt.close()

def create_summary():
    # Menggabungkan 4 PNG menjadi 2x2 grid
    from PIL import Image
    imgs = [Image.open(os.path.join(OUTPUT_DIR, f"chart{i}_{name}.png")) 
            for i, name in zip(range(1,5), ['stock_coverage', 'transaction_gaps', 'trend_signal', 'risk_flags'])]
    
    w, h = imgs[0].size
    summary_img = Image.new('RGB', (w*2, h*2))
    summary_img.paste(imgs[0], (0,0))
    summary_img.paste(imgs[1], (w,0))
    summary_img.paste(imgs[2], (0,h))
    summary_img.paste(imgs[3], (w,h))
    summary_img.save(os.path.join(OUTPUT_DIR, "summary_eda.png"))

if __name__ == "__main__":
    print("Loading data...")
    raw, proc = prepare_data()
    
    print("Generating Chart 1...")
    create_chart_1(proc)
    print("Generating Chart 2...")
    create_chart_2(raw)
    print("Generating Chart 3...")
    create_chart_3(proc)
    print("Generating Chart 4...")
    create_chart_4(proc)
    
    print("Creating Summary Grid...")
    try:
        create_summary()
    except ImportError:
        print("Pillow not installed, skipping summary_eda.png combining.")
    
    # Console Summary
    latest = proc.sort_values('date').groupby('product_id').last()
    # Risk calculation fallback
    if 'stockout_risk' not in latest.columns:
        latest['stockout_risk'] = latest['stock_coverage'] < 3

    print("\n" + "="*30)
    print(f"EDA VALIDATION COMPLETED")
    print(f"Total Baris: {len(proc)}")
    print(f"Jumlah Produk Unik: {proc['product_id'].nunique()}")
    print(f"% Stock == 0: {(proc['stock_qty'] == 0).mean()*100:.2f}%")
    print(f"% Stockout Risk (Snapshot): {latest['stockout_risk'].mean()*100:.2f}%")
    print("="*30)
    print(f"File PNG tersedia di: {OUTPUT_DIR}")
