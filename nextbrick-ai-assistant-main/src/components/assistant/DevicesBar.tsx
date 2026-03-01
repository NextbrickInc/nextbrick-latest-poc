// ─── components/assistant/DevicesBar.tsx ─────────────────────────────────────
// Your Applications & Devices — horizontal scrollable tile row
import { Monitor, Cpu, Zap, Network } from "lucide-react";

const DEVICES = [
  { name: "Oscilloscopes", icon: Monitor, count: 12, color: "text-blue-400", bg: "bg-blue-500/10" },
  { name: "Signal Analyzers", icon: Cpu, count: 8, color: "text-purple-400", bg: "bg-purple-500/10" },
  { name: "Power Supplies", icon: Zap, count: 5, color: "text-yellow-400", bg: "bg-yellow-500/10" },
  { name: "Network Test", icon: Network, count: 3, color: "text-teal-400", bg: "bg-teal-500/10" },
];

export default function DevicesBar() {
  return (
    <div className="glass-panel p-4">
      <h3 className="mb-3 text-xs font-semibold uppercase tracking-widest text-muted-foreground">
        Your Applications &amp; Devices
      </h3>
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        {DEVICES.map(({ name, icon: Icon, count, color, bg }) => (
          <button
            key={name}
            className="flex flex-col items-center gap-1.5 rounded-xl border border-border bg-background p-3
              hover:border-primary/30 hover:bg-accent transition-all hover:-translate-y-0.5 text-center"
          >
            <div className={`flex h-9 w-9 items-center justify-center rounded-lg ${bg}`}>
              <Icon className={`h-4.5 w-4.5 ${color}`} style={{ width: 18, height: 18 }} />
            </div>
            <span className="text-[10px] font-medium text-foreground/80 leading-tight">{name}</span>
            <span className="text-[9px] text-muted-foreground">{count} items</span>
          </button>
        ))}
      </div>
    </div>
  );
}
