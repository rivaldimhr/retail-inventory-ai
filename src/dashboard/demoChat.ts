// Demo chat: answers questions with rules over the exported results (no AI model).
// Used when the dashboard runs as a static demo without an LLM API key.

export interface DemoProduct {
  product_id: string; product_name: string; category: string; unit_price: number;
  current_stock: number; on_order: number; stock_coverage_days: number; lead_time_days: number;
  reorder_point: number; safety_stock: number; recommended_order_qty: number;
  revenue_at_risk: number; lost_revenue_30d: number; trend_direction: string; days_since_last_sale: number;
  demand_signal: { forecast_7d: number; actual_last_7d: number; avg_sales_30d_actual: number; lost_sales_30d: number };
  risk_flags: Record<string, boolean>;
}
interface Rule { antecedents: string[]; consequents: string[]; confidence: number; lift: number; transactions: number }
interface Metrics {
  test_period: string[]; algorithm: string; mae_improvement_vs_best_baseline: number;
  metrics: Record<string, { mae: number; wape: number | null; bias: number | null }>;
  by_category: { category: string; mae: number; wape: number | null }[];
}
export interface DemoData {
  forecast: { metadata: { data_as_of: string }; data: DemoProduct[] };
  mba: { data: { rules: Rule[] } };
  metrics: { data: Metrics };
}

const NOTE = "\n\n(Mode demo: Chat AI belum aktif karena API key perlu disiapkan. Jawaban ini dibuat otomatis dari data.)";
const money = (v: number) => `£${Math.round(v).toLocaleString("en-GB")}`;
const price = (v: number) => `£${v.toFixed(2)}`;
const pct = (v: number) => `${(v * 100).toFixed(1)}%`;
const days = (d: number) => (d >= 999 ? "∞" : `${d} hari`);
const FLAG_LABEL: Record<string, string> = {
  out_of_stock: "stok kosong", stockout_risk: "berisiko habis sebelum kiriman tiba", overstock_risk: "overstock",
  deadstock_risk: "deadstock", promo_opportunity: "peluang promo", missed_revenue_flag: "sempat kehilangan penjualan",
};
const TREND: Record<string, string> = { INCREASING: "naik", DECREASING: "turun", STABLE: "stabil" };
const STOP = new Set(["of", "the", "and", "set", "pack", "design", "red", "white", "pink", "blue",
  "green", "black", "cream", "assorted", "colour", "colours", "retrospot", "vintage", "yang", "dan", "apa", "ini", "itu", "untuk"]);

const short = (p: DemoProduct) =>
  `• ${p.product_name}: stok ${p.current_stock}${p.on_order ? ` (+${p.on_order} dikirim)` : ""}, prediksi 7 hari ${p.demand_signal.forecast_7d} unit, cukup ${days(p.stock_coverage_days)}`;
const list = (rows: DemoProduct[], n = 5, extra?: (p: DemoProduct) => string) =>
  rows.slice(0, n).map((p) => short(p) + (extra ? extra(p) : "")).join("\n") + (rows.length > n ? `\n…dan ${rows.length - n} produk lainnya.` : "");
const words = (t: string) => t.toLowerCase().replace(/[^a-z0-9 ]/g, " ").split(/\s+/).filter((w) => w.length > 2 && !STOP.has(w));

/** Products named in the question: exact code / name, or the best word overlap. */
function findProducts(q: string, data: DemoProduct[]): DemoProduct[] {
  const exact = data.filter((p) => q.includes(p.product_name.toLowerCase()) || new RegExp(`\\b${p.product_id.toLowerCase()}\\b`).test(q));
  if (exact.length) return exact;
  const qw = new Set(words(q));
  const scored = data
    .map((p) => { const pw = words(p.product_name); const hit = pw.filter((w) => qw.has(w)).length; return { p, hit, ratio: pw.length ? hit / pw.length : 0 }; })
    .filter((x) => x.hit >= 2 || (x.hit === 1 && x.ratio >= 0.5))
    .sort((a, b) => b.hit - a.hit || b.ratio - a.ratio);
  return scored.length ? scored.filter((x) => x.hit === scored[0].hit).slice(0, 3).map((x) => x.p) : [];
}

function findCategory(q: string, data: DemoProduct[]): string | null {
  const cats = [...new Set(data.map((p) => p.category))];
  return cats.find((c) => c.toLowerCase().split(/[ &]+/).filter((w) => w.length > 3).some((w) => q.includes(w.replace(/s$/, "")))) ?? null;
}

function explainProduct(p: DemoProduct, rules: Rule[]): string {
  const d = p.demand_signal;
  const flags = Object.entries(p.risk_flags).filter(([, v]) => v).map(([k]) => FLAG_LABEL[k] ?? k);
  const lines = [
    `📦 ${p.product_name} (${p.product_id}, ${p.category}, ${price(p.unit_price)}/unit)`,
    `• Stok sekarang ${p.current_stock} unit${p.on_order ? `, ${p.on_order} unit sedang dikirim` : ""}. Cukup untuk ${days(p.stock_coverage_days)}.`,
    `• Prediksi 7 hari ke depan: ${d.forecast_7d} unit (7 hari terakhir terjual ${d.actual_last_7d} unit, tren ${TREND[p.trend_direction] ?? p.trend_direction}).`,
    `• Waktu kirim supplier ${p.lead_time_days} hari · titik pesan ulang ${p.reorder_point} · stok pengaman ${p.safety_stock}.`,
  ];
  if (p.recommended_order_qty > 0) lines.push(`• Saran: pesan ${p.recommended_order_qty} unit sekarang (≈ ${money(p.recommended_order_qty * p.unit_price)}).`);
  else lines.push("• Belum perlu dipesan: stok + kiriman masih di atas titik pesan ulang.");
  if (p.revenue_at_risk > 0) lines.push(`• Tanpa pesanan baru, sekitar ${money(p.revenue_at_risk)} penjualan berisiko hilang sebelum kiriman tiba.`);
  if (d.lost_sales_30d > 0) lines.push(`• 30 hari terakhir ${d.lost_sales_30d} unit permintaan tidak terlayani (${money(p.lost_revenue_30d)}).`);
  lines.push(`• Status: ${flags.length ? flags.join(", ") : "aman"}.`);
  const pair = rules.find((r) => r.antecedents[0].toLowerCase() === p.product_name.toLowerCase() || r.consequents[0].toLowerCase() === p.product_name.toLowerCase());
  if (pair) {
    const other = pair.antecedents[0].toLowerCase() === p.product_name.toLowerCase() ? pair.consequents[0] : pair.antecedents[0];
    lines.push(`• Sering dibeli bersama: ${other} (lift ${pair.lift.toFixed(1)}×).`);
  }
  return lines.join("\n");
}

const HELP = `Saya bisa menjawab pertanyaan seperti:
• "Produk apa yang harus dipesan hari ini?"
• "Produk mana yang stoknya kosong / berisiko habis?"
• "Produk mana yang sebaiknya didiskon?" atau "Ada deadstock?"
• "Produk terlaris minggu depan?" · "Produk yang trennya naik / turun?"
• "Ringkasan kategori Kitchen" atau "Kategori mana yang paling berisiko?"
• "Berapa penjualan yang hilang?" · "Nilai yang berisiko?"
• "Produk apa yang sering dibeli bersamaan?" atau "Ide bundling untuk lunch bag"
• "Seberapa akurat prediksinya?"
• Sebut nama produk, misalnya "Jumbo Bag Red Retrospot", untuk penjelasan lengkap.`;

export function answerDemo(message: string, d: DemoData): string {
  const q = message.toLowerCase();
  const data = d.forecast.data;
  const rules = d.mba?.data?.rules ?? [];
  const has = (re: RegExp) => re.test(q);
  const sum = (rows: DemoProduct[], f: (p: DemoProduct) => number) => rows.reduce((s, p) => s + f(p), 0);
  const reorder = data.filter((p) => p.recommended_order_qty > 0).sort((a, b) => b.revenue_at_risk - a.revenue_at_risk || b.recommended_order_qty - a.recommended_order_qty);
  const empty = data.filter((p) => p.risk_flags.out_of_stock);
  const atRisk = data.filter((p) => p.risk_flags.stockout_risk);

  if (has(/^(hai|halo|hi|hello|pagi|siang|sore|malam)\b/) && q.length < 25)
    return `Halo! Saya asisten stok untuk ${data.length} produk (data per ${d.forecast.metadata.data_as_of}).\n\n${HELP}${NOTE}`;
  if (has(/bantuan|help|bisa apa|contoh pertanyaan|cara pakai/)) return HELP + NOTE;

  // Market basket
  if (has(/bersama|bundl|paket|cross.?sell|market basket|pasangan/)) {
    const named = findProducts(q, data);
    if (named.length) {
      const name = named[0].product_name.toLowerCase();
      const pairs = rules.filter((r) => r.antecedents[0].toLowerCase() === name || r.consequents[0].toLowerCase() === name).slice(0, 5);
      if (!pairs.length) return `Belum ada pasangan produk yang kuat untuk ${named[0].product_name} di data market basket.` + NOTE;
      return `Produk yang sering dibeli bersama ${named[0].product_name}:\n` + pairs.map((r) => {
        const other = r.antecedents[0].toLowerCase() === name ? r.consequents[0] : r.antecedents[0];
        return `• ${other}: ${r.transactions} invoice, confidence ${pct(r.confidence)}, lift ${r.lift.toFixed(1)}×`;
      }).join("\n") + "\n\nIde: jadikan paket bundling atau tampilkan sebagai \"sering dibeli bersama\"." + NOTE;
    }
    return "Pasangan produk paling kuat (cocok untuk bundling):\n" + rules.slice(0, 6).map((r) =>
      `• ${r.antecedents[0]} → ${r.consequents[0]}: ${pct(r.confidence)} pembeli juga membeli, lift ${r.lift.toFixed(1)}×`).join("\n") +
      "\n\nLift di atas 2 berarti hubungannya sangat kuat, bukan kebetulan." + NOTE;
  }

  // Model accuracy
  if (has(/akura|akurat|error|mae|wape|meleset|seberapa tepat|model/)) {
    const m = d.metrics?.data;
    if (!m) return "Data evaluasi model tidak tersedia." + NOTE;
    const acc = (w: number | null) => (w === null ? "-" : `${((1 - w) * 100).toFixed(1)}%`);
    const best = [...m.by_category].sort((a, b) => (a.wape ?? 1) - (b.wape ?? 1));
    return `Akurasi prediksi 7 hari (diuji ${m.test_period[0]} s.d. ${m.test_period[1]}):\n` +
      `• Model: ${acc(m.metrics.model.wape)} (rata-rata meleset ${m.metrics.model.mae.toFixed(1)} unit per produk per minggu)\n` +
      `• Rata-rata 28 hari: ${acc(m.metrics.baseline_avg_28_days.wape)}\n• Sama dengan 7 hari terakhir: ${acc(m.metrics.baseline_last_7_days.wape)}\n` +
      `• Model ${pct(m.mae_improvement_vs_best_baseline)} lebih akurat dari metode pembanding terbaik. Total prediksi semua produk hanya meleset ${pct(Math.abs(m.metrics.model.bias ?? 0))}.\n` +
      `• Kategori paling mudah ditebak: ${best[0].category} (${acc(best[0].wape)}); paling sulit: ${best[best.length - 1].category} (${acc(best[best.length - 1].wape)}).` + NOTE;
  }

  // Category questions
  const cat = findCategory(q, data);
  if (has(/kategori|category/) || (cat && !findProducts(q, data).length)) {
    if (cat) {
      const rows = data.filter((p) => p.category === cat);
      const r = rows.filter((p) => p.recommended_order_qty > 0);
      const top = [...rows].sort((a, b) => b.demand_signal.forecast_7d - a.demand_signal.forecast_7d);
      return `Ringkasan kategori ${cat} (${rows.length} produk):\n` +
        `• Perlu dipesan: ${r.length} · stok kosong: ${rows.filter((p) => p.risk_flags.out_of_stock).length} · overstock: ${rows.filter((p) => p.risk_flags.overstock_risk).length}\n` +
        `• Prediksi 7 hari: ${Math.round(sum(rows, (p) => p.demand_signal.forecast_7d)).toLocaleString("en-GB")} unit · penjualan hilang 30 hari: ${money(sum(rows, (p) => p.lost_revenue_30d))}\n` +
        `\nTerlaris minggu depan:\n${list(top, 3)}` + (r.length ? `\n\nPerlu dipesan:\n${list(r, 3, (p) => ` → pesan ${p.recommended_order_qty} unit`)}` : "") + NOTE;
    }
    const cats = [...new Set(data.map((p) => p.category))].map((c) => {
      const rows = data.filter((p) => p.category === c);
      return { c, n: rows.length, order: rows.filter((p) => p.recommended_order_qty > 0).length, lost: sum(rows, (p) => p.lost_revenue_30d) };
    }).sort((a, b) => b.lost - a.lost);
    return "Ringkasan per kategori (urut dari penjualan hilang terbesar):\n" +
      cats.map((x) => `• ${x.c}: ${x.n} produk, ${x.order} perlu dipesan, hilang ${money(x.lost)} (30 hari)`).join("\n") +
      "\n\nSebut nama kategori untuk detailnya, misalnya \"kategori kitchen\"." + NOTE;
  }

  // A specific product
  const named = findProducts(q, data);
  if (named.length === 1 || (named.length > 1 && q.includes(named[0].product_name.toLowerCase())))
    return explainProduct(named[0], rules) + NOTE;
  if (named.length > 1)
    return "Ada beberapa produk yang cocok. Maksudnya yang mana?\n" + named.map((p) => `• ${p.product_name} (${p.product_id})`).join("\n") + NOTE;

  if (has(/kosong|habis|stockout|stok.?out|kritis|risiko|bahaya|darurat/)) {
    let t = "";
    t += empty.length ? `${empty.length} produk sedang kosong di rak (penjualan hilang hari ini):\n${list(empty, 5, (p) => (p.on_order ? "" : " · belum ada kiriman"))}` : "Tidak ada produk yang stoknya kosong.";
    t += atRisk.length ? `\n\n${atRisk.length} produk akan habis sebelum kiriman berikutnya tiba:\n${list(atRisk, 5, (p) => ` → pesan ${p.recommended_order_qty} unit`)}` : "\n\nTidak ada produk lain yang berisiko habis sebelum kiriman tiba.";
    return t + NOTE;
  }
  if (has(/pesan|order|restock|reorder|beli dari supplier|belanja/)) {
    if (!reorder.length) return "Saat ini tidak ada produk yang perlu dipesan: semua stok masih di atas titik pesan ulang." + NOTE;
    return `Ada ${reorder.length} produk yang perlu dipesan, total ${reorder.reduce((s, p) => s + p.recommended_order_qty, 0).toLocaleString("en-GB")} unit (≈ ${money(sum(reorder, (p) => p.recommended_order_qty * p.unit_price))}):\n` +
      list(reorder, 8, (p) => ` → pesan ${p.recommended_order_qty} unit`) + "\n\nTip: klik \"Unduh daftar pesan\" di tabel untuk file CSV-nya." + NOTE;
  }
  if (has(/hilang|lost|rugi|kehilangan|nilai berisiko|revenue|pendapatan|uang/)) {
    const lost = [...data].sort((a, b) => b.lost_revenue_30d - a.lost_revenue_30d).filter((p) => p.lost_revenue_30d > 0);
    return `Penjualan yang hilang karena stok kosong (30 hari terakhir): ${money(sum(data, (p) => p.lost_revenue_30d))} dari ${lost.length} produk.\n` +
      `Penjualan yang berisiko hilang sebelum kiriman berikutnya: ${money(sum(data, (p) => p.revenue_at_risk))}.\n\nProduk dengan kehilangan terbesar:\n` +
      lost.slice(0, 5).map((p) => `• ${p.product_name}: ${money(p.lost_revenue_30d)} (${p.demand_signal.lost_sales_30d} unit)`).join("\n") + NOTE;
  }
  if (has(/deadstock|tidak laku|ga laku|nggak laku|mati/)) {
    const dead = data.filter((p) => p.risk_flags.deadstock_risk);
    return (dead.length ? `${dead.length} produk tidak terjual ≥ 60 hari tetapi masih ada stok:\n` + dead.map((p) => `• ${p.product_name}: stok ${p.current_stock}, terakhir terjual ${p.days_since_last_sale} hari lalu (nilai ≈ ${money(p.current_stock * p.unit_price)})`).join("\n") + "\n\nSaran: cuci gudang atau jadikan bonus bundling." : "Tidak ada deadstock.") + NOTE;
  }
  if (has(/diskon|promo|overstock|menumpuk|berlebih|kebanyakan|sale/)) {
    const rows = data.filter((p) => p.risk_flags.overstock_risk || p.risk_flags.promo_opportunity).sort((a, b) => b.stock_coverage_days - a.stock_coverage_days);
    if (!rows.length) return "Tidak ada produk dengan stok berlebih saat ini." + NOTE;
    return `${rows.length} produk punya stok berlebih atau penjualannya turun. Kandidat diskon (stok paling lama habis):\n` +
      list(rows, 6, (p) => ` · nilai stok ≈ ${money(p.current_stock * p.unit_price)}`) + NOTE;
  }
  if (has(/terlaris|laris|paling banyak|best.?sell|top|populer|favorit/)) {
    const top = [...data].sort((a, b) => b.demand_signal.forecast_7d - a.demand_signal.forecast_7d);
    return "Produk dengan prediksi penjualan tertinggi 7 hari ke depan:\n" + list(top, 8) + NOTE;
  }
  if (has(/naik|meningkat|tumbuh|trending|turun|menurun|tren/)) {
    const dir = has(/turun|menurun/) ? "DECREASING" : "INCREASING";
    const rows = data.filter((p) => p.trend_direction === dir).sort((a, b) => b.demand_signal.forecast_7d - a.demand_signal.forecast_7d);
    return `${rows.length} produk dengan tren ${TREND[dir]} (14 hari terakhir dibanding 14 hari sebelumnya):\n` + list(rows, 6, (p) => ` · 7 hari terakhir ${p.demand_signal.actual_last_7d} unit`) + NOTE;
  }
  if (has(/berapa|jumlah|total|ringkas|summary|kondisi|status|gambaran|overview/)) {
    return `Kondisi stok per ${d.forecast.metadata.data_as_of} (${data.length} produk):\n` +
      `• Perlu dipesan: ${reorder.length} · stok kosong: ${empty.length} · berisiko habis: ${atRisk.length}\n` +
      `• Overstock: ${data.filter((p) => p.risk_flags.overstock_risk).length} · deadstock: ${data.filter((p) => p.risk_flags.deadstock_risk).length}\n` +
      `• Prediksi total 7 hari: ${Math.round(sum(data, (p) => p.demand_signal.forecast_7d)).toLocaleString("en-GB")} unit\n` +
      `• Penjualan hilang 30 hari: ${money(sum(data, (p) => p.lost_revenue_30d))} · berisiko hilang: ${money(sum(data, (p) => p.revenue_at_risk))}` + NOTE;
  }
  return "Maaf, saya belum memahami pertanyaan itu.\n\n" + HELP + NOTE;
}
