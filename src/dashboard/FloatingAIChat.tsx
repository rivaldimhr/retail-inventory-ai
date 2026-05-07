import { useState, useRef, useEffect, useCallback } from "react";
import "./FloatingAIChat.css";

// ─── Types ────────────────────────────────────────────────────────────────────

interface Message {
  id: string;
  role: "user" | "assistant" | "error";
  content: string;
  ts: number;
}

interface InventoryContext {
  total_count: number;
  stockout_count: number;
  overstock_count: number;
  deadstock_count: number;
  lost_sales_count: number;
  generated_at: string;
}

interface FloatingAIChatProps {
  inventoryContext?: InventoryContext | null;
}

// ─── Constants ────────────────────────────────────────────────────────────────

const API_BASE = "http://localhost:8000";

const QUICK_PROMPTS = [
  "Produk mana yang paling berisiko stockout?",
  "Berikan rekomendasi untuk overstock.",
  "Ringkasan kondisi inventory hari ini.",
];

// ─── Icons ────────────────────────────────────────────────────────────────────

const RobotIcon = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"
    strokeLinecap="round" strokeLinejoin="round" width="24" height="24">
    <rect x="3" y="11" width="18" height="10" rx="2" />
    <rect x="8" y="15" width="2" height="2" rx="0.5" fill="currentColor" stroke="none" />
    <rect x="14" y="15" width="2" height="2" rx="0.5" fill="currentColor" stroke="none" />
    <path d="M8 11V8a4 4 0 0 1 8 0v3" />
    <circle cx="12" cy="4" r="1.5" fill="currentColor" stroke="none" />
    <line x1="12" y1="5.5" x2="12" y2="7" />
    <line x1="3" y1="16" x2="1" y2="16" />
    <line x1="23" y1="16" x2="21" y2="16" />
  </svg>
);

const CloseIcon = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"
    strokeLinecap="round" width="14" height="14">
    <line x1="18" y1="6" x2="6" y2="18" />
    <line x1="6" y1="6" x2="18" y2="18" />
  </svg>
);

const SendIcon = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
    strokeLinecap="round" strokeLinejoin="round" width="16" height="16">
    <line x1="22" y1="2" x2="11" y2="13" />
    <polygon points="22 2 15 22 11 13 2 9 22 2" fill="currentColor" stroke="none" />
  </svg>
);

// ─── Sub-components ───────────────────────────────────────────────────────────

function TypingIndicator() {
  return (
    <div className="fai-msg fai-msg--assistant">
      <div className="fai-msg-avatar"><RobotIcon /></div>
      <div className="fai-msg-bubble fai-msg-bubble--typing">
        <span /><span /><span />
      </div>
    </div>
  );
}

function ChatMessage({ msg }: { msg: Message }) {
  const isUser = msg.role === "user";
  const isError = msg.role === "error";
  return (
    <div className={`fai-msg ${isUser ? "fai-msg--user" : "fai-msg--assistant"}`}>
      {!isUser && (
        <div className={`fai-msg-avatar ${isError ? "fai-msg-avatar--error" : ""}`}>
          <RobotIcon />
        </div>
      )}
      <div className={`fai-msg-bubble ${isError ? "fai-msg-bubble--error" : ""}`}>
        {msg.content}
      </div>
    </div>
  );
}

// ─── Main Component ───────────────────────────────────────────────────────────

export default function FloatingAIChat({ inventoryContext }: FloatingAIChatProps) {
  const [open, setOpen] = useState(false);
  const [visible, setVisible] = useState(false);
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "welcome",
      role: "assistant",
      content: "Halo! Saya AI Analyst untuk inventory Anda. Tanyakan apa saja tentang stok, risiko, atau rekomendasi.",
      ts: Date.now(),
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);

  const chatRef = useRef<HTMLDivElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (open) {
      setVisible(true);
      setTimeout(() => inputRef.current?.focus(), 300);
    } else {
      const t = setTimeout(() => setVisible(false), 250);
      return () => clearTimeout(t);
    }
  }, [open]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (chatRef.current && !chatRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    if (open) document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [open]);

  const sendMessage = useCallback(async (text: string) => {
    const trimmed = text.trim();
    if (!trimmed || loading) return;

    const userMsg: Message = { id: crypto.randomUUID(), role: "user", content: trimmed, ts: Date.now() };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setLoading(true);

    try {
      const res = await fetch(`${API_BASE}/api/v1/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: trimmed,
          inventory_context: inventoryContext ?? null,
        }),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error((err as { detail?: string }).detail ?? `HTTP ${res.status}`);
      }

      const data = await res.json();
      const aiMsg: Message = {
        id: crypto.randomUUID(),
        role: "assistant",
        content: data.response,
        ts: Date.now(),
      };
      setMessages((prev) => [...prev, aiMsg]);
    } catch (err) {
      const errorMsg: Message = {
        id: crypto.randomUUID(),
        role: "error",
        content: err instanceof Error ? err.message : "Gagal menghubungi AI service.",
        ts: Date.now(),
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setLoading(false);
    }
  }, [loading, inventoryContext]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage(input);
    }
  };

  const unreadCount = !open ? messages.filter((m) => m.role === "assistant" && m.id !== "welcome").length : 0;

  return (
    <div className="fai-root" ref={chatRef}>
      {visible && (
        <div className={`fai-popup ${open ? "fai-popup--open" : "fai-popup--close"}`}>
          {/* Header */}
          <div className="fai-popup-header">
            <div className="fai-popup-title-group">
              <div className="fai-popup-avatar"><RobotIcon /></div>
              <div>
                <div className="fai-popup-title">AI Analyst</div>
                <div className="fai-popup-subtitle">
                  {loading ? (
                    <span className="fai-status-thinking">Sedang menganalisis...</span>
                  ) : (
                    <span className="fai-status-online">● Online</span>
                  )}
                </div>
              </div>
            </div>
            <button className="fai-close-btn" onClick={() => setOpen(false)} aria-label="Tutup chat">
              <CloseIcon />
            </button>
          </div>

          {/* Context bar */}
          {inventoryContext && (
            <div className="fai-context-bar">
              <span className="fai-context-item fai-context-danger">{inventoryContext.stockout_count} Stockout</span>
              <span className="fai-context-sep">·</span>
              <span className="fai-context-item fai-context-warning">{inventoryContext.overstock_count} Overstock</span>
              <span className="fai-context-sep">·</span>
              <span className="fai-context-item fai-context-muted">{inventoryContext.total_count} Produk</span>
            </div>
          )}

          {/* Messages */}
          <div className="fai-messages">
            {messages.map((msg) => (
              <ChatMessage key={msg.id} msg={msg} />
            ))}
            {loading && <TypingIndicator />}
            <div ref={messagesEndRef} />
          </div>

          {/* Quick prompts */}
          {messages.length <= 1 && !loading && (
            <div className="fai-quick-prompts">
              {QUICK_PROMPTS.map((q) => (
                <button key={q} className="fai-quick-btn" onClick={() => sendMessage(q)}>
                  {q}
                </button>
              ))}
            </div>
          )}

          {/* Input */}
          <div className="fai-input-row">
            <div className="fai-input-area">
              <input
                ref={inputRef}
                className="fai-input"
                type="text"
                placeholder="Tanya tentang inventory..."
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                disabled={loading}
                maxLength={500}
              />
              <button
                className={`fai-send-btn ${input.trim() && !loading ? "fai-send-btn--active" : ""}`}
                onClick={() => sendMessage(input)}
                disabled={!input.trim() || loading}
                aria-label="Kirim"
              >
                <SendIcon />
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Trigger */}
      <button
        className={`fai-trigger ${open ? "fai-trigger--active" : ""}`}
        onClick={() => setOpen((p) => !p)}
        aria-label="Buka AI Analyst"
      >
        <span className={`fai-trigger-icon ${open ? "fai-trigger-icon--rotated" : ""}`}>
          <RobotIcon />
        </span>
        {!open && unreadCount > 0 && (
          <span className="fai-badge">{unreadCount > 9 ? "9+" : unreadCount}</span>
        )}
        {!open && <span className="fai-trigger-pulse" />}
      </button>
    </div>
  );
}
