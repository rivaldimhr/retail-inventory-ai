import { useState, useEffect, useCallback } from "react";
import "./Dashboard.css";
import FloatingAIChat from "./FloatingAIChat";

// ─── Types ───────────────────────────────────────────────────────────────────

interface DemandSignal {
  avg_daily_demand_forecast: number;
  avg_sales_30d_actual: number;
  lost_sales_last_snapshot: number;
  unmet_demand_flag: boolean;
}

interface RiskFlags {
  stockout_risk: boolean;
  overstock_risk: boolean;
  deadstock_risk: boolean;
  promo_opportunity: boolean;
  missed_revenue_flag: boolean;
}

interface Prediction {
  product_id: string;
  store_id: string;
  category: string;
  current_stock: number;
  demand_signal: DemandSignal;
  stock_coverage_days: number;
  trend_direction: "INCREASING" | "DECREASING" | "STABLE";
  risk_flags: RiskFlags;
  confidence_score: number;
}

interface ForecastMetadata {
  generated_at: string;
  cached_at: string;
  total_count: number;
}

interface ForecastResponse {
  status: string;
  metadata: ForecastMetadata;
  data: Prediction[];
}

interface HealthResponse {
  status: string;
  cache_loaded: boolean;
  data_stale: boolean;
}

// ─── Constants ───────────────────────────────────────────────────────────────

const API_BASE = "http://localhost:8000";
const COVERAGE_MAX = 60;

// ─── Icons (inline SVG) ───────────────────────────────────────────────────────

const icons = {
  box:     <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/><polyline points="3.27 6.96 12 12.01 20.73 6.96"/><line x1="12" y1="22.08" x2="12" y2="12"/></svg>,
  alert:   <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>,
  trend:   <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="23 6 13.5 15.5 8.5 10.5 1 18"/><polyline points="17 6 23 6 23 12"/></svg>,
  archive: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="21 8 21 21 3 21 3 8"/><rect x="1" y="3" width="22" height="5"/><line x1="10" y1="12" x2="14" y2="12"/></svg>,
  dollar:  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><line x1="12" y1="1" x2="12" y2="23"/><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/></svg>,
  refresh: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="23 4 23 10 17 10"/><polyline points="1 20 1 14 7 14"/><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/></svg>,
  search:  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>,
};

// ─── Components ───────────────────────────────────────────────────────────────

function SummaryCard({
  label, value, sub, variant, icon,
}: {
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

function CoverageBar({ days, isStockout, isOverstock }: { days: number; isStockout: boolean; isOverstock: boolean }) {
  const pct = Math.min((days / COVERAGE_MAX) * 100, 100);
  const cls = isStockout ? "bar-danger" : isOverstock ? "bar-warning" : days >= 14 ? "bar-ok" : "bar-caution";
  return (
    <div className="coverage-cell">
      <span className={`coverage-num ${isStockout ? "text-danger" : isOverstock ? "text-warning" : ""}`}>{days}h</span>
      <div className="coverage-track">
        <div className={`coverage-fill ${cls}`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

function TrendBadge({ direction }: { direction: Prediction["trend_direction"] }) {
  const map = {
    INCREASING: { label: "▲ Naik",   cls: "trend-up" },
    DECREASING: { label: "▼ Turun",  cls: "trend-down" },
    STABLE:     { label: "● Stabil", cls: "trend-stable" },
  };
  const { label, cls } = map[direction];
  return <span className={`badge ${cls}`}>{label}</span>;
}

function RiskBadges({ flags }: { flags: RiskFlags }) {
  const active = [
    flags.stockout_risk      && <span key="so" className="badge risk-stockout">Stockout</span>,
    flags.overstock_risk     && <span key="ov" className="badge risk-overstock">Overstock</span>,
    flags.deadstock_risk     && <span key="ds" className="badge risk-deadstock">Deadstock</span>,
    flags.promo_opportunity  && <span key="pr" className="badge risk-promo">Promo</span>,
    flags.missed_revenue_flag && <span key="ls" className="badge risk-missed">Lost Sales</span>,
  ].filter(Boolean);
  return (
    <div className="risk-badges">
      {active.length ? active : <span className="badge risk-ok">OK</span>}
    </div>
  );
}

// ─── App ──────────────────────────────────────────────────────────────────────

export default function App() {
  const [predictions, setPredictions] = useState<Prediction[]>([]);
  const [metadata, setMetadata]       = useState<ForecastMetadata | null>(null);
  const [health, setHealth]           = useState<HealthResponse | null>(null);
  const [loading, setLoading]         = useState(true);
  const [error, setError]             = useState<string | null>(null);
  const [categoryFilter, setCategoryFilter] = useState("");
  const [searchQuery, setSearchQuery]       = useState("");

  const fetchData = useCallback(async (category?: string) => {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams();
      if (category) params.set("category", category);
      const [fRes, hRes] = await Promise.all([
        fetch(`${API_BASE}/api/v1/forecast?${params}`),
        fetch(`${API_BASE}/api/v1/health`),
      ]);
      if (!fRes.ok) {
        const d = await fRes.json().catch(() => ({}));
        throw new Error((d as { detail?: string }).detail ?? `HTTP ${fRes.status}`);
      }
      const forecast: ForecastResponse = await fRes.json();
      const healthData: HealthResponse = await hRes.json();
      setPredictions(forecast.data);
      setMetadata(forecast.metadata);
      setHealth(healthData);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Gagal mengambil data dari API.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchData(categoryFilter || undefined); }, [fetchData, categoryFilter]);

  const categories    = [...new Set(predictions.map((p) => p.category))].sort();
  const filtered      = predictions.filter((p) =>
    !searchQuery ||
    p.product_id.toLowerCase().includes(searchQuery.toLowerCase()) ||
    p.store_id.toLowerCase().includes(searchQuery.toLowerCase())
  );
  const stockoutCount  = predictions.filter((p) => p.risk_flags.stockout_risk).length;
  const overstockCount = predictions.filter((p) => p.risk_flags.overstock_risk).length;
  const deadstockCount = predictions.filter((p) => p.risk_flags.deadstock_risk).length;
  const lostSalesCount = predictions.filter((p) => p.risk_flags.missed_revenue_flag).length;

  const inventoryContext = metadata
    ? {
        total_count: metadata.total_count,
        stockout_count: stockoutCount,
        overstock_count: overstockCount,
        deadstock_count: deadstockCount,
        lost_sales_count: lostSalesCount,
        generated_at: metadata.generated_at,
      }
    : null;

  return (
    <div className="app">
      {/* ── Navbar ── */}
      <header className="navbar">
        <div className="navbar-brand">
          <div className="brand-logo">AI</div>
          <div>
            <div className="brand-name">AIforBusiness</div>
            <div className="brand-sub">Retail Inventory Dashboard</div>
          </div>
        </div>
        <div className="navbar-right">
          {metadata && (
            <div className="meta-pill">
              <span>Data: {new Date(metadata.generated_at).toLocaleString("id-ID", { dateStyle: "short", timeStyle: "short" })}</span>
              <span className="meta-sep">·</span>
              <span>{metadata.total_count} produk</span>
            </div>
          )}
          {health && (
            <div className={`health-chip ${health.data_stale ? "stale" : "live"}`}>
              <span className="health-dot" />
              {health.data_stale ? "Stale" : "Live"}
            </div>
          )}
          <button className="btn-refresh" onClick={() => fetchData(categoryFilter || undefined)} disabled={loading}>
            <span className="btn-icon">{icons.refresh}</span>
            {loading ? "Memuat..." : "Refresh"}
          </button>
        </div>
      </header>

      <main className="main">
        {/* ── Summary Cards ── */}
        <section className="cards-grid">
          <SummaryCard label="Total Produk"   value={metadata?.total_count ?? "—"} icon={icons.box}     variant="sc-neutral" />
          <SummaryCard label="Stockout Risk"  value={stockoutCount}  icon={icons.alert}   variant="sc-danger"  sub="coverage < lead time" />
          <SummaryCard label="Overstock Risk" value={overstockCount} icon={icons.trend}   variant="sc-warning" sub="coverage > 30h & turun" />
          <SummaryCard label="Deadstock"      value={deadstockCount} icon={icons.archive} variant="sc-muted"   sub="stok tinggi, sales ≈ 0" />
          <SummaryCard label="Lost Sales"     value={lostSalesCount} icon={icons.dollar}  variant="sc-info"    sub="permintaan tak terpenuhi" />
        </section>

        {/* ── Table Section ── */}
        <section className="table-section">
          <div className="table-header">
            <div className="table-title">
              <h2>Inventory Forecast</h2>
              <span className="table-count">{filtered.length} produk</span>
            </div>
            <div className="table-controls">
              <div className="search-wrap">
                <span className="search-icon">{icons.search}</span>
                <input
                  className="search-input"
                  type="text"
                  placeholder="Cari Product ID / Store ID..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                />
              </div>
              <select
                className="cat-select"
                value={categoryFilter}
                onChange={(e) => setCategoryFilter(e.target.value)}
              >
                <option value="">Semua Kategori</option>
                {categories.map((c) => <option key={c} value={c}>{c}</option>)}
              </select>
            </div>
          </div>

          {/* Loading */}
          {loading && (
            <div className="state-box">
              <div className="spinner" />
              <p>Mengambil data dari API...</p>
            </div>
          )}

          {/* Error */}
          {!loading && error && (
            <div className="state-box state-error">
              <div className="error-icon">{icons.alert}</div>
              <p className="error-title">Gagal Memuat Data</p>
              <p className="error-detail">{error}</p>
              <p className="error-hint">Jalankan: <code>uvicorn src.api.main:app --reload</code></p>
            </div>
          )}

          {/* Table */}
          {!loading && !error && (
            <div className="table-wrap">
              <table className="dtable">
                <thead>
                  <tr>
                    <th>Product ID</th>
                    <th>Store</th>
                    <th>Kategori</th>
                    <th className="th-right">Stok</th>
                    <th>Coverage</th>
                    <th className="th-right">Forecast/hr</th>
                    <th className="th-right">Aktual 30d</th>
                    <th className="th-right">Lost Sales</th>
                    <th>Tren</th>
                    <th>Risk Flags</th>
                    <th className="th-right">Conf.</th>
                  </tr>
                </thead>
                <tbody>
                  {filtered.length === 0 ? (
                    <tr><td colSpan={11} className="empty-cell">Tidak ada data yang cocok.</td></tr>
                  ) : (
                    filtered.map((p) => {
                      const hasRisk = Object.values(p.risk_flags).some(Boolean);
                      const rowCls  = p.risk_flags.stockout_risk ? "row-stockout"
                                    : p.risk_flags.overstock_risk ? "row-overstock"
                                    : hasRisk ? "row-risk" : "";
                      return (
                        <tr key={`${p.product_id}-${p.store_id}`} className={rowCls}>
                          <td><code className="pid">{p.product_id}</code></td>
                          <td className="td-muted">{p.store_id}</td>
                          <td><span className="badge badge-cat">{p.category}</span></td>
                          <td className="td-num">{p.current_stock}</td>
                          <td>
                            <CoverageBar
                              days={p.stock_coverage_days}
                              isStockout={p.risk_flags.stockout_risk}
                              isOverstock={p.risk_flags.overstock_risk}
                            />
                          </td>
                          <td className="td-num">{p.demand_signal.avg_daily_demand_forecast}</td>
                          <td className="td-num">{p.demand_signal.avg_sales_30d_actual}</td>
                          <td className={`td-num ${p.demand_signal.lost_sales_last_snapshot > 0 ? "text-danger" : ""}`}>
                            {p.demand_signal.lost_sales_last_snapshot}
                          </td>
                          <td><TrendBadge direction={p.trend_direction} /></td>
                          <td><RiskBadges flags={p.risk_flags} /></td>
                          <td className="td-num td-conf">
                            <span className="conf-bar" style={{ "--pct": `${p.confidence_score * 100}%` } as React.CSSProperties} />
                            {(p.confidence_score * 100).toFixed(0)}%
                          </td>
                        </tr>
                      );
                    })
                  )}
                </tbody>
              </table>
            </div>
          )}
        </section>
      </main>

      <footer className="footer">
        AIforBusiness © {new Date().getFullYear()} — Powered by FastAPI + XGBoost
      </footer>

      <FloatingAIChat inventoryContext={inventoryContext} />
    </div>
  );
}