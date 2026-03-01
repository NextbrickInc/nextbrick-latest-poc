// ─── components/assistant/AIToolsGrid.tsx ────────────────────────────────────
// Agentic AI capabilities showcase — maps directly to POC use-cases.
import { Code2, FileText, BarChart3, Image, Wrench, Search, Zap, Brain } from "lucide-react";

const TOOLS = [
  { icon: Wrench, label: "Tool Orchestrator", desc: "Salesforce, SQL, AEM, Confluence", color: "text-blue-400", bg: "bg-blue-500/10" },
  { icon: Search, label: "Semantic Search", desc: "Vector + keyword retrieval", color: "text-primary", bg: "bg-primary/10" },
  { icon: FileText, label: "Text Summary", desc: "Cited answers & snippets", color: "text-green-400", bg: "bg-green-500/10" },
  { icon: BarChart3, label: "Spec Analysis", desc: "Filter by product metrics", color: "text-yellow-400", bg: "bg-yellow-500/10" },
  { icon: Code2, label: "Code Generator", desc: "Automation & scripts", color: "text-purple-400", bg: "bg-purple-500/10" },
  { icon: Image, label: "PDF / Manual", desc: "AEM DAM lookup", color: "text-orange-400", bg: "bg-orange-500/10" },
  { icon: Brain, label: "Agentic Loop", desc: "Plan → Retrieve → Act", color: "text-teal-400", bg: "bg-teal-500/10" },
  { icon: Zap, label: "Pricing Lookup", desc: "Dynamic, region-aware", color: "text-pink-400", bg: "bg-pink-500/10" },
];

export default function AIToolsGrid() {
  return (
    <div className="glass-panel p-4">
      <div className="mb-3 flex items-center justify-between">
        <h3 className="text-xs font-semibold uppercase tracking-widest text-muted-foreground">
          AI Tools
        </h3>
        <span className="text-[10px] text-muted-foreground">Agentic modules</span>
      </div>
      <div className="grid grid-cols-2 gap-3">
        {TOOLS.map(({ icon: Icon, label, desc, color, bg }) => (
          <div
            key={label}
            className={`rounded-2xl border border-border ${bg} p-3 transition-all hover:-translate-y-0.5 hover:shadow-md`}
          >
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-background shadow-sm">
              <Icon className={`h-4 w-4 ${color}`} />
            </div>
            <p className="mt-2 text-sm font-semibold text-foreground">{label}</p>
            <p className="text-[11px] text-muted-foreground">{desc}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
