// ─── components/assistant/FloatingChat.tsx ────────────────────────────────────
// Self-contained floating chat widget. Clicking the robot avatar toggles a
// chat drawer. Shares the same Redux chatSlice / sendMessage thunk as ChatPanel.
import { useRef, useEffect, useState } from "react";
import {
    Send, Sparkles, User, Bot, X, Minimize2, AlertCircle,
    Wrench, Clock, ChevronRight, Zap, Brain
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

// Colour map for tool badges
const TOOL_COLOURS: Record<string, string> = {
    salesforce: "border-blue-500/40 bg-blue-500/10 text-blue-400",
    pricing: "border-yellow-500/40 bg-yellow-500/10 text-yellow-400",
    calibration: "border-green-500/40 bg-green-500/10 text-green-400",
    elasticsearch: "border-purple-500/40 bg-purple-500/10 text-purple-400",
    aem: "border-orange-500/40 bg-orange-500/10 text-orange-400",
    confluence: "border-teal-500/40 bg-teal-500/10 text-teal-400",
};

function toolColour(tool: string) {
    const key = Object.keys(TOOL_COLOURS).find((k) =>
        tool.toLowerCase().includes(k)
    );
    return key
        ? TOOL_COLOURS[key]
        : "border-border bg-secondary text-muted-foreground";
}

const QUICK_PROMPTS = [
    { text: "Where is my order?", icon: "📦" },
    { text: "Create a support case", icon: "🎫" },
    { text: "What is the price of DSOX1202A in US?", icon: "💰" },
    { text: "Find instructions manual of U1610A", icon: "📄" },
];

export default function FloatingChat() {
    const dispatch = useAppDispatch();
    const messages = useAppSelector(selectActiveMessages);
    const chatStatus = useAppSelector(selectChatStatus);
    const chatError = useAppSelector(selectChatError);
    const modelName = useAppSelector((s) => s.model.name);
    const activeId = useAppSelector(selectActiveSessionId);

    const [open, setOpen] = useState(false);
    const [inputValue, setInputValue] = useState("");
    const messagesEndRef = useRef<HTMLDivElement>(null);
    const inputRef = useRef<HTMLTextAreaElement>(null);
    const isLoading = chatStatus === "sending";

    // Auto-scroll to bottom on new messages
    useEffect(() => {
        if (open) {
            messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
        }
    }, [messages, open]);

    // Clear error after 5s
    useEffect(() => {
        if (chatError) {
            const t = setTimeout(() => dispatch(clearError()), 5000);
            return () => clearTimeout(t);
        }
    }, [chatError, dispatch]);

    // Focus input when opened
    useEffect(() => {
        if (open) {
            setTimeout(() => inputRef.current?.focus(), 100);
        }
    }, [open]);

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

    const visibleMessages = messages.slice(-30);
    const isEmpty = visibleMessages.length <= 1;

    return (
        <>
            {/* ── Floating robot button ──────────────────────────────────────────── */}
            <div className="fixed bottom-20 right-28 z-50 flex flex-col items-end gap-2">

                {/* Tooltip — visible on hover, hidden when chat open */}
                {!open && (
                    <span className="mb-1 rounded-full bg-foreground/90 px-3 py-1 text-[11px] font-semibold text-background shadow-lg whitespace-nowrap opacity-0 hover:opacity-100 transition-opacity pointer-events-none">
                        Chat with AI Agent
                    </span>
                )}

                {/* Robot button */}
                <button
                    onClick={() => setOpen((v) => !v)}
                    aria-label={open ? "Close chat" : "Open AI chat"}
                    className="relative flex items-center justify-center focus:outline-none group"
                >
                    {/* Pulsing ring — only when closed */}
                    {!open && (
                        <span className="absolute inline-flex h-16 w-16 rounded-full bg-primary opacity-20 animate-ping" />
                    )}

                    <div
                        className={`relative flex h-14 w-14 items-center justify-center rounded-full bg-white shadow-xl border-2 transition-all duration-200
              ${open
                                ? "border-primary scale-105 shadow-primary/40"
                                : "border-primary/20 hover:scale-110 hover:shadow-primary/30"
                            }`}
                    >
                        {/* Show X when open, robot when closed */}
                        {open ? (
                            <X className="h-6 w-6 text-primary" />
                        ) : (
                            <img src="/image.png" alt="AI Agent" className="h-12 w-12 object-contain" />
                        )}
                    </div>
                </button>
            </div>

            {/* ── Chat drawer ────────────────────────────────────────────────────── */}
            <div
                className={`fixed bottom-36 right-28 z-40 flex flex-col
          w-[360px] rounded-2xl border border-border bg-card shadow-2xl shadow-primary/10
          transition-all duration-300 origin-bottom-right overflow-hidden
          ${open
                        ? "opacity-100 scale-100 pointer-events-auto"
                        : "opacity-0 scale-95 pointer-events-none"
                    }`}
                style={{ maxHeight: "560px", minHeight: "460px" }}
            >
                {/* Header */}
                <div className="flex items-center justify-between border-b border-border px-4 py-3 bg-gradient-to-r from-primary/5 to-transparent shrink-0">
                    <div className="flex items-center gap-2.5">
                        <img
                            src="/image.png"
                            alt="Nextbrick AI"
                            className="h-9 w-9 object-contain drop-shadow-sm"
                        />
                        <div>
                            <p className="text-sm font-bold text-foreground leading-none">
                                Nextbrick AI Agent
                            </p>
                            <p className="mt-0.5 text-[10px] text-muted-foreground flex items-center gap-1">
                                <Brain className="h-2.5 w-2.5 text-primary" />
                                {modelName || "Model not configured"} · Plan → Retrieve → Act
                            </p>
                        </div>
                    </div>
                    <div className="flex items-center gap-2">
                        {isLoading && (
                            <Badge
                                variant="outline"
                                className="gap-1 border-yellow-500/40 bg-yellow-500/10 text-yellow-400 text-[10px] animate-pulse"
                            >
                                <Zap className="h-2.5 w-2.5" />
                                Thinking…
                            </Badge>
                        )}
                        <Badge
                            variant="outline"
                            className="gap-1 text-[10px] border-green-500/40 bg-green-500/10 text-green-400"
                        >
                            <span className="h-1.5 w-1.5 rounded-full bg-green-500 animate-pulse" />
                            Live
                        </Badge>
                        <button
                            onClick={() => setOpen(false)}
                            className="ml-1 rounded-md p-1 text-muted-foreground hover:bg-secondary hover:text-foreground transition-colors"
                            aria-label="Minimize chat"
                        >
                            <Minimize2 className="h-3.5 w-3.5" />
                        </button>
                    </div>
                </div>

                {/* Error banner */}
                {chatError && (
                    <div className="mx-3 mt-2 shrink-0 flex items-center gap-2 rounded-lg border border-destructive/20 bg-destructive/10 px-3 py-2 text-xs text-destructive">
                        <AlertCircle className="h-3.5 w-3.5 shrink-0" />
                        {chatError}
                    </div>
                )}

                {/* Messages */}
                <div className="flex-1 overflow-y-auto px-4 py-3 space-y-4">

                    {/* Quick prompts — shown on empty chat */}
                    {isEmpty && (
                        <div className="pb-1">
                            <p className="mb-2 flex items-center gap-1.5 text-xs text-muted-foreground">
                                <Sparkles className="h-3 w-3 text-primary" />
                                Try asking:
                            </p>
                            <div className="space-y-1.5">
                                {QUICK_PROMPTS.map(({ text, icon }) => (
                                    <button
                                        key={text}
                                        className="flex w-full items-center gap-2.5 rounded-lg border border-border bg-background p-2.5 text-left text-xs hover:bg-accent hover:border-primary/30 transition-colors group"
                                        onClick={() => {
                                            setInputValue(text);
                                            inputRef.current?.focus();
                                        }}
                                    >
                                        <span className="text-base leading-none">{icon}</span>
                                        <span className="flex-1 text-foreground group-hover:text-primary transition-colors">
                                            {text}
                                        </span>
                                        <ChevronRight className="h-3 w-3 text-muted-foreground group-hover:text-primary" />
                                    </button>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* Message list */}
                    {visibleMessages.map((msg) => {
                        const isIntro = msg.id === messages[0]?.id && msg.role === "assistant";
                        return (
                            <div
                                key={msg.id}
                                className={`flex gap-2.5 ${msg.role === "user" ? "flex-row-reverse" : "flex-row"}`}
                            >
                                {/* Avatar */}
                                <div
                                    className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-full
                    ${msg.role === "user"
                                            ? "bg-secondary text-foreground"
                                            : msg.error
                                                ? "bg-destructive/10 text-destructive"
                                                : "bg-primary shadow-sm shadow-primary/20 text-primary-foreground"
                                        }`}
                                >
                                    {msg.role === "user" ? (
                                        <User className="h-3.5 w-3.5" />
                                    ) : msg.error ? (
                                        <AlertCircle className="h-3.5 w-3.5" />
                                    ) : (
                                        <Bot className="h-3.5 w-3.5" />
                                    )}
                                </div>

                                {/* Bubble */}
                                <div className={`flex max-w-[80%] flex-col gap-1.5 ${msg.role === "user" ? "items-end" : "items-start"}`}>
                                    <div
                                        className={`rounded-2xl px-3 py-2 leading-relaxed ${isIntro ? "text-sm" : "text-sm"}
                      ${msg.role === "user"
                                                ? "bg-primary text-primary-foreground rounded-tr-sm"
                                                : msg.error
                                                    ? "bg-destructive/10 text-destructive border border-destructive/20 rounded-tl-sm"
                                                    : "bg-secondary text-foreground rounded-tl-sm"
                                            }`}
                                    >
                                        {msg.text}
                                    </div>

                                    {/* Tool badges */}
                                    {msg.tool_calls?.length > 0 && (
                                        <div className="flex flex-wrap gap-1">
                                            {msg.tool_calls.map((tc, i) => (
                                                <Badge key={i} variant="outline" className={`gap-1 text-[10px] h-5 ${toolColour(tc.tool)}`}>
                                                    <Wrench className="h-2.5 w-2.5" />
                                                    {tc.tool}
                                                </Badge>
                                            ))}
                                        </div>
                                    )}

                                    {/* Meta */}
                                    {(msg.latencyMs != null || msg.model) && (
                                        <div className="flex items-center gap-2 text-[10px] text-muted-foreground">
                                            {msg.latencyMs != null && (
                                                <span className="flex items-center gap-0.5">
                                                    <Clock className="h-2.5 w-2.5" />{msg.latencyMs}ms
                                                </span>
                                            )}
                                            {msg.model && (
                                                <span className="flex items-center gap-0.5">
                                                    <Sparkles className="h-2.5 w-2.5" />{msg.model}
                                                </span>
                                            )}
                                        </div>
                                    )}
                                </div>
                            </div>
                        );
                    })}

                    {/* Typing indicator */}
                    {isLoading && (
                        <div className="flex gap-2.5">
                            <div className="flex h-7 w-7 items-center justify-center rounded-full bg-primary shadow-sm">
                                <Bot className="h-3.5 w-3.5 text-primary-foreground" />
                            </div>
                            <div className="flex items-center gap-1.5 rounded-2xl rounded-tl-sm bg-secondary px-4 py-3">
                                <span className="h-1.5 w-1.5 rounded-full bg-muted-foreground animate-bounce [animation-delay:0ms]" />
                                <span className="h-1.5 w-1.5 rounded-full bg-muted-foreground animate-bounce [animation-delay:150ms]" />
                                <span className="h-1.5 w-1.5 rounded-full bg-muted-foreground animate-bounce [animation-delay:300ms]" />
                            </div>
                        </div>
                    )}

                    <div ref={messagesEndRef} />
                </div>

                {/* Input area */}
                <div className="border-t border-border p-3 bg-card shrink-0">
                    <div className="flex items-end gap-2">
                        <textarea
                            ref={inputRef}
                            rows={1}
                            value={inputValue}
                            onChange={(e) => setInputValue(e.target.value)}
                            onKeyDown={handleKey}
                            placeholder="Ask the AI agent anything…"
                            disabled={isLoading}
                            className="flex-1 resize-none rounded-lg border border-input bg-background px-3 py-2.5 text-sm outline-none
                placeholder:text-muted-foreground focus:border-primary focus:ring-1 focus:ring-primary/30
                disabled:opacity-50 transition-colors min-h-[40px] max-h-[100px] leading-relaxed"
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
        </>
    );
}
