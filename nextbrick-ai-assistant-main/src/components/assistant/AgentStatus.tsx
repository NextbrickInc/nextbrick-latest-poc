import { Brain, Search, Wrench, ShieldCheck } from "lucide-react";

const STEPS = [
  { label: "Plan", desc: "Intent + context", icon: Brain, status: "active" },
  { label: "Retrieve", desc: "Vector + keyword search", icon: Search, status: "active" },
  { label: "Act", desc: "Tool calls & workflows", icon: Wrench, status: "queued" },
  { label: "Verify", desc: "Citations + confidence", icon: ShieldCheck, status: "idle" },
];

const STATUS_STYLES: Record<string, string> = {
  active: "bg-primary/10 text-primary border-primary/30",
  queued: "bg-warning/10 text-warning border-warning/30",
  idle: "bg-muted text-muted-foreground border-border",
};

export default function AgentStatus() {
  return (
    <div className="glass-panel p-4">
      <div className="flex items-center justify-between">
        <h3 className="text-xs font-semibold uppercase tracking-widest text-muted-foreground">
          Agentic Loop
        </h3>
        <span className="rounded-full bg-primary/10 px-2 py-0.5 text-[10px] font-medium text-primary">
          Live
        </span>
      </div>
      <div className="mt-3 space-y-2">
        {STEPS.map(({ label, desc, icon: Icon, status }) => (
          <div key={label} className="flex items-center gap-3 rounded-xl border border-border bg-background px-3 py-2">
            <div className={`flex h-8 w-8 items-center justify-center rounded-lg border ${STATUS_STYLES[status]}`}>
              <Icon className="h-4 w-4" />
            </div>
            <div className="flex-1">
              <p className="text-sm font-semibold text-foreground">{label}</p>
              <p className="text-[11px] text-muted-foreground">{desc}</p>
            </div>
            <span className={`rounded-full border px-2 py-0.5 text-[10px] ${STATUS_STYLES[status]}`}>
              {status}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
