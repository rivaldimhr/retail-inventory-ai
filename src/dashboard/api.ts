import { answerDemo, type DemoData } from "./demoChat";

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

// ─── Demo chat: rule-based answers from the exported data ─────────────────────

export async function demoChat(message: string): Promise<string> {
  const [forecast, mba, metrics] = await Promise.all([
    demoFile<DemoData["forecast"]>("forecast.json"),
    demoFile<DemoData["mba"]>("mba.json").catch(() => ({ data: { rules: [] } })),
    demoFile<DemoData["metrics"]>("metrics.json").catch(() => null as unknown as DemoData["metrics"]),
  ]);
  return answerDemo(message, { forecast, mba, metrics });
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
