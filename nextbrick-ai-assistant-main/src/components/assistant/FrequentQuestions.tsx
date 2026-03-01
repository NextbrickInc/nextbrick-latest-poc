// ─── components/assistant/FrequentQuestions.tsx ──────────────────────────────
// POC test-cases as a clickable FAQ panel — injects prompt directly into chat.
import { useState } from "react";
import { ChevronDown, ChevronUp, ArrowRight } from "lucide-react";
import { useAppDispatch, useAppSelector } from "@/store/hooks";
import { sendMessage, selectActiveSessionId } from "@/store/slices/chatSlice";

const FAQ_ITEMS = [
  {
    category: "Salesforce",
    color: "text-blue-400",
    questions: [
      { q: "Where is my order?", icon: "📦" },
      { q: "What is my service order status?", icon: "🔧" },
      { q: "Create a support case", icon: "🎫" },
      { q: "Give me case status", icon: "📊" },
    ],
  },
  {
    category: "Knowledge & Manuals",
    color: "text-green-400",
    questions: [
      { q: "How to measure my data using oscilloscope?", icon: "📡" },
      { q: "Find the instructions manual of U1610A", icon: "📄" },
      { q: "How do I make an eye diagram using ADS?", icon: "🖥️" },
      { q: "What is jitter?", icon: "❓" },
    ],
  },
  {
    category: "Pricing & Search",
    color: "text-yellow-400",
    questions: [
      { q: "What is the price of DSOX1202A in US?", icon: "💰" },
      { q: "Are there any products with max 2 GSa/s?", icon: "🔍" },
      { q: "Cal certificate status for this asset", icon: "📋" },
      { q: "Give me knowledge articles on calibration", icon: "🧠" },
    ],
  },
];

export default function FrequentQuestions() {
  const dispatch = useAppDispatch();
  const sessionId = useAppSelector(selectActiveSessionId);
  const [open, setOpen] = useState<string | null>("Salesforce");

  return (
    <div className="glass-panel overflow-hidden">
      <div className="border-b border-border px-4 py-3">
        <h3 className="text-xs font-semibold uppercase tracking-widest text-muted-foreground">
          Often Asked Prompts
        </h3>
      </div>
      <div className="divide-y divide-border">
        {FAQ_ITEMS.map(({ category, color, questions }) => {
          const isOpen = open === category;
          return (
            <div key={category}>
              <button
                className="flex w-full items-center justify-between px-4 py-3 text-left hover:bg-accent transition-colors"
                onClick={() => setOpen(isOpen ? null : category)}
                aria-expanded={isOpen}
              >
                <span className={`text-xs font-semibold ${color}`}>{category}</span>
                {isOpen
                  ? <ChevronUp className="h-3.5 w-3.5 text-muted-foreground" />
                  : <ChevronDown className="h-3.5 w-3.5 text-muted-foreground" />
                }
              </button>
              {isOpen && (
                <div className="divide-y divide-border/50 bg-background/50">
                  {questions.map(({ q, icon }) => (
                    <button
                      key={q}
                      className="flex w-full items-center gap-3 px-4 py-2.5 text-left hover:bg-accent transition-colors group"
                      onClick={() => dispatch(sendMessage({ sessionId, message: q }))}
                    >
                      <span className="text-base leading-none">{icon}</span>
                      <span className="flex-1 text-xs text-foreground/80 group-hover:text-foreground transition-colors">
                        {q}
                      </span>
                      <ArrowRight className="h-3 w-3 shrink-0 text-muted-foreground group-hover:text-primary transition-colors" />
                    </button>
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
