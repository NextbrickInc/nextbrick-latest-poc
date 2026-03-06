import React, { useState, useEffect, useRef } from "react";
import {
  MessageSquare, X, Bot, User, Send, ChevronDown, Cpu, Database, Globe,
  Brain, Wrench, Clock, Sparkles, Copy, ThumbsUp, ThumbsDown,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { MarkdownMessage } from "@/components/assistant/MarkdownMessage";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

// ── Types ────────────────────────────────────────────────────────────────────

interface ToolCall {
  tool: string;
  status: string;
  detail: string;
}

interface FloatingMessage {
  role: "user" | "assistant";
  content: string;
  thinkingSteps?: string[];
  tool_calls?: ToolCall[];
  citations?: string[];
  latencyMs?: number | null;
  inputTokens?: number | null;
  outputTokens?: number | null;
  model?: string | null;
}

// ── Constants ────────────────────────────────────────────────────────────────

const THINKING_STEPS = [
  { label: "Planning", icon: "🧠", color: "text-blue-500" },
  { label: "Retrieving", icon: "🔍", color: "text-purple-500" },
  { label: "Acting", icon: "⚡", color: "text-yellow-500" },
];

const MODEL_OPTIONS = [
  { id: "qwen3-coder:480b-cloud", label: "Qwen3 480B" },
  { id: "mistral-nemo:12b", label: "Mistral Nemo 12B" },
  { id: "qwen2.5:14b-instruct-q4_k_m", label: "Qwen2.5 14B" },
  { id: "mixtral:8x7b-instruct-v0.1-q4_K_M", label: "Mixtral 8x7B" },
  { id: "gpt-oss:120b-cloud", label: "GPT-OSS 120B" },
  { id: "gpt-5.2", label: "ChatGPT 5.2" },
  { id: "gemini-3", label: "Gemini 3" },
  { id: "claude-3.6-sonnet", label: "Claude Sonnet 4.6" },
  { id: "claude-3.6-opus", label: "Claude Opus 4.6" },
  { id: "grok-4", label: "Grok 4" },
];

const DATA_SOURCE_OPTIONS = [
  { id: "auto", label: "Auto" },
  { id: "coveo", label: "Coveo" },
  { id: "aem_dam", label: "AEM DAM" },
  { id: "aem_pages", label: "AEM Pages" },
  { id: "confluence", label: "Confluence" },
  { id: "salesforce", label: "Salesforce" },
  { id: "pim", label: "PIM" },
  { id: "skilljar_lms", label: "Skilljar LMS" },
  { id: "oracle", label: "Oracle" },
  { id: "snowflake", label: "Snowflake" },
];

const LANGUAGE_OPTIONS = [
  { id: "en", label: "English" },
  { id: "de", label: "German" },
  { id: "es", label: "Spanish" },
  { id: "zh-Hans", label: "Simplified Chinese" },
  { id: "zh-Hant", label: "Traditional Chinese" },
  { id: "ja", label: "Japanese" },
  { id: "ko", label: "Korean" },
  { id: "fr", label: "French" },
];

// Tool badge colour map (matches ChatPanel)
const TOOL_COLOURS: Record<string, string> = {
  salesforce: "border-blue-500/40 bg-blue-500/10 text-blue-400",
  pricing: "border-yellow-500/40 bg-yellow-500/10 text-yellow-400",
  calibration: "border-green-500/40 bg-green-500/10 text-green-400",
  elasticsearch: "border-purple-500/40 bg-purple-500/10 text-purple-400",
  aem: "border-orange-500/40 bg-orange-500/10 text-orange-400",
  confluence: "border-teal-500/40 bg-teal-500/10 text-teal-400",
  email: "border-pink-500/40 bg-pink-500/10 text-pink-400",
  snowflake: "border-sky-500/40 bg-sky-500/10 text-sky-400",
};

function toolColour(tool: string) {
  const key = Object.keys(TOOL_COLOURS).find((k) => tool.toLowerCase().includes(k));
  return key ? TOOL_COLOURS[key] : "border-border bg-secondary text-muted-foreground";
}

// ── Thinking animation ──────────────────────────────────────────────────────

function ThinkingSteps() {
  const [step, setStep] = useState(0);
  useEffect(() => {
    const interval = setInterval(() => setStep((s) => (s < 2 ? s + 1 : s)), 2000);
    return () => clearInterval(interval);
  }, []);
  return (
    <div className="space-y-2 py-1">
      {THINKING_STEPS.map((s, i) => (
        <div
          key={s.label}
          className={
            "flex items-center gap-2 text-[11px] transition-opacity duration-500 " +
            (i > step ? "opacity-30" : "opacity-100")
          }
        >
          <span className={i <= step ? "text-green-500" : s.color}>
            {i <= step ? "✓" : s.icon}
          </span>
          <span className="font-medium text-foreground/80">
            {s.label}
            {i === step ? "..." : ""}
          </span>
        </div>
      ))}
    </div>
  );
}

// ── FloatingChat component ──────────────────────────────────────────────────

export default function FloatingChat() {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<FloatingMessage[]>([
    { role: "assistant", content: "Hello! I am Keysight's AI Assistant. How can I help you today?" },
  ]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [selectedModel, setSelectedModel] = useState(MODEL_OPTIONS[0]?.id ?? "gpt-oss:120b-cloud");
  const [selectedSource, setSelectedSource] = useState("auto");
  const [routingMode, setRoutingMode] = useState<"auto" | "manual">("auto");
  const [selectedLanguage, setSelectedLanguage] = useState(() => {
    if (typeof window !== "undefined") {
      return window.localStorage.getItem("keysight.language") || "en";
    }
    return "en";
  });
  const sessionIdRef = useRef<string>("");
  if (!sessionIdRef.current && typeof crypto !== "undefined" && crypto.randomUUID) {
    sessionIdRef.current = crypto.randomUUID().slice(0, 8);
  }
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading]);

  // Sync language with Navbar/ChatPanel (localStorage)
  useEffect(() => {
    if (!open || typeof window === "undefined") return;
    const stored = window.localStorage.getItem("keysight.language");
    if (stored && stored !== selectedLanguage) setSelectedLanguage(stored);
  }, [open, selectedLanguage]);

  const [thumbsState, setThumbsState] = useState<Record<number, "up" | "down" | null>>({});

  const sendFeedback = async (msgIndex: number, signal: "thumbs_up" | "thumbs_down", query?: string) => {
    setThumbsState((prev) => ({ ...prev, [msgIndex]: signal === "thumbs_up" ? "up" : "down" }));
    try {
      await fetch("/api/user/feedback", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_id: sessionIdRef.current || "anonymous",
          signal,
          query: query || "",
          message_id: `${sessionIdRef.current}-${msgIndex}`,
        }),
      });
    } catch {
      // silently ignore
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const userMsg = input.trim();
    setInput("");
    const historyForApi = messages.map((m) => ({ role: m.role, content: m.content }));
    setMessages((prev) => [...prev, { role: "user", content: userMsg }]);
    setIsLoading(true);

    const effectiveLang = selectedLanguage || "en";
    if (typeof window !== "undefined") {
      window.localStorage.setItem("keysight.language", effectiveLang);
    }

    const effectiveSource = routingMode === "auto" ? "auto" : selectedSource;

    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: userMsg,
          history: historyForApi,
          session_id: sessionIdRef.current,
          model_profile: selectedModel,
          data_source: effectiveSource,
          language: effectiveLang,
        }),
      });
      const data = await res.json();
      const reply = data.reply ?? data.output ?? "Sorry, no response.";
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: reply,
          thinkingSteps: data.thinking_steps ?? [],
          tool_calls: data.tool_calls ?? [],
          citations: data.citations ?? [],
          latencyMs: data.latency_ms ?? null,
          inputTokens: data.input_tokens ?? null,
          outputTokens: data.output_tokens ?? null,
          model: data.model ?? null,
        },
      ]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: "Sorry, there was an error connecting to the backend." },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  // ── Closed state — just show floating button ─────────────────────────────
  if (!open) {
    return (
      <Button
        onClick={() => setOpen(true)}
        className="fixed bottom-6 right-6 h-14 w-14 rounded-full shadow-lg"
        size="icon"
      >
        <MessageSquare className="h-6 w-6" />
      </Button>
    );
  }

  const modelLabel = MODEL_OPTIONS.find((m) => m.id === selectedModel)?.label ?? "Model";
  const sourceLabel =
    selectedSource === "auto"
      ? "Auto"
      : DATA_SOURCE_OPTIONS.find((s) => s.id === selectedSource)?.label ?? selectedSource;
  const languageLabel =
    LANGUAGE_OPTIONS.find((l) => l.id === selectedLanguage)?.label ?? "English";

  // ── Open state ─────────────────────────────────────────────────────────────
  return (
    <div className="fixed bottom-6 right-6 flex h-[600px] w-[420px] flex-col overflow-hidden rounded-2xl border bg-background shadow-2xl z-50">
      {/* ── Header ────────────────────────────────────────────────────────── */}
      <div className="border-b bg-muted/30">
        {/* Top row: title, Live badge, language selector, close */}
        <div className="flex items-center justify-between gap-2 p-3">
          <div className="flex items-center gap-2 min-w-0">
            <Bot className="h-5 w-5 shrink-0 text-primary" />
            <span className="font-semibold truncate">Keysight AI</span>
            <Badge
              variant="outline"
              className="gap-1 shrink-0 border-green-500/40 bg-green-500/10 text-green-600 text-[10px]"
            >
              <span className="h-1.5 w-1.5 rounded-full bg-green-500 animate-pulse" /> Live
            </Badge>
          </div>
          <div className="flex items-center gap-1.5 shrink-0">
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  className="h-7 px-2.5 text-[11px] gap-1"
                >
                  <Globe className="h-3.5 w-3.5 shrink-0" />
                  <span className="truncate max-w-[72px]">{languageLabel}</span>
                  <ChevronDown className="h-3 w-3 shrink-0" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="min-w-[160px]">
                <DropdownMenuLabel className="text-[11px]">Response language</DropdownMenuLabel>
                <DropdownMenuSeparator />
                {LANGUAGE_OPTIONS.map((l) => (
                  <DropdownMenuItem
                    key={l.id}
                    className="text-[11px]"
                    onClick={() => {
                      setSelectedLanguage(l.id);
                      if (typeof window !== "undefined")
                        window.localStorage.setItem("keysight.language", l.id);
                    }}
                  >
                    {l.label}
                  </DropdownMenuItem>
                ))}
              </DropdownMenuContent>
            </DropdownMenu>
            <Button
              variant="ghost"
              size="icon"
              className="h-8 w-8 rounded-full shrink-0"
              onClick={() => setOpen(false)}
            >
              <X className="h-4 w-4" />
            </Button>
          </div>
        </div>
        {/* Second row: Model, Data Source / Auto toggle */}
        <div className="flex flex-wrap items-center gap-1.5 px-3 pb-2">
          {/* Model dropdown */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                type="button"
                variant="outline"
                size="sm"
                className="h-6 max-w-[140px] px-2 text-[10px] gap-1 truncate"
              >
                <Cpu className="h-3 w-3 shrink-0" />
                <span className="truncate">{modelLabel}</span>
                <ChevronDown className="h-3 w-3 shrink-0" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="start" className="min-w-[180px] max-h-[240px] overflow-y-auto">
              <DropdownMenuLabel className="text-[11px]">Model</DropdownMenuLabel>
              <DropdownMenuSeparator />
              <DropdownMenuGroup>
                {MODEL_OPTIONS.map((m) => (
                  <DropdownMenuItem
                    key={m.id}
                    className="text-[11px]"
                    onClick={() => setSelectedModel(m.id)}
                  >
                    {m.label}
                  </DropdownMenuItem>
                ))}
              </DropdownMenuGroup>
            </DropdownMenuContent>
          </DropdownMenu>

          {/* Auto/Manual toggle */}
          <div className="flex items-center rounded-full border border-border overflow-hidden h-6">
            <button
              type="button"
              onClick={() => {
                setRoutingMode("auto");
                setSelectedSource("auto");
              }}
              className={`px-2.5 py-0.5 text-[10px] font-medium transition-colors ${routingMode === "auto"
                ? "bg-primary text-primary-foreground"
                : "bg-transparent text-muted-foreground hover:text-foreground"
                }`}
            >
              Auto
            </button>
            <button
              type="button"
              onClick={() => setRoutingMode("manual")}
              className={`px-2.5 py-0.5 text-[10px] font-medium transition-colors ${routingMode === "manual"
                ? "bg-primary text-primary-foreground"
                : "bg-transparent text-muted-foreground hover:text-foreground"
                }`}
            >
              Manual
            </button>
          </div>

          {/* Data source dropdown (only when manual) */}
          {routingMode === "manual" && (
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  className="h-6 max-w-[100px] px-2 text-[10px] gap-1 truncate"
                >
                  <Database className="h-3 w-3 shrink-0" />
                  <span className="truncate">{sourceLabel}</span>
                  <ChevronDown className="h-3 w-3 shrink-0" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="start" className="min-w-[200px] max-h-[240px] overflow-y-auto">
                <DropdownMenuLabel className="text-[11px]">Data source</DropdownMenuLabel>
                <DropdownMenuSeparator />
                {DATA_SOURCE_OPTIONS.filter((s) => s.id !== "auto").map((s) => (
                  <DropdownMenuItem
                    key={s.id}
                    className="text-[11px]"
                    onClick={() => setSelectedSource(s.id)}
                  >
                    {s.label}
                  </DropdownMenuItem>
                ))}
              </DropdownMenuContent>
            </DropdownMenu>
          )}
        </div>
      </div>

      {/* ── Messages area ─────────────────────────────────────────────────── */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((m, i) => (
          <div key={i} className={"flex gap-2 " + (m.role === "user" ? "flex-row-reverse" : "")}>
            {/* Avatar */}
            <div
              className={
                "flex h-7 w-7 items-center justify-center rounded-full shrink-0 " +
                (m.role === "user" ? "bg-muted" : "bg-primary")
              }
            >
              {m.role === "user" ? (
                <User className="h-3.5 w-3.5 text-muted-foreground" />
              ) : (
                <Bot className="h-3.5 w-3.5 text-primary-foreground" />
              )}
            </div>

            {/* Message content column */}
            <div
              className={`flex flex-col gap-1.5 max-w-[85%] ${m.role === "user" ? "items-end" : "items-start"
                }`}
            >
              {/* Text bubble */}
              <div
                className={
                  "rounded-2xl px-3.5 py-2.5 text-sm leading-relaxed " +
                  (m.role === "user"
                    ? "bg-primary text-primary-foreground rounded-tr-sm"
                    : "bg-muted rounded-tl-sm")
                }
              >
                <div className="flex items-start gap-1.5">
                  <div className="flex-1 min-w-0">
                    {m.role === "assistant" ? (
                      <MarkdownMessage content={m.content} />
                    ) : (
                      m.content
                    )}
                  </div>
                  {m.role === "assistant" && m.content && i > 0 && (
                    <button
                      type="button"
                      onClick={() => {
                        navigator?.clipboard?.writeText(m.content).catch(() => undefined);
                      }}
                      className="ml-1 inline-flex items-center justify-center rounded-md bg-background/40 hover:bg-background/80 border border-border/50 text-[9px] px-1 py-0.5 text-muted-foreground shrink-0"
                      aria-label="Copy response"
                    >
                      <Copy className="h-2.5 w-2.5" />
                    </button>
                  )}
                </div>
              </div>

              {/* Reasoning steps */}
              {m.role === "assistant" && m.thinkingSteps && m.thinkingSteps.length > 0 && (
                <div className="w-full rounded-lg border border-border/60 bg-muted/30 px-3 py-2 text-left">
                  <div className="flex items-center gap-1.5 mb-1.5 text-[10px] font-medium text-muted-foreground">
                    <Brain className="h-3 w-3" />
                    Reasoning steps
                  </div>
                  <ul className="space-y-0.5 text-[11px] text-muted-foreground font-mono">
                    {m.thinkingSteps.map((line, j) => (
                      <li
                        key={j}
                        className={
                          line.startsWith("Calling tool")
                            ? "text-primary font-medium"
                            : ""
                        }
                      >
                        {line}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Tool call badges */}
              {m.tool_calls && m.tool_calls.length > 0 && (
                <div className="flex flex-wrap gap-1">
                  {Array.from(
                    new Map(m.tool_calls.map((tc) => [tc.tool, tc])).values()
                  ).map((tc) => (
                    <Badge
                      key={tc.tool}
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
              {m.citations && m.citations.length > 0 && (
                <div className="flex flex-wrap gap-1">
                  {m.citations.map((c, j) => (
                    <Badge
                      key={j}
                      variant="outline"
                      className="gap-1 text-[9px] h-4 border-muted-foreground/30 text-muted-foreground"
                    >
                      📎 {c}
                    </Badge>
                  ))}
                </div>
              )}

              {/* Footer metrics: latency, tokens, model, summary */}
              {m.role === "assistant" && i > 0 && (m.latencyMs != null || m.model) && (
                <div className="flex flex-wrap items-center gap-x-2.5 gap-y-0.5 text-[10px] text-muted-foreground">
                  {m.latencyMs != null && (
                    <span className="flex items-center gap-0.5">
                      <Clock className="h-2.5 w-2.5" />
                      {m.latencyMs >= 1000
                        ? `${(m.latencyMs / 1000).toFixed(0)} seconds`
                        : `${m.latencyMs}ms`}
                    </span>
                  )}
                  {(m.inputTokens != null || m.outputTokens != null) && (
                    <span>
                      {m.inputTokens != null && m.outputTokens != null
                        ? `${(m.inputTokens ?? 0).toLocaleString()} tokens in / ${(m.outputTokens ?? 0).toLocaleString()} tokens out`
                        : m.inputTokens != null
                          ? `${(m.inputTokens ?? 0).toLocaleString()} tokens in`
                          : `${(m.outputTokens ?? 0).toLocaleString()} tokens out`}
                    </span>
                  )}
                  {m.model && (
                    <span className="flex items-center gap-0.5">
                      <Sparkles className="h-2.5 w-2.5" />
                      {m.model}
                    </span>
                  )}
                  <button
                    type="button"
                    onClick={() => {
                      const summaryPrompt =
                        "Give a short executive summary of your previous answer, focusing on the most important points.";
                      setInput(summaryPrompt);
                    }}
                    className="inline-flex items-center gap-0.5 rounded-full border border-border/60 bg-background/60 px-1.5 py-0.5 text-[9px] hover:bg-background text-muted-foreground"
                  >
                    <Sparkles className="h-2 w-2" />
                    Summary
                  </button>
                  {/* Thumbs feedback */}
                  <button
                    type="button"
                    onClick={() => sendFeedback(i, "thumbs_up", messages[i - 1]?.content)}
                    className={`inline-flex items-center justify-center rounded-full border px-1.5 py-0.5 text-[9px] transition-colors ${thumbsState[i] === "up"
                        ? "border-green-500 bg-green-500/10 text-green-500"
                        : "border-border/60 bg-background/60 text-muted-foreground hover:text-green-500"
                      }`}
                    title="Helpful"
                  >
                    <ThumbsUp className="h-2.5 w-2.5" />
                  </button>
                  <button
                    type="button"
                    onClick={() => sendFeedback(i, "thumbs_down", messages[i - 1]?.content)}
                    className={`inline-flex items-center justify-center rounded-full border px-1.5 py-0.5 text-[9px] transition-colors ${thumbsState[i] === "down"
                        ? "border-red-500 bg-red-500/10 text-red-500"
                        : "border-border/60 bg-background/60 text-muted-foreground hover:text-red-500"
                      }`}
                    title="Not helpful"
                  >
                    <ThumbsDown className="h-2.5 w-2.5" />
                  </button>
                </div>
              )}
            </div>
          </div>
        ))}

        {/* Loading / thinking animation */}
        {isLoading && (
          <div className="flex gap-2.5">
            <div className="flex h-7 w-7 items-center justify-center rounded-full bg-primary shrink-0">
              <Bot className="h-3.5 w-3.5 text-primary-foreground" />
            </div>
            <div className="flex flex-col gap-1.5 rounded-2xl rounded-tl-sm bg-muted px-4 py-3 min-w-[160px]">
              <ThinkingSteps />
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* ── Input area ────────────────────────────────────────────────────── */}
      <div className="border-t p-3 bg-background">
        <form onSubmit={handleSubmit} className="flex gap-2">
          <Input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask Keysight AI..."
            disabled={isLoading}
            className="flex-1"
          />
          <Button type="submit" size="icon" disabled={isLoading || !input.trim()}>
            <Send className="h-4 w-4" />
          </Button>
        </form>
      </div>
    </div>
  );
}
