import { useState, useEffect, useCallback, useRef } from "react";
import "./Dashboard.css";
import FloatingAIChat from "./FloatingAIChat";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
  PieChart, Pie, ComposedChart, Line,
} from "recharts";
import { api, DEMO } from "./api";

// ─── Types ───────────────────────────────────────────────────────────────────

interface MBARule {
  antecedents: string[];
  consequents: string[];
  transactions: number;
  support: number;
  confidence: number;
  lift: number;
}

interface MBAData {
  generated_at: string;
  rules: MBARule[];
  summary: { total_rules: number; total_transactions: number; total_products: number };
}

interface DemandSignal {
  forecast_7d: number;
  avg_daily_demand_forecast: number;
  actual_last_7d: number;
  avg_sales_30d_actual: number;
  lost_sales_30d: number;
  unmet_demand_flag: boolean;
}

interface RiskFlags {
  out_of_stock: boolean;
  stockout_risk: boolean;
  overstock_risk: boolean;
  deadstock_risk: boolean;
  promo_opportunity: boolean;
  missed_revenue_flag: boolean;
}

interface Prediction {
  product_id: string;
  product_name: string;
  category: string;
  unit_price: number;
  current_stock: number;
  on_order: number;
  lead_time_days: number;
  safety_stock: number;
  reorder_point: number;
  stock_coverage_days: number;
  trend_direction: "INCREASING" | "DECREASING" | "STABLE";
  demand_signal: DemandSignal;
  recommended_order_qty: number;
  revenue_at_risk: number;
  lost_revenue_30d: number;
  days_since_last_sale: number;
  risk_flags: RiskFlags;
}

interface ModelSummary {
  algorithm: string;
  mae_7d: number;
  wape_7d: number | null;
  mae_improvement_vs_best_baseline: number;
}

interface ForecastMetadata {
  generated_at: string;
  data_as_of: string;
  currency: string;
  horizon_days: number;
  model: ModelSummary | null;
  stale: boolean;
  total_count: number;
}

interface HistoryPoint { date: string; units_sold: number; stock: number; lost_sales: number; received: number }

// ─── Helpers ─────────────────────────────────────────────────────────────────

const COVERAGE_MAX = 60;
const money = (v: number, cur = "GBP") =>
  new Intl.NumberFormat("en-GB", { style: "currency", currency: cur, maximumFractionDigits: 0 }).format(v);

const icons = {
  box:     <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/><polyline points="3.27 6.96 12 12.01 20.73 6.96"/><line x1="12" y1="22.08" x2="12" y2="12"/></svg>,
  alert:   <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>,
  cart:    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="9" cy="21" r="1"/><circle cx="20" cy="21" r="1"/><path d="M1 1h4l2.68 13.39a2 2 0 0 0 2 1.61h9.72a2 2 0 0 0 2-1.61L23 6H6"/></svg>,
  trend:   <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="23 6 13.5 15.5 8.5 10.5 1 18"/><polyline points="17 6 23 6 23 12"/></svg>,
  archive: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="21 8 21 21 3 21 3 8"/><rect x="1" y="3" width="22" height="5"/><line x1="10" y1="12" x2="14" y2="12"/></svg>,
  dollar:  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><line x1="12" y1="1" x2="12" y2="23"/><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/></svg>,
  refresh: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="23 4 23 10 17 10"/><polyline points="1 20 1 14 7 14"/><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/></svg>,
  search:  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>,
  target:  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="2"/></svg>,
  download:<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>,
};

// ─── Small components ─────────────────────────────────────────────────────────

function SummaryCard({ label, value, sub, variant, icon }: {
  label: string; value: number | string; sub?: string; variant?: string; icon?: React.ReactNode;
}) {
  return (
    <div className={`sc ${variant ?? ""}`}>
      {icon && <div className="sc-icon">{icon}</div>}
      <div className="sc-body">
        <div className="sc-value">{value}</div>
        <div className="sc-label">{label}</div>
        {sub && <div className="sc-sub">{sub}</div>}
      </div>
    </div>
  );
}

function CoverageBar({ days, lead, isStockout, isOverstock }: { days: number; lead: number; isStockout: boolean; isOverstock: boolean }) {
  const pct = Math.min((days / COVERAGE_MAX) * 100, 100);
  const cls = isStockout ? "bar-danger" : isOverstock ? "bar-warning" : days >= lead * 2 ? "bar-ok" : "bar-caution";
  return (
    <div className="coverage-cell" title={`Stok cukup untuk ${days} hari. Pengiriman supplier ${lead} hari.`}>
      <span className={`coverage-num ${isStockout ? "text-danger" : isOverstock ? "text-warning" : ""}`}>
        {days >= 999 ? "∞" : `${days}h`}
      </span>
      <div className="coverage-track">
        <div className={`coverage-fill ${cls}`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

function TrendBadge({ direction }: { direction: Prediction["trend_direction"] }) {
  const map = {
    INCREASING: { label: "▲ Naik", cls: "trend-up" },
    DECREASING: { label: "▼ Turun", cls: "trend-down" },
    STABLE: { label: "● Stabil", cls: "trend-stable" },
  };
  const { label, cls } = map[direction];
  return <span className={`badge ${cls}`}>{label}</span>;
}

function RiskBadges({ flags }: { flags: RiskFlags }) {
  const active = [
    flags.out_of_stock && <span key="oos" className="badge risk-stockout">Stok kosong</span>,
    flags.stockout_risk && <span key="so" className="badge risk-stockout">Stockout</span>,
    flags.overstock_risk && <span key="ov" className="badge risk-overstock">Overstock</span>,
    flags.deadstock_risk && <span key="ds" className="badge risk-deadstock">Deadstock</span>,
    flags.promo_opportunity && <span key="pr" className="badge risk-promo">Promo</span>,
    flags.missed_revenue_flag && <span key="ls" className="badge risk-missed">Lost Sales</span>,
  ].filter(Boolean);
  return <div className="risk-badges">{active.length ? active : <span className="badge risk-ok">OK</span>}</div>;
}

function ProductDetail({ p, currency, onClose }: { p: Prediction; currency: string; onClose: () => void }) {
  const [history, setHistory] = useState<HistoryPoint[] | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const panelRef = useRef<HTMLDivElement>(null);

  useEffect(() => { panelRef.current?.scrollIntoView({ behavior: "smooth", block: "start" }); }, [p.product_id]);

  useEffect(() => {
    setHistory(null);
    setErr(null);
    api(`/api/v1/products/${encodeURIComponent(p.product_id)}/history?days=90`)
      .then((j) => setHistory(j.data))
      .catch((e) => setErr(e instanceof Error ? e.message : "Gagal memuat riwayat."));
  }, [p.product_id]);

  return (
    <div className="detail-panel" ref={panelRef}>
      <div className="detail-head">
        <div>
          <div className="detail-title">{p.product_name}</div>
          <div className="td-muted">{p.product_id} · {p.category} · {money(p.unit_price, currency)}/unit</div>
        </div>
        <button className="btn-ghost" onClick={onClose}>Tutup</button>
      </div>
      <div className="detail-stats">
        <div><b>{p.current_stock}</b><span>stok sekarang</span></div>
        <div><b>{p.on_order}</b><span>sedang dikirim</span></div>
        <div><b>{p.demand_signal.forecast_7d}</b><span>prediksi 7 hari</span></div>
        <div><b>{p.reorder_point}</b><span>titik pesan ulang</span></div>
        <div><b>{p.safety_stock}</b><span>stok pengaman</span></div>
        <div><b>{p.lead_time_days} hari</b><span>waktu kirim supplier</span></div>
      </div>
      {err && <p className="error-detail">{err}</p>}
      {!err && !history && <div className="state-box"><div className="spinner" /></div>}
      {history && (
        <ResponsiveContainer width="100%" height={240}>
          <ComposedChart data={history} margin={{ top: 8, right: 8, left: -12, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
            <XAxis dataKey="date" tick={{ fontSize: 10, fill: "#64748b" }} minTickGap={24} />
            <YAxis tick={{ fontSize: 11, fill: "#64748b" }} />
            <Tooltip contentStyle={{ fontSize: 12, borderRadius: 8, border: "1px solid #e2e8f0" }} />
            <Legend wrapperStyle={{ fontSize: 12 }} />
            <Bar dataKey="units_sold" name="Terjual" fill="#6366f1" />
            <Bar dataKey="lost_sales" name="Tidak terlayani" fill="#f43f5e" />
            <Line dataKey="stock" name="Stok" stroke="#10b981" dot={false} strokeWidth={2} />
          </ComposedChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}

function downloadOrderList(rows: Prediction[], currency: string) {
  const header = ["product_id", "product_name", "category", "current_stock", "on_order", "forecast_7d",
    "recommended_order_qty", `unit_price_${currency}`, `order_value_${currency}`];
  const lines = rows.map((p) => [
    p.product_id, `"${p.product_name.replace(/"/g, '""')}"`, p.category, p.current_stock, p.on_order,
    p.demand_signal.forecast_7d, p.recommended_order_qty, p.unit_price,
    (p.recommended_order_qty * p.unit_price).toFixed(2),
  ].join(","));
  const blob = new Blob([[header.join(","), ...lines].join("\n")], { type: "text/csv" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = `daftar-pesan-${new Date().toISOString().slice(0, 10)}.csv`;
  a.click();
  URL.revokeObjectURL(a.href);
}

// ─── App ──────────────────────────────────────────────────────────────────────

export default function App() {
  const [activeTab, setActiveTab] = useState<"forecast" | "mba">("forecast");

  const [predictions, setPredictions] = useState<Prediction[]>([]);
  const [metadata, setMetadata] = useState<ForecastMetadata | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [categoryFilter, setCategoryFilter] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const [onlyReorder, setOnlyReorder] = useState(false);
  const [selected, setSelected] = useState<Prediction | null>(null);

  const [mbaData, setMbaData] = useState<MBAData | null>(null);
  const [mbaLoading, setMbaLoading] = useState(false);
  const [mbaError, setMbaError] = useState<string | null>(null);
  const [mbaSearch, setMbaSearch] = useState("");
  const [mbaRefreshing, setMbaRefreshing] = useState(false);

  const fetchMba = useCallback(async () => {
    setMbaLoading(true);
    setMbaError(null);
    try {
      setMbaData((await api("/api/v1/mba")).data);
    } catch (err) {
      setMbaError(err instanceof Error ? err.message : "Gagal mengambil data market basket.");
    } finally {
      setMbaLoading(false);
    }
  }, []);

  const runMbaRefresh = async () => {
    setMbaRefreshing(true);
    setMbaError(null);
    try {
      await api("/api/v1/mba/refresh", { method: "POST" });
      await fetchMba();
    } catch (err) {
      setMbaError(err instanceof Error ? err.message : "Gagal menjalankan analisis.");
    } finally {
      setMbaRefreshing(false);
    }
  };

  useEffect(() => { if (activeTab === "mba" && !mbaData) fetchMba(); }, [activeTab, mbaData, fetchMba]);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const json = await api("/api/v1/forecast");
      setPredictions(json.data);
      setMetadata(json.metadata);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Gagal mengambil data dari API.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchData(); }, [fetchData]);

  const currency = metadata?.currency ?? "GBP";
  const categories = [...new Set(predictions.map((p) => p.category))].sort();
  const q = searchQuery.toLowerCase();
  const filtered = predictions.filter((p) =>
    (!categoryFilter || p.category === categoryFilter) &&
    (!onlyReorder || p.recommended_order_qty > 0) &&
    (!q || p.product_id.toLowerCase().includes(q) || p.product_name.toLowerCase().includes(q))
  );
  const reorderRows = predictions.filter((p) => p.recommended_order_qty > 0);
  const count = (k: keyof RiskFlags) => predictions.filter((p) => p.risk_flags[k]).length;
  const stockoutCount = count("stockout_risk");
  const outOfStockCount = count("out_of_stock");
  const overstockCount = count("overstock_risk");
  const deadstockCount = count("deadstock_risk");
  const lostSalesCount = count("missed_revenue_flag");
  const revenueAtRisk = predictions.reduce((s, p) => s + p.revenue_at_risk, 0);
  const lostRevenue = predictions.reduce((s, p) => s + p.lost_revenue_30d, 0);

  const inventoryContext = metadata ? {
    total_count: metadata.total_count,
    stockout_count: stockoutCount,
    overstock_count: overstockCount,
    deadstock_count: deadstockCount,
    lost_sales_count: lostSalesCount,
    reorder_count: reorderRows.length,
    generated_at: metadata.generated_at,
  } : null;

  const topDemandChartData = [...predictions]
    .sort((a, b) => b.demand_signal.forecast_7d - a.demand_signal.forecast_7d)
    .slice(0, 10)
    .map((p) => ({
      name: p.product_name.length > 16 ? p.product_name.slice(0, 16) + "…" : p.product_name,
      "Prediksi 7 hari": p.demand_signal.forecast_7d,
      "7 hari terakhir": p.demand_signal.actual_last_7d,
    }));

  const okCount = predictions.filter((p) => !Object.values(p.risk_flags).some(Boolean)).length;
  const riskChartData = [
    { name: "Aman", value: okCount, fill: "#10b981" },
    { name: "Stok kosong", value: outOfStockCount, fill: "#be123c" },
    { name: "Stockout", value: stockoutCount, fill: "#f43f5e" },
    { name: "Overstock", value: overstockCount, fill: "#f59e0b" },
    { name: "Deadstock", value: deadstockCount, fill: "#94a3b8" },
    { name: "Lost Sales", value: lostSalesCount, fill: "#a855f7" },
  ].filter((d) => d.value > 0);

  const categoryChartData = categories.map((c) => ({
    name: c.length > 18 ? c.slice(0, 18) + "…" : c,
    Produk: predictions.filter((p) => p.category === c).length,
    "Perlu dipesan": predictions.filter((p) => p.category === c && p.recommended_order_qty > 0).length,
  }));

  const mq = mbaSearch.toLowerCase();
  const mbaFiltered = (mbaData?.rules ?? []).filter((r) =>
    !mq || r.antecedents.some((a) => a.toLowerCase().includes(mq)) || r.consequents.some((c) => c.toLowerCase().includes(mq))
  );
  const model = metadata?.model;

  return (
    <div className="app">
      <header className="navbar">
        <div className="navbar-brand">
          <div className="brand-logo">AI</div>
          <div>
            <div className="brand-name">Retail Inventory AI</div>
            <div className="brand-sub">Prediksi stok · Rekomendasi pesan · Market basket</div>
          </div>
        </div>
        <div className="navbar-right">
          {metadata && (
            <div className="meta-pill">
              <span>Data per {metadata.data_as_of}</span>
              <span className="meta-sep">·</span>
              <span>{metadata.total_count} produk</span>
            </div>
          )}
          {metadata && !DEMO && (
            <div className={`health-chip ${metadata.stale ? "stale" : "live"}`} title={metadata.stale ? "Forecast lebih dari 24 jam. Jalankan ulang pipeline." : "Forecast terbaru"}>
              <span className="health-dot" />
              {metadata.stale ? "Perlu diperbarui" : "Terbaru"}
            </div>
          )}
          <button className="btn-refresh" onClick={fetchData} disabled={loading}>
            <span className="btn-icon">{icons.refresh}</span>
            {loading ? "Memuat..." : "Refresh"}
          </button>
        </div>
      </header>

      {DEMO && (
        <div className="demo-banner">
          Mode demo: data asli Online Retail II (UCI) sampai {metadata?.data_as_of ?? "…"}, tanpa server. Stok adalah hasil simulasi.
          Chat AI belum aktif karena API key perlu disiapkan, jadi chat menjawab otomatis dari data.{" "}
          <a href="https://github.com/rivaldimhr/retail-inventory-ai" target="_blank" rel="noreferrer">Lihat kode di GitHub</a>
        </div>
      )}

      <nav className="tab-nav">
        <button className={`tab-btn ${activeTab === "forecast" ? "tab-active" : ""}`} onClick={() => setActiveTab("forecast")}>
          Stok &amp; Prediksi
        </button>
        <button className={`tab-btn ${activeTab === "mba" ? "tab-active" : ""}`} onClick={() => setActiveTab("mba")}>
          Market Basket
        </button>
      </nav>

      <main className="main">
        {activeTab === "mba" && (
          <section className="mba-section">
            <section className="cards-grid">
              <SummaryCard label="Pasangan produk" value={mbaData?.summary.total_rules ?? "—"} icon={icons.trend} variant="sc-neutral" />
              <SummaryCard label="Invoice dianalisis" value={mbaData?.summary.total_transactions.toLocaleString("id-ID") ?? "—"} icon={icons.box} variant="sc-neutral" />
              <SummaryCard label="Total produk" value={mbaData?.summary.total_products.toLocaleString("id-ID") ?? "—"} icon={icons.archive} variant="sc-neutral" />
            </section>

            <div className="table-section">
              <div className="table-header">
                <div className="table-title">
                  <h2>Produk yang sering dibeli bersamaan</h2>
                  <span className="table-count">{mbaFiltered.length} aturan</span>
                </div>
                <div className="table-controls">
                  <div className="search-wrap">
                    <span className="search-icon">{icons.search}</span>
                    <input className="search-input" type="text" placeholder="Cari produk..." value={mbaSearch} onChange={(e) => setMbaSearch(e.target.value)} />
                  </div>
                  <button className="btn-refresh" onClick={runMbaRefresh} disabled={mbaRefreshing || DEMO}>
                    <span className="btn-icon">{icons.refresh}</span>
                    {mbaRefreshing ? "Memproses..." : "Hitung ulang"}
                  </button>
                </div>
              </div>

              {mbaLoading && <div className="state-box"><div className="spinner" /><p>Memuat aturan...</p></div>}
              {!mbaLoading && mbaError && (
                <div className="state-box state-error">
                  <div className="error-icon">{icons.alert}</div>
                  <p className="error-title">Gagal memuat market basket</p>
                  <p className="error-detail">{mbaError}</p>
                  <p className="error-hint">Klik <strong>Hitung ulang</strong> untuk menjalankan analisis pertama kali.</p>
                </div>
              )}
              {!mbaLoading && !mbaError && mbaData && (
                <div className="table-wrap">
                  <table className="dtable mba-table">
                    <thead>
                      <tr>
                        <th>Jika membeli</th>
                        <th>Cenderung juga membeli</th>
                        <th className="th-right">Invoice</th>
                        <th><span className="mba-th-tip" data-tip="Persentase invoice yang berisi kedua produk.">Support <span className="mba-info">?</span></span></th>
                        <th><span className="mba-th-tip" data-tip="Dari pembeli produk pertama, berapa persen yang juga membeli produk kedua.">Confidence <span className="mba-info">?</span></span></th>
                        <th><span className="mba-th-tip mba-th-tip-left" data-tip="Seberapa jauh di atas kebetulan. Di atas 1 = saling terkait; di atas 2 = sangat kuat.">Lift <span className="mba-info">?</span></span></th>
                      </tr>
                    </thead>
                    <tbody>
                      {mbaFiltered.length === 0 ? (
                        <tr><td colSpan={6} className="empty-cell">Tidak ada aturan yang cocok.</td></tr>
                      ) : mbaFiltered.map((rule, i) => (
                        <tr key={i}>
                          <td>{rule.antecedents.join(" + ")}</td>
                          <td>{rule.consequents.join(" + ")}</td>
                          <td className="td-num">{rule.transactions.toLocaleString("id-ID")}</td>
                          <td>{(rule.support * 100).toFixed(2)}%</td>
                          <td>
                            <div className="mba-conf-cell">
                              <div className="mba-conf-bar-track"><div className="mba-conf-bar-fill" style={{ width: `${rule.confidence * 100}%` }} /></div>
                              <span className="mba-conf-label">{(rule.confidence * 100).toFixed(1)}%</span>
                            </div>
                          </td>
                          <td className={rule.lift >= 2 ? "text-danger" : rule.lift >= 1.5 ? "text-warning" : ""}>{rule.lift.toFixed(2)}x</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </section>
        )}

        {activeTab === "forecast" && <>
          <section className="cards-grid">
            <SummaryCard label="Perlu dipesan" value={reorderRows.length} icon={icons.cart} variant="sc-neutral" sub="stok + kiriman ≤ titik pesan ulang" />
            <SummaryCard label="Risiko kehabisan" value={stockoutCount} icon={icons.alert} variant="sc-danger" sub={`habis sebelum kiriman tiba · ${outOfStockCount} sedang kosong`} />
            <SummaryCard label="Nilai berisiko" value={money(revenueAtRisk, currency)} icon={icons.dollar} variant="sc-danger" sub="penjualan hilang jika tidak dipesan" />
            <SummaryCard label="Overstock" value={overstockCount} icon={icons.trend} variant="sc-warning" sub="stok > 60 hari" />
            <SummaryCard label="Deadstock" value={deadstockCount} icon={icons.archive} variant="sc-muted" sub="tidak terjual ≥ 60 hari" />
            <SummaryCard label="Penjualan hilang 30h" value={money(lostRevenue, currency)} icon={icons.dollar} variant="sc-info" sub={`${lostSalesCount} produk sempat kosong`} />
          </section>

          {model && (
            <section className="model-strip">
              <span className="model-icon">{icons.target}</span>
              <span>
                Akurasi prediksi 7 hari: rata-rata meleset <b>{model.mae_7d.toFixed(1)} unit</b> per produk
                {model.wape_7d !== null && <> ({(model.wape_7d * 100).toFixed(0)}% dari total penjualan)</>}
                {" · "}
                {model.mae_improvement_vs_best_baseline >= 0
                  ? <><b>{(model.mae_improvement_vs_best_baseline * 100).toFixed(0)}% lebih akurat</b> dari metode rata-rata sederhana</>
                  : <>belum lebih akurat dari metode rata-rata sederhana</>}
                <span className="td-muted"> · {model.algorithm}</span>
              </span>
            </section>
          )}

          {!loading && !error && predictions.length > 0 && (
            <section className="charts-grid">
              <div className="chart-card">
                <div className="chart-card-title">Top 10 produk: prediksi 7 hari vs 7 hari terakhir</div>
                <ResponsiveContainer width="100%" height={220}>
                  <BarChart data={topDemandChartData} margin={{ top: 4, right: 8, left: -16, bottom: 56 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                    <XAxis dataKey="name" tick={{ fontSize: 10, fill: "#64748b" }} angle={-35} textAnchor="end" interval={0} />
                    <YAxis tick={{ fontSize: 11, fill: "#64748b" }} />
                    <Tooltip contentStyle={{ fontSize: 12, borderRadius: 8, border: "1px solid #e2e8f0" }} />
                    <Legend verticalAlign="top" wrapperStyle={{ fontSize: 12, paddingBottom: 6 }} />
                    <Bar dataKey="Prediksi 7 hari" fill="#6366f1" radius={[4, 4, 0, 0]} />
                    <Bar dataKey="7 hari terakhir" fill="#a78bfa" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
              <div className="chart-card">
                <div className="chart-card-title">Status risiko produk</div>
                <ResponsiveContainer width="100%" height={220}>
                  <PieChart>
                    <Pie data={riskChartData} cx="50%" cy="50%" innerRadius={50} outerRadius={78} paddingAngle={3} dataKey="value"
                      label={({ percent }) => ((percent ?? 0) >= 0.03 ? `${((percent ?? 0) * 100).toFixed(0)}%` : "")} labelLine={false} />
                    <Tooltip contentStyle={{ fontSize: 12, borderRadius: 8, border: "1px solid #e2e8f0" }} />
                    <Legend wrapperStyle={{ fontSize: 12 }} />
                  </PieChart>
                </ResponsiveContainer>
              </div>
              <div className="chart-card">
                <div className="chart-card-title">Produk per kategori</div>
                <ResponsiveContainer width="100%" height={220}>
                  <BarChart data={categoryChartData} layout="vertical" margin={{ top: 4, right: 8, left: 24, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                    <XAxis type="number" tick={{ fontSize: 11, fill: "#64748b" }} />
                    <YAxis type="category" dataKey="name" width={110} tick={{ fontSize: 10, fill: "#64748b" }} />
                    <Tooltip contentStyle={{ fontSize: 12, borderRadius: 8, border: "1px solid #e2e8f0" }} />
                    <Legend wrapperStyle={{ fontSize: 12 }} />
                    <Bar dataKey="Produk" fill="#c7d2fe" />
                    <Bar dataKey="Perlu dipesan" fill="#6366f1" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </section>
          )}

          {selected && <ProductDetail p={selected} currency={currency} onClose={() => setSelected(null)} />}

          <section className="table-section">
            <div className="table-header">
              <div className="table-title">
                <h2>Daftar produk</h2>
                <span className="table-count">{filtered.length} produk</span>
              </div>
              <div className="table-controls">
                <div className="search-wrap">
                  <span className="search-icon">{icons.search}</span>
                  <input className="search-input" type="text" placeholder="Cari nama atau kode produk..." value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)} />
                </div>
                <select className="cat-select" value={categoryFilter} onChange={(e) => setCategoryFilter(e.target.value)}>
                  <option value="">Semua kategori</option>
                  {categories.map((c) => <option key={c} value={c}>{c}</option>)}
                </select>
                <label className="toggle-label">
                  <input type="checkbox" checked={onlyReorder} onChange={(e) => setOnlyReorder(e.target.checked)} />
                  Hanya yang perlu dipesan
                </label>
                <button className="btn-refresh" onClick={() => downloadOrderList(reorderRows, currency)} disabled={!reorderRows.length}>
                  <span className="btn-icon">{icons.download}</span>
                  Unduh daftar pesan
                </button>
              </div>
            </div>

            {loading && <div className="state-box"><div className="spinner" /><p>Mengambil data dari API...</p></div>}
            {!loading && error && (
              <div className="state-box state-error">
                <div className="error-icon">{icons.alert}</div>
                <p className="error-title">Gagal memuat data</p>
                <p className="error-detail">{error}</p>
                <p className="error-hint">Pastikan backend berjalan: <code>uvicorn src.api.main:app --reload</code></p>
              </div>
            )}
            {!loading && !error && (
              <div className="table-wrap">
                <table className="dtable">
                  <thead>
                    <tr>
                      <th>Produk</th>
                      <th>Kategori</th>
                      <th className="th-right">Stok</th>
                      <th>Cukup untuk</th>
                      <th className="th-right">Prediksi 7 hari</th>
                      <th className="th-right">Saran pesan</th>
                      <th className="th-right">Nilai berisiko</th>
                      <th>Tren</th>
                      <th>Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filtered.length === 0 ? (
                      <tr><td colSpan={9} className="empty-cell">Tidak ada produk yang cocok.</td></tr>
                    ) : filtered.map((p) => {
                      const hasRisk = Object.values(p.risk_flags).some(Boolean);
                      const rowCls = p.risk_flags.stockout_risk || p.risk_flags.out_of_stock ? "row-stockout" : p.risk_flags.overstock_risk ? "row-overstock" : hasRisk ? "row-risk" : "";
                      return (
                        <tr key={p.product_id} className={`${rowCls} row-click ${selected?.product_id === p.product_id ? "row-selected" : ""}`}
                          onClick={() => setSelected(p)} tabIndex={0} onKeyDown={(e) => { if (e.key === "Enter") setSelected(p); }}>
                          <td>
                            <div className="pname">{p.product_name}</div>
                            <code className="pid">{p.product_id}</code>
                          </td>
                          <td><span className="badge badge-cat">{p.category}</span></td>
                          <td className="td-num">{p.current_stock}{p.on_order > 0 && <div className="td-muted">+{p.on_order} dikirim</div>}</td>
                          <td><CoverageBar days={p.stock_coverage_days} lead={p.lead_time_days} isStockout={p.risk_flags.stockout_risk} isOverstock={p.risk_flags.overstock_risk} /></td>
                          <td className="td-num">{p.demand_signal.forecast_7d}</td>
                          <td className={`td-num ${p.recommended_order_qty > 0 ? "text-order" : "td-muted"}`}>{p.recommended_order_qty > 0 ? p.recommended_order_qty : "—"}</td>
                          <td className={`td-num ${p.revenue_at_risk > 0 ? "text-danger" : "td-muted"}`}>{p.revenue_at_risk > 0 ? money(p.revenue_at_risk, currency) : "—"}</td>
                          <td><TrendBadge direction={p.trend_direction} /></td>
                          <td><RiskBadges flags={p.risk_flags} /></td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        </>}
      </main>

      <footer className="footer">
        Retail Inventory AI · Data: Online Retail II (UCI, CC BY 4.0) · FastAPI + gradient boosting
      </footer>

      <FloatingAIChat inventoryContext={inventoryContext} />
    </div>
  );
}
