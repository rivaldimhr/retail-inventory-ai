// Backend address. Set VITE_API_BASE (e.g. https://my-api.onrender.com) for a deployed backend.
// Empty string = same origin, which works with the Vite dev proxy in vite.config.ts.
export const API_BASE: string = import.meta.env.VITE_API_BASE ?? "";

// Demo mode (VITE_DEMO=true): no backend. Data comes from static JSON exported by
// scripts/export_demo.py, and the chat answers with simple rules over the same data.
export const DEMO: boolean = import.meta.env.VITE_DEMO === "true";

// Optional: a deployed backend used ONLY for the chat in demo mode (e.g. https://xxx.onrender.com).
export const CHAT_API: string = import.meta.env.VITE_CHAT_API ?? "";

const demoBase = `${import.meta.env.BASE_URL}demo/`;
const demoCache = new Map<string, Promise<unknown>>();

function demoFile<T>(name: string): Promise<T> {
  if (!demoCache.has(name)) {
    demoCache.set(name, fetch(demoBase + name).then((r) => {
      if (!r.ok) throw new Error(`Data demo ${name} tidak ditemukan.`);
      return r.json();
    }));
  }
  return demoCache.get(name) as Promise<T>;
}

async function readError(res: Response): Promise<never> {
  const d = await res.json().catch(() => ({}));
  throw new Error((d as { detail?: string }).detail ?? `HTTP ${res.status}`);
}

interface HistoryFile { columns: string[]; data: Record<string, (string | number)[][]> }

/** GET/POST an API path such as "/api/v1/forecast". In demo mode, served from static files. */
export async function api<T = any>(path: string, init?: RequestInit): Promise<T> {
  if (!DEMO) {
    const res = await fetch(`${API_BASE}${path}`, init);
    if (!res.ok) await readError(res);
    return res.json();
  }
  const clean = path.split("?")[0];
  if (clean === "/api/v1/forecast") return demoFile<T>("forecast.json");
  if (clean === "/api/v1/mba") return demoFile<T>("mba.json");
  if (clean === "/api/v1/mba/refresh") return { status: "success" } as T;
  if (clean === "/api/v1/metrics") return demoFile<T>("metrics.json");
  const m = clean.match(/^\/api\/v1\/products\/([^/]+)\/history$/);
  if (m) {
    const id = decodeURIComponent(m[1]);
    const h = await demoFile<HistoryFile>("history.json");
    const rows = h.data[id];
    if (!rows) throw new Error(`Produk ${id} tidak ditemukan.`);
    return { status: "success", data: rows.map((r) => Object.fromEntries(h.columns.map((c, i) => [c, r[i]]))) } as T;
  }
  throw new Error("Fitur ini tidak tersedia di mode demo.");
}

// ─── Demo chat: rule-based answers from the forecast data ─────────────────────

interface DemoProduct {
  product_id: string; product_name: string; current_stock: number; on_order: number;
  stock_coverage_days: number; lead_time_days: number; recommended_order_qty: number;
  revenue_at_risk: number; lost_revenue_30d: number; trend_direction: string;
  demand_signal: { forecast_7d: number; lost_sales_30d: number };
  risk_flags: Record<string, boolean>;
}

const fmt = (v: number) => `£${Math.round(v).toLocaleString("en-GB")}`;
const line = (p: DemoProduct) =>
  `• ${p.product_name}: stok ${p.current_stock}${p.on_order ? ` (+${p.on_order} dikirim)` : ""}, ` +
  `prediksi 7 hari ${p.demand_signal.forecast_7d} unit, cukup ${p.stock_coverage_days >= 999 ? "∞" : p.stock_coverage_days} hari`;

export async function demoChat(message: string): Promise<string> {
  const { data } = await demoFile<{ data: DemoProduct[] }>("forecast.json");
  const q = message.toLowerCase();
  const named = data.filter((p) => q.includes(p.product_name.toLowerCase()) || q.includes(p.product_id.toLowerCase()));
  const note = "\n\n(Mode demo: Chat AI belum aktif karena API key perlu disiapkan. Jawaban ini dibuat otomatis dari data.)";

  if (named.length) {
    const p = named[0];
    const labels: Record<string, string> = { out_of_stock: "stok kosong", stockout_risk: "berisiko habis", overstock_risk: "overstock",
      deadstock_risk: "deadstock", promo_opportunity: "peluang promo", missed_revenue_flag: "sempat kehilangan penjualan" };
    const flags = Object.entries(p.risk_flags).filter(([, v]) => v).map(([k]) => labels[k] ?? k);
    return `${line(p)}. Waktu kirim supplier ${p.lead_time_days} hari. ` +
      (p.recommended_order_qty > 0 ? `Saran: pesan ${p.recommended_order_qty} unit sekarang. ` : "Belum perlu dipesan. ") +
      (flags.length ? `Status: ${flags.join(", ")}.` : "Status aman.") +
      (p.demand_signal.lost_sales_30d ? ` Dalam 30 hari terakhir ${p.demand_signal.lost_sales_30d} unit permintaan tidak terlayani (${fmt(p.lost_revenue_30d)}).` : "") + note;
  }
  if (/pesan|order|beli|restock|reorder/.test(q)) {
    const rows = data.filter((p) => p.recommended_order_qty > 0).sort((a, b) => b.revenue_at_risk - a.revenue_at_risk);
    if (!rows.length) return "Saat ini tidak ada produk yang perlu dipesan: semua stok masih di atas titik pesan ulang." + note;
    return `Ada ${rows.length} produk yang perlu dipesan:\n` +
      rows.slice(0, 5).map((p) => `${line(p)} → pesan ${p.recommended_order_qty} unit`).join("\n") + note;
  }
  if (/habis|stockout|kosong|kritis|risiko|risk/.test(q)) {
    const rows = data.filter((p) => p.risk_flags.stockout_risk || p.risk_flags.out_of_stock);
    const lost = data.filter((p) => p.risk_flags.missed_revenue_flag).sort((a, b) => b.lost_revenue_30d - a.lost_revenue_30d);
    return (rows.length ? `${rows.length} produk sedang kosong atau berisiko habis sebelum kiriman tiba:\n${rows.slice(0, 5).map(line).join("\n")}` : "Tidak ada produk yang berisiko habis sebelum kiriman berikutnya.") +
      (lost.length ? `\n\nProduk yang paling banyak kehilangan penjualan dalam 30 hari terakhir:\n${lost.slice(0, 3).map((p) => `• ${p.product_name}: ${fmt(p.lost_revenue_30d)}`).join("\n")}` : "") + note;
  }
  if (/diskon|promo|overstock|menumpuk|berlebih|deadstock/.test(q)) {
    const rows = data.filter((p) => p.risk_flags.overstock_risk || p.risk_flags.deadstock_risk || p.risk_flags.promo_opportunity)
      .sort((a, b) => b.stock_coverage_days - a.stock_coverage_days);
    if (!rows.length) return "Tidak ada produk dengan stok berlebih saat ini." + note;
    return `${rows.length} produk punya stok berlebih atau penjualannya turun. Kandidat diskon:\n` + rows.slice(0, 5).map(line).join("\n") + note;
  }
  const reorder = data.filter((p) => p.recommended_order_qty > 0).length;
  const stockout = data.filter((p) => p.risk_flags.stockout_risk).length;
  const over = data.filter((p) => p.risk_flags.overstock_risk).length;
  return `Ringkasan: ${data.length} produk dipantau, ${reorder} perlu dipesan, ${stockout} berisiko habis, ${over} overstock. ` +
    "Coba tanyakan \"produk apa yang harus dipesan?\", \"produk mana yang berisiko habis?\", \"produk mana yang sebaiknya didiskon?\", atau sebut nama produk." + note;
}

// ─── Chat entry point ─────────────────────────────────────────────────────────

export interface ChatReply { text: string; source: "ai" | "rules" }

/** Wake a sleeping free-tier backend as soon as the user opens the chat. */
export function warmUpChat(): void {
  const base = DEMO ? CHAT_API : API_BASE;
  if (DEMO && !CHAT_API) return;
  fetch(`${base}/api/v1/health`).catch(() => undefined);
}

export async function sendChat(message: string, inventoryContext: unknown): Promise<ChatReply> {
  if (DEMO && !CHAT_API) return { text: await demoChat(message), source: "rules" };
  const base = DEMO ? CHAT_API : API_BASE;
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 75000);  // free servers can take ~1 min to wake up
  try {
    const res = await fetch(`${base}/api/v1/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message, inventory_context: inventoryContext ?? null }),
      signal: controller.signal,
    });
    if (!res.ok) await readError(res);
    return { text: (await res.json()).response, source: "ai" };
  } catch (err) {
    if (!DEMO) throw err;
    // Demo: if the AI server is asleep, unconfigured or rate-limited, answer from the data instead.
    const reason = err instanceof Error && err.name !== "AbortError" ? err.message : "server AI tidak merespons";
    return { text: `Server AI belum bisa dihubungi (${reason}).\n\n` + (await demoChat(message)), source: "rules" };
  } finally {
    clearTimeout(timer);
  }
}
