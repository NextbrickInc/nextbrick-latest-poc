// ─── components/assistant/ChatPanel.tsx ──────────────────────────────────────
// Full-featured agentic chat panel — styled after the provided reference UI.
// Reads/writes from Redux chatSlice. Shows tool-call badges, citations,
// latency, and a suggested-prompts carousel when the chat is empty.
import { useRef, useEffect, useState } from "react";
import {
  Bot, Send, Sparkles, User, Wrench, AlertCircle,
  ChevronRight, Clock, Zap, Brain
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { useAppDispatch, useAppSelector } from "@/store/hooks";
import {
  sendMessage,
  selectActiveMessages,
  selectChatStatus,
  selectChatError,
  clearError,
  selectActiveSessionId,
} from "@/store/slices/chatSlice";

// ── Suggested prompts ─────────────────────────────────────────────────────────
const SUGGESTED_PROMPTS = [
  { text: "Where is my order?", icon: "📦", category: "Salesforce" },
  { text: "Give me cal certificate for this asset", icon: "📋", category: "Calibration" },
  { text: "What is the price of DSOX1202A in US?", icon: "💰", category: "Pricing" },
  { text: "Find the instructions manual of U1610A", icon: "📄", category: "AEM DAM" },
  { text: "Create a support case", icon: "🎫", category: "Salesforce" },
  { text: "What is my service order status?", icon: "🔧", category: "Service" },
  { text: "How do I make an eye diagram using ADS?", icon: "📡", category: "Knowledge" },
  { text: "Are there any products with 2 GSa/s?", icon: "🔍", category: "Search" },
];

// Colour map for tool badge colours
const TOOL_COLOURS: Record<string, string> = {
  "salesforce": "border-blue-500/40 bg-blue-500/10 text-blue-400",
  "pricing": "border-yellow-500/40 bg-yellow-500/10 text-yellow-400",
  "calibration": "border-green-500/40 bg-green-500/10 text-green-400",
  "elasticsearch": "border-purple-500/40 bg-purple-500/10 text-purple-400",
  "aem": "border-orange-500/40 bg-orange-500/10 text-orange-400",
  "confluence": "border-teal-500/40 bg-teal-500/10 text-teal-400",
  "email": "border-pink-500/40 bg-pink-500/10 text-pink-400",
  "snowflake": "border-sky-500/40 bg-sky-500/10 text-sky-400",
};

function toolColour(tool: string) {
  const key = Object.keys(TOOL_COLOURS).find((k) => tool.toLowerCase().includes(k));
  return key ? TOOL_COLOURS[key] : "border-border bg-secondary text-muted-foreground";
}

// ── Component ────────────────────────────────────────────────────────────────
export default function ChatPanel() {
  const dispatch = useAppDispatch();
  const messages = useAppSelector(selectActiveMessages);
  const chatStatus = useAppSelector(selectChatStatus);
  const chatError = useAppSelector(selectChatError);
  const modelName = useAppSelector((s) => s.model.name);
  const activeId = useAppSelector(selectActiveSessionId);

  const [inputValue, setInputValue] = useState("");
  const messagesContainerRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const isLoading = chatStatus === "sending";

  // Auto-scroll INSIDE the messages box only — never moves the page
  useEffect(() => {
    const el = messagesContainerRef.current;
    if (!el) return;
    el.scrollTop = el.scrollHeight;
  }, [messages]);

  // Clear error after 5s
  useEffect(() => {
    if (chatError) {
      const t = setTimeout(() => dispatch(clearError()), 5000);
      return () => clearTimeout(t);
    }
  }, [chatError, dispatch]);

  // Clear input when session changes (New Chat)
  useEffect(() => {
    setInputValue("");
    inputRef.current?.focus();
  }, [activeId]);

  const handleSend = () => {
    const text = inputValue.trim();
    if (!text || isLoading) return;
    setInputValue("");
    dispatch(sendMessage({ sessionId: activeId, message: text }));
  };

  const handleKey = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  // Show only the last ~20 messages to keep scroll snappy
  const visibleMessages = messages.slice(-20);
  const isEmpty = visibleMessages.length <= 1; // only greeting

  return (
    <div className="flex flex-col rounded-2xl border border-border bg-card overflow-hidden shadow-lg">
      {/* ── Panel header */}
      <div className="flex items-center justify-between border-b border-border px-4 py-2.5 bg-gradient-to-r from-primary/5 to-transparent">
        <div className="flex items-center gap-2.5">
          <img src="/image.png" alt="Nextbrick AI" className="h-10 w-10 object-contain drop-shadow-sm" />
          <div>
            <p className="text-sm font-bold text-foreground leading-none">Nextbrick AI Assistant</p>
            <p className="mt-0.5 text-[10px] text-muted-foreground flex items-center gap-1">
              <Brain className="h-2.5 w-2.5 text-primary" />
              {modelName || "Model not configured"} · Plan → Retrieve → Act
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {isLoading && (
            <Badge variant="outline" className="gap-1 border-yellow-500/40 bg-yellow-500/10 text-yellow-400 text-[10px] animate-pulse">
              <Zap className="h-2.5 w-2.5" />
              Thinking…
            </Badge>
          )}
          <Badge variant="outline" className="gap-1 text-[10px] border-green-500/40 bg-green-500/10 text-green-400">
            <span className="h-1.5 w-1.5 rounded-full bg-green-500 animate-pulse" />
            Live
          </Badge>
        </div>
      </div>

      {/* ── Messages area */}
      <div ref={messagesContainerRef} className="flex-1 overflow-y-auto px-4 py-4 space-y-4 min-h-[340px] max-h-[500px]">

        {/* Empty state — show suggested prompts */}
        {isEmpty && (
          <div className="pb-2">
            <p className="mb-3 flex items-center gap-1.5 text-xs text-muted-foreground">
              <Sparkles className="h-3 w-3 text-primary" />
              Try asking one of these:
            </p>
            <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
              {SUGGESTED_PROMPTS.map(({ text, icon, category }) => (
                <button
                  key={text}
                  className="flex items-start gap-2.5 rounded-lg border border-border bg-background p-2.5 text-left text-xs hover:bg-accent hover:border-primary/30 transition-colors group"
                  onClick={() => {
                    setInputValue(text);
                    inputRef.current?.focus();
                  }}
                >
                  <span className="text-base leading-none">{icon}</span>
                  <div className="min-w-0">
                    <span className="text-foreground group-hover:text-primary transition-colors line-clamp-2">
                      {text}
                    </span>
                    <span className="mt-0.5 block text-[10px] text-muted-foreground">{category}</span>
                  </div>
                  <ChevronRight className="ml-auto h-3 w-3 shrink-0 text-muted-foreground group-hover:text-primary transition-colors" />
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Messages */}
        {visibleMessages.map((msg) => {
          const isIntro = msg.id === messages[0]?.id && msg.role === "assistant";
          return (
            <div
              key={msg.id}
              className={`flex gap-3 ${msg.role === "user" ? "flex-row-reverse" : "flex-row"}`}
            >
              {/* Avatar */}
              <div className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-full 
              ${msg.role === "user"
                  ? "bg-primary/20 text-primary"
                  : msg.error
                    ? "bg-destructive/20 text-destructive"
                    : "bg-primary shadow-md shadow-primary/20 text-primary-foreground"
                }`}
              >
                {msg.role === "user"
                  ? <User className="h-3.5 w-3.5" />
                  : msg.error
                    ? <AlertCircle className="h-3.5 w-3.5" />
                    : <Bot className="h-3.5 w-3.5" />
                }
              </div>

              {/* Bubble */}
              <div className={`flex max-w-[82%] flex-col gap-1.5 ${msg.role === "user" ? "items-end" : "items-start"}`}>
                <div
                  className={`rounded-2xl px-3.5 py-2.5 leading-relaxed ${isIntro ? "text-base" : "text-sm"}
                  ${msg.role === "user"
                      ? "bg-primary text-primary-foreground rounded-tr-sm"
                      : msg.error
                        ? "bg-destructive/10 text-destructive border border-destructive/20 rounded-tl-sm"
                        : "bg-secondary text-foreground rounded-tl-sm"
                    }`}
                >
                  {msg.text}
                </div>

                {/* Tool calls */}
                {msg.tool_calls && msg.tool_calls.length > 0 && (
                  <div className="flex flex-wrap gap-1">
                    {msg.tool_calls.map((tc, i) => (
                      <Badge
                        key={i}
                        variant="outline"
                        className={`gap-1 text-[10px] h-5 ${toolColour(tc.tool)}`}
                      >
                        <Wrench className="h-2.5 w-2.5" />
                        {tc.tool}
                      </Badge>
                    ))}
                  </div>
                )}

                {/* Citations */}
                {msg.citations && msg.citations.length > 0 && (
                  <div className="flex flex-wrap gap-1">
                    {msg.citations.map((c, i) => (
                      <Badge
                        key={i}
                        variant="outline"
                        className="gap-1 text-[10px] h-5 border-muted-foreground/30 text-muted-foreground"
                      >
                        📎 {c}
                      </Badge>
                    ))}
                  </div>
                )}

                {/* Meta row */}
                <div className="flex items-center gap-2 text-[10px] text-muted-foreground">
                  {msg.latencyMs != null && (
                    <span className="flex items-center gap-0.5">
                      <Clock className="h-2.5 w-2.5" />
                      {msg.latencyMs}ms
                    </span>
                  )}
                  {msg.model && (
                    <span className="flex items-center gap-0.5">
                      <Sparkles className="h-2.5 w-2.5" />
                      {msg.model}
                    </span>
                  )}
                </div>
              </div>
            </div>
          );
        })}

        {/* Typing indicator */}
        {isLoading && (
          <div className="flex gap-3">
            <div className="flex h-7 w-7 items-center justify-center rounded-full bg-primary shadow-md shadow-primary/20">
              <Bot className="h-3.5 w-3.5 text-primary-foreground" />
            </div>
            <div className="flex items-center gap-1.5 rounded-2xl rounded-tl-sm bg-secondary px-4 py-3">
              <span className="h-1.5 w-1.5 rounded-full bg-muted-foreground animate-bounce [animation-delay:0ms]" />
              <span className="h-1.5 w-1.5 rounded-full bg-muted-foreground animate-bounce [animation-delay:150ms]" />
              <span className="h-1.5 w-1.5 rounded-full bg-muted-foreground animate-bounce [animation-delay:300ms]" />
            </div>
          </div>
        )}


      </div>

      {/* ── Input area ────────────────────────────────────────────────────── */}
      <div className="border-t border-border p-3 bg-card">
        <div className="flex items-end gap-2">
          <textarea
            ref={inputRef}
            rows={1}
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={handleKey}
            placeholder="Type a message or ask a question…"
            disabled={isLoading}
            className="flex-1 resize-none rounded-lg border border-input bg-background px-3.5 py-2.5 text-sm outline-none
              placeholder:text-muted-foreground focus:border-primary focus:ring-1 focus:ring-primary/30
              disabled:opacity-50 transition-colors min-h-[40px] max-h-[120px]"
            style={{ fieldSizing: "content" } as React.CSSProperties}
          />
          <button
            onClick={handleSend}
            disabled={!inputValue.trim() || isLoading}
            className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary text-primary-foreground
              shadow-md shadow-primary/20 hover:bg-primary/90 disabled:opacity-40
              transition-all hover:scale-105 active:scale-95"
            aria-label="Send message"
          >
            <Send className="h-4 w-4" />
          </button>
        </div>
        <p className="mt-1.5 text-center text-[10px] text-muted-foreground">
          Nextbrick AI may make mistakes. Validate critical information.
        </p>
      </div>
    </div>
  );
}
