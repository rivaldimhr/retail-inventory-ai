import { useState, useRef, useEffect } from "react";
import "./FloatingAIChat.css";

const RobotIcon = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" width="26" height="26">
    <rect x="3" y="11" width="18" height="10" rx="2" />
    <rect x="8" y="15" width="2" height="2" rx="0.5" fill="currentColor" stroke="none" />
    <rect x="14" y="15" width="2" height="2" rx="0.5" fill="currentColor" stroke="none" />
    <path d="M8 11V8a4 4 0 0 1 8 0v3" />
    <line x1="12" y1="4" x2="12" y2="6" />
    <circle cx="12" cy="3.5" r="1" fill="currentColor" stroke="none" />
    <line x1="3" y1="16" x2="1" y2="16" />
    <line x1="23" y1="16" x2="21" y2="16" />
    <line x1="10" y1="21" x2="10" y2="23" />
    <line x1="14" y1="21" x2="14" y2="23" />
  </svg>
);

const CloseIcon = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" width="14" height="14">
    <line x1="18" y1="6" x2="6" y2="18" />
    <line x1="6" y1="6" x2="18" y2="18" />
  </svg>
);

const SparkleIcon = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" width="14" height="14">
    <path d="M12 3l1.5 4.5L18 9l-4.5 1.5L12 15l-1.5-4.5L6 9l4.5-1.5z" fill="currentColor" stroke="none" opacity="0.8"/>
    <path d="M19 3l0.75 2.25L22 6l-2.25.75L19 9l-.75-2.25L16 6l2.25-.75z" fill="currentColor" stroke="none" opacity="0.6"/>
    <path d="M5 15l0.5 1.5L7 17l-1.5.5L5 19l-.5-1.5L3 17l1.5-.5z" fill="currentColor" stroke="none" opacity="0.5"/>
  </svg>
);

const PLACEHOLDER_INSIGHTS = [
  {
    label: "Stockout Alert",
    text: "3 produk berisiko kehabisan stok dalam 24 jam ke depan berdasarkan tren permintaan saat ini.",
    variant: "insight-danger",
  },
  {
    label: "Overstock Detected",
    text: "5 SKU menunjukkan pola overstock. Pertimbangkan promosi untuk mempercepat perputaran stok.",
    variant: "insight-warning",
  },
  {
    label: "Demand Spike",
    text: "Kategori Electronics mencatat lonjakan demand +32% dibanding rata-rata 30 hari terakhir.",
    variant: "insight-info",
  },
];

export default function FloatingAIChat() {
  const [open, setOpen] = useState(false);
  const [visible, setVisible] = useState(false);
  const chatRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (open) {
      setVisible(true);
    } else {
      const timer = setTimeout(() => setVisible(false), 250);
      return () => clearTimeout(timer);
    }
  }, [open]);

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (chatRef.current && !chatRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    if (open) document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [open]);

  return (
    <div className="fai-root" ref={chatRef}>
      {visible && (
        <div className={`fai-popup ${open ? "fai-popup--open" : "fai-popup--close"}`}>
          <div className="fai-popup-header">
            <div className="fai-popup-title-group">
              <div className="fai-popup-avatar">
                <RobotIcon />
              </div>
              <div>
                <div className="fai-popup-title">AI Analysis</div>
                <div className="fai-popup-subtitle">Inventory Intelligence</div>
              </div>
            </div>
            <button className="fai-close-btn" onClick={() => setOpen(false)} aria-label="Tutup chat">
              <CloseIcon />
            </button>
          </div>

          <div className="fai-popup-body">
            <div className="fai-greeting">
              <SparkleIcon />
              <span>Halo! Berikut ringkasan analisis inventory hari ini.</span>
            </div>

            <div className="fai-insights">
              {PLACEHOLDER_INSIGHTS.map((insight) => (
                <div key={insight.label} className={`fai-insight-card ${insight.variant}`}>
                  <div className="fai-insight-label">{insight.label}</div>
                  <div className="fai-insight-text">{insight.text}</div>
                </div>
              ))}
            </div>

            <div className="fai-input-area">
              <input
                className="fai-input"
                type="text"
                placeholder="Tanya sesuatu tentang inventory..."
                readOnly
              />
              <button className="fai-send-btn" disabled aria-label="Kirim">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" width="16" height="16">
                  <line x1="22" y1="2" x2="11" y2="13" />
                  <polygon points="22 2 15 22 11 13 2 9 22 2" />
                </svg>
              </button>
            </div>

            <div className="fai-disclaimer">
              AI integration belum aktif — ini adalah UI placeholder.
            </div>
          </div>
        </div>
      )}

      <button
        className={`fai-trigger ${open ? "fai-trigger--active" : ""}`}
        onClick={() => setOpen((prev) => !prev)}
        aria-label="Buka AI Assistant"
      >
        <span className={`fai-trigger-icon ${open ? "fai-trigger-icon--rotated" : ""}`}>
          <RobotIcon />
        </span>
        <span className="fai-trigger-pulse" />
      </button>
    </div>
  );
}
