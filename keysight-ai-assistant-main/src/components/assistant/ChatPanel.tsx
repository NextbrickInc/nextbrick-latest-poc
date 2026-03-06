// ─── components/assistant/ChatPanel.tsx ──────────────────────────────────────
// Full-featured agentic chat panel — styled after the provided reference UI.
// Reads/writes from Redux chatSlice. Shows tool-call badges, citations,
// latency, and a suggested-prompts carousel when the chat is empty.
import { useRef, useEffect, useState } from "react";
import {
  Bot, Send, Sparkles, User, Wrench, AlertCircle,
  ChevronRight, Clock, Zap, Brain, Copy, ChevronDown,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { MarkdownMessage } from "@/components/assistant/MarkdownMessage";
import { useAppDispatch, useAppSelector } from "@/store/hooks";
import {
  sendMessage,
  mergePendingResponse,
  selectActiveMessages,
  selectChatStatus,
  selectChatError,
  selectPendingFulfill,
  clearError,
  selectActiveSessionId,
} from "@/store/slices/chatSlice";
import { setModelName } from "@/store/slices/modelSlice";

type ModelOption = {
  id: string;
  label: string;
  group: "onprem" | "cloud";
};

const MODEL_OPTIONS: ModelOption[] = [
  // On‑prem / Ollama first
  { id: "qwen3-coder:480b-cloud", label: "Qwen3 Coder 480B (on‑prem)", group: "onprem" },
  { id: "mistral-nemo:12b", label: "Mistral Nemo 12B", group: "onprem" },
  { id: "qwen2.5:14b-instruct-q4_k_m", label: "Qwen2.5 14B Instruct (Q4_K_M)", group: "onprem" },
  { id: "bge-m3:latest", label: "BGE-M3 Embeddings", group: "onprem" },
  { id: "mixtral:8x7b-instruct-v0.1-q4_K_M", label: "Mixtral 8×7B Instruct (Q4_K_M)", group: "onprem" },
  { id: "qwen2.5:32b-instruct-q4_k_m", label: "Qwen2.5 32B Instruct (Q4_K_M)", group: "onprem" },
  { id: "gpt-oss:20b-cloud", label: "GPT‑OSS 20B (on‑prem)", group: "onprem" },
  { id: "gpt-oss:120b-cloud", label: "GPT‑OSS 120B (on‑prem)", group: "onprem" },
  { id: "ministral-3:8b-instruct-2512-q4_K_M", label: "Ministral‑3 8B Instruct (Q4_K_M)", group: "onprem" },

  // Cloud / hosted models
  { id: "gpt-5.2", label: "ChatGPT 5.2 (latest)", group: "cloud" },
  { id: "gemini-3", label: "Gemini 3 (latest)", group: "cloud" },
  { id: "claude-3.6-sonnet", label: "Claude Sonnet 4.6", group: "cloud" },
  { id: "claude-3.6-opus", label: "Claude Opus 4.6", group: "cloud" },
  { id: "grok-4", label: "Grok 4", group: "cloud" },
];

// ── Language options ──────────────────────────────────────────────────────────
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
  const pendingFulfill = useAppSelector(selectPendingFulfill);
  const modelName = useAppSelector((s) => s.model.name);
  const activeId = useAppSelector(selectActiveSessionId);

  const [inputValue, setInputValue] = useState("");
  const [selectedModelProfile, setSelectedModelProfile] = useState<string>(
    MODEL_OPTIONS[0]?.id ?? "gpt-oss:120b-cloud",
  );
  const [selectedSource, setSelectedSource] = useState<string>("auto");
  const [selectedLanguage, setSelectedLanguage] = useState<string>(() => {
    if (typeof window !== "undefined") {
      return window.localStorage.getItem("keysight.language") || "en";
    }
    return "en";
  });
  const messagesContainerRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const isLoading = chatStatus === "sending";

  // Apply delayed response after minimum 5s thinking
  useEffect(() => {
    if (!pendingFulfill) return;
    const delay = Math.max(0, pendingFulfill.mergeAt - Date.now());
    const t = setTimeout(() => dispatch(mergePendingResponse()), delay);
    return () => clearTimeout(t);
  }, [pendingFulfill, dispatch]);

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

  // Keep language in sync with Navbar (localStorage is source of truth)
  useEffect(() => {
    if (typeof window === "undefined") return;
    const stored = window.localStorage.getItem("keysight.language");
    if (stored && stored !== selectedLanguage) setSelectedLanguage(stored);
  }, []);
  const handleStorageSync = () => {
    if (typeof window === "undefined") return;
    const stored = window.localStorage.getItem("keysight.language");
    if (stored && stored !== selectedLanguage) setSelectedLanguage(stored);
  };
  useEffect(() => {
    window.addEventListener("storage", handleStorageSync);
    window.addEventListener("focus", handleStorageSync);
    return () => {
      window.removeEventListener("storage", handleStorageSync);
      window.removeEventListener("focus", handleStorageSync);
    };
  }, [selectedLanguage]);

  const handleSend = () => {
    const text = inputValue.trim();
    if (!text || isLoading) return;
    setInputValue("");
    const effectiveLang =
      (typeof window !== "undefined" ? window.localStorage.getItem("keysight.language") : null) ||
      selectedLanguage ||
      "en";
    if (typeof window !== "undefined") {
      window.localStorage.setItem("keysight.language", effectiveLang);
    }
    setSelectedLanguage(effectiveLang);
    dispatch(
      sendMessage({
        sessionId: activeId,
        message: text,
        modelProfile: selectedModelProfile,
        dataSource: selectedSource,
        language: effectiveLang,
      }),
    );
  };

  const handleKey = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  // Show only the last ~20 messages to keep scroll snappy
  const visibleMessages = messages.slice(-20);
  const lastUserMessage = [...visibleMessages].reverse().find((m) => m.role === "user");
  const isEmpty = visibleMessages.length <= 1; // only greeting
  const pendingThinkingSteps: string[] =
    (pendingFulfill?.payload.response.thinking_steps as string[] | undefined) || [];
  const currentPendingStep =
    pendingThinkingSteps.length > 0 ? pendingThinkingSteps[pendingThinkingSteps.length - 1] : null;

  const currentModel = MODEL_OPTIONS.find((m) => m.id === selectedModelProfile) ?? MODEL_OPTIONS[0];
  const selectedLanguageLabel =
    LANGUAGE_OPTIONS.find((l) => l.id === selectedLanguage)?.label ?? "English";
  const latestAssistantMessage = [...messages]
    .reverse()
    .find(
      (m) =>
        m.role === "assistant" &&
        !m.error &&
        !!m.text &&
        !m.text.startsWith("Hi! I'm your Keysight AI Assistant."),
    );

  const handleLanguageChange = (languageId: string) => {
    if (languageId === selectedLanguage) return;
    setSelectedLanguage(languageId);
    if (typeof window !== "undefined") {
      window.localStorage.setItem("keysight.language", languageId);
    }
    if (isLoading || !latestAssistantMessage) return;
    const languageLabel =
      LANGUAGE_OPTIONS.find((l) => l.id === languageId)?.label ?? "English";
    dispatch(
      sendMessage({
        sessionId: activeId,
        message: `Translate your previous answer into ${languageLabel}. Keep all technical details unchanged, preserve markdown structure and links, and apply multilingual citation rules exactly.`,
        modelProfile: selectedModelProfile,
        dataSource: selectedSource,
        language: languageId,
      }),
    );
  };

  return (
    <div className="flex flex-col rounded-2xl border border-border bg-card overflow-hidden shadow-lg min-w-0">
      {/* ── Panel header */}
      <div className="flex items-center justify-between border-b border-border px-4 py-2.5 bg-gradient-to-r from-primary/5 to-transparent">
        <div className="flex items-center gap-2.5">
          <img src="/image.png" alt="Keysight AI" className="h-10 w-10 object-contain drop-shadow-sm" />
          <div>
            <p className="text-sm font-bold text-foreground leading-none">Keysight AI Assistant</p>
            <div className="mt-0.5 flex flex-col gap-0.5">
              <p className="text-[10px] text-muted-foreground flex items-center gap-1">
                <Brain className="h-2.5 w-2.5 text-primary" />
                {modelName || "Model not configured"} · Plan → Retrieve → Act
              </p>
              <div className="flex flex-wrap items-center gap-2">
                <div className="flex items-center gap-1">
                  <span className="text-[10px] text-muted-foreground">Model:</span>
                  <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        className="h-6 px-2 py-0 text-[10px] gap-1"
                      >
                        {currentModel?.label ?? "Select model"}
                        <ChevronDown className="h-3 w-3" />
                      </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent className="min-w-[220px]">
                      <DropdownMenuLabel className="text-[11px]">On‑prem / Ollama</DropdownMenuLabel>
                      <DropdownMenuGroup>
                        {MODEL_OPTIONS.filter((m) => m.group === "onprem").map((m) => (
                          <DropdownMenuItem
                            key={m.id}
                            className="text-[11px]"
                            onClick={() => {
                              setSelectedModelProfile(m.id);
                              dispatch(setModelName(m.label));
                            }}
                          >
                            {m.label}
                          </DropdownMenuItem>
                        ))}
                      </DropdownMenuGroup>
                      <DropdownMenuSeparator />
                      <DropdownMenuLabel className="text-[11px]">Cloud</DropdownMenuLabel>
                      <DropdownMenuGroup>
                        {MODEL_OPTIONS.filter((m) => m.group === "cloud").map((m) => (
                          <DropdownMenuItem
                            key={m.id}
                            className="text-[11px]"
                            onClick={() => {
                              setSelectedModelProfile(m.id);
                              dispatch(setModelName(m.label));
                            }}
                          >
                            {m.label}
                          </DropdownMenuItem>
                        ))}
                      </DropdownMenuGroup>
                    </DropdownMenuContent>
                  </DropdownMenu>
                </div>
                <div className="flex items-center gap-1">
                  <span className="text-[10px] text-muted-foreground">Data source:</span>
                  <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        className="h-6 px-2 py-0 text-[10px] gap-1"
                      >
                        {selectedSource === "auto"
                          ? "Auto"
                          : selectedSource}
                        <ChevronDown className="h-3 w-3" />
                      </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent className="min-w-[260px]">
                      <DropdownMenuLabel className="text-[11px]">Routing</DropdownMenuLabel>
                      <DropdownMenuItem
                        className="text-[11px]"
                        onClick={() => setSelectedSource("auto")}
                      >
                        Auto (let assistant choose)
                      </DropdownMenuItem>
                      <DropdownMenuSeparator />
                      <DropdownMenuLabel className="text-[11px]">Data sources</DropdownMenuLabel>
                      {[
                        { id: "coveo", label: "Coveo" },
                        { id: "aem_dam", label: "AEM DAM" },
                        { id: "aem_pages", label: "AEM Pages" },
                        { id: "confluence", label: "Confluence" },
                        {
                          id: "salesforce",
                          label: "Salesforce (Cases, Emails, KB, Service Notes, Service Orders)",
                        },
                        { id: "pim", label: "PIM" },
                        { id: "skilljar_lms", label: "Skilljar LMS" },
                        { id: "oracle", label: "Oracle (Parts and Sales data)" },
                        { id: "snowflake", label: "Snowflake (Enterprise Data Warehouse)" },
                      ].map((src) => (
                        <DropdownMenuItem
                          key={src.id}
                          className="text-[11px]"
                          onClick={() => setSelectedSource(src.id)}
                        >
                          {src.label}
                        </DropdownMenuItem>
                      ))}
                    </DropdownMenuContent>
                  </DropdownMenu>
                </div>
              </div>
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {isLoading && (
            <Badge
              variant="outline"
              className="gap-1 border-red-500/40 bg-red-500/10 text-red-400 text-[10px] animate-pulse"
            >
              <Zap className="h-2.5 w-2.5 text-red-400" />
              {currentPendingStep
                ? `${currentPendingStep.slice(0, 48)}${
                    currentPendingStep.length > 48 ? "…" : ""
                  }`
                : "Reasoning…"}
            </Badge>
          )}
          <Badge variant="outline" className="gap-1 text-[10px] border-green-500/40 bg-green-500/10 text-green-400">
            <span className="h-1.5 w-1.5 rounded-full bg-green-500 animate-pulse" />
            Live
          </Badge>
        </div>
      </div>

      {/* ── Messages area */}
      <div ref={messagesContainerRef} className="flex-1 overflow-y-auto overflow-x-hidden px-4 py-4 space-y-4 min-h-[340px] max-h-[500px]">

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
              <div className={`flex min-w-0 max-w-[95%] flex-col gap-1.5 ${msg.role === "user" ? "items-end" : "items-start"}`}>
                <div
                  className={`min-w-0 overflow-hidden rounded-2xl px-3.5 py-2.5 leading-relaxed ${isIntro ? "text-base" : "text-sm"}
                  ${msg.role === "user"
                      ? "bg-primary text-primary-foreground rounded-tr-sm"
                      : msg.error
                        ? "bg-destructive/10 text-destructive border border-destructive/20 rounded-tl-sm"
                        : "bg-secondary text-foreground rounded-tl-sm"
                    }`}
                >
                  <div className="flex items-start gap-2">
                    <div className="flex-1 min-w-0">
                      {msg.role === "assistant" ? (
                        <MarkdownMessage content={msg.text} />
                      ) : (
                        msg.text
                      )}
                    </div>
                    <button
                      type="button"
                      onClick={() => {
                        if (navigator?.clipboard && msg.text) {
                          navigator.clipboard.writeText(msg.text).catch(() => undefined);
                        }
                      }}
                      className="ml-1 inline-flex items-center justify-center rounded-md bg-background/40 hover:bg-background/80 border border-border/50 text-[10px] px-1.5 py-0.5 text-muted-foreground shrink-0"
                      aria-label={msg.role === "user" ? "Copy prompt" : "Copy response"}
                    >
                      <Copy className="h-3 w-3 mr-1" />
                      Copy
                    </button>
                  </div>
                </div>

                {/* Thinking / reasoning steps */}
                {msg.role === "assistant" && msg.thinkingSteps && msg.thinkingSteps.length > 0 && (
                  <div className="rounded-lg border border-border/60 bg-muted/30 px-3 py-2 text-left">
                    <div className="flex items-center gap-1.5 mb-1.5 text-[10px] font-medium text-muted-foreground">
                      <Brain className="h-3 w-3" />
                      Reasoning steps
                    </div>
                    <ul className="space-y-0.5 text-[11px] text-muted-foreground font-mono">
                      {msg.thinkingSteps.map((line, i) => (
                        <li key={i} className={line.startsWith("Calling tool") ? "text-primary/90 font-medium" : ""}>
                          {line}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* Tool calls — one badge per unique tool */}
                {msg.tool_calls && msg.tool_calls.length > 0 && (
                  <div className="flex flex-wrap gap-1">
                    {Array.from(new Map(msg.tool_calls.map((tc) => [tc.tool, tc])).values()).map((tc, i) => (
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

                {/* Meta row — latency, tokens in/out, model, actions */}
                <div className="flex flex-wrap items-center gap-x-3 gap-y-0.5 text-[10px] text-muted-foreground">
                  {msg.latencyMs != null && (
                    <span className="flex items-center gap-0.5">
                      <Clock className="h-2.5 w-2.5" />
                      {msg.latencyMs >= 1000
                        ? `${(msg.latencyMs / 1000).toFixed(0)} seconds`
                        : `${msg.latencyMs}ms`}
                    </span>
                  )}
                  {(msg.inputTokens != null || msg.outputTokens != null) && (
                    <span className="flex items-center gap-0.5">
                      {msg.inputTokens != null && msg.outputTokens != null
                        ? `${(msg.inputTokens ?? 0).toLocaleString()} tokens in / ${(msg.outputTokens ?? 0).toLocaleString()} tokens out`
                        : msg.inputTokens != null
                          ? `${(msg.inputTokens ?? 0).toLocaleString()} tokens in`
                          : `${(msg.outputTokens ?? 0).toLocaleString()} tokens out`}
                    </span>
                  )}
                  {msg.model && (
                    <span className="flex items-center gap-0.5">
                      <Sparkles className="h-2.5 w-2.5" />
                      {msg.model}
                    </span>
                  )}
                  {msg.role === "assistant" && (
                    <button
                      type="button"
                      onClick={() => {
                        const kind =
                          msg.text?.toLowerCase().includes("case number") ||
                          msg.text?.toLowerCase().includes("status:")
                            ? "case"
                            : msg.text?.toLowerCase().includes("datasheet") ||
                              msg.text?.toLowerCase().includes("specifications")
                              ? "datasheet"
                              : "general";
                        const summaryPrompt =
                          kind === "datasheet"
                            ? "Summarize your previous answer as a concise product datasheet summary with key specs, options, and usage notes."
                            : kind === "case"
                              ? "Summarize your previous answer as a support case summary, highlighting customer, issue, actions taken, and current status."
                              : "Give a short executive summary of your previous answer, focusing on the most important points.";
                        dispatch(
                          sendMessage({
                            sessionId: activeId,
                            message: summaryPrompt,
                            modelProfile: selectedModelProfile,
                            dataSource: selectedSource,
                            language: selectedLanguage,
                          }),
                        );
                      }}
                      className="ml-1 inline-flex items-center gap-1 rounded-full border border-border/60 bg-background/60 px-2 py-0.5 text-[10px] hover:bg-background text-muted-foreground"
                    >
                      <Sparkles className="h-2.5 w-2.5" />
                      Summary
                    </button>
                  )}
                </div>
              </div>
            </div>
          );
        })}

        {/* In-progress reasoning placeholder while waiting for response */}
        {isLoading && (
          <div className="flex gap-3 flex-row mt-1">
            <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-primary shadow-md shadow-primary/20 text-primary-foreground">
              <Bot className="h-3.5 w-3.5" />
            </div>
            <div className="flex min-w-0 max-w-[95%] flex-col gap-1.5 items-start">
              <div className="min-w-0 rounded-2xl rounded-tl-sm px-3.5 py-2.5 bg-secondary text-foreground text-sm">
                <div className="flex items-center gap-1.5 mb-1 text-[10px] font-medium text-muted-foreground">
                  <Brain className="h-3 w-3" />
                  Reasoning (in progress)
                </div>
                {currentPendingStep ? (
                  <ul className="space-y-0.5 text-[11px] text-muted-foreground font-mono">
                    {lastUserMessage && (
                      <li className="text-foreground/80">
                        {`User query: "${lastUserMessage.text.slice(0, 80)}${
                          lastUserMessage.text.length > 80 ? "…" : ""
                        }"`}
                      </li>
                    )}
                    <li className="text-primary/90 font-semibold">
                      {currentPendingStep}
                    </li>
                  </ul>
                ) : (
                  <ul className="space-y-0.5 text-[11px] text-muted-foreground font-mono">
                    {lastUserMessage && (
                      <li>{`User query: "${lastUserMessage.text.slice(0, 80)}${
                        lastUserMessage.text.length > 80 ? "…" : ""
                      }"`}</li>
                    )}
                    <li>Identifying the most relevant data source</li>
                    <li>Selecting appropriate tools (Salesforce / Elasticsearch / others)</li>
                    <li>Preparing search/query against internal systems</li>
                    <li>Waiting for tool responses…</li>
                  </ul>
                )}
              </div>
            </div>
          </div>
        )}

      </div>

      {/* ── Input area ────────────────────────────────────────────────────── */}
      <div className="border-t border-border p-3 bg-card">
        <div className="mb-2.5 flex items-center justify-between rounded-md border border-border/70 bg-muted/30 px-2.5 py-1.5">
          <span className="text-[10px] text-muted-foreground">Response language</span>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                type="button"
                variant="outline"
                size="sm"
                className="h-6 px-2 py-0 text-[10px] gap-1"
              >
                {selectedLanguageLabel}
                <ChevronDown className="h-3 w-3" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent className="min-w-[220px]">
              <DropdownMenuLabel className="text-[11px]">Language</DropdownMenuLabel>
              {LANGUAGE_OPTIONS.map((lang) => (
                <DropdownMenuItem
                  key={lang.id}
                  className="text-[11px]"
                  onClick={() => handleLanguageChange(lang.id)}
                >
                  {lang.label}
                </DropdownMenuItem>
              ))}
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
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
          Keysight AI may make mistakes. Validate critical information.
        </p>
      </div>
    </div>
  );
}
