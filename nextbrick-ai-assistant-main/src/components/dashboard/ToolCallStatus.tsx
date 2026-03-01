// ─── components/dashboard/ToolCallStatus.tsx ─────────────────────────────────
// Compact vertical list — fits in the narrow right column of the page layout.
import { Plug, CheckCircle2, Clock, Wifi } from "lucide-react";

const TOOLS = [
  {
    name: "Salesforce",
    status: "Connected",
    latency: "120ms",
    color: "text-blue-400",
    bg: "bg-blue-500/10",
    dot: "bg-blue-400",
  },
  {
    name: "Confluence",
    status: "Connected",
    latency: "85ms",
    color: "text-teal-400",
    bg: "bg-teal-500/10",
    dot: "bg-teal-400",
  },
  {
    name: "AEM DAM",
    status: "Connected",
    latency: "210ms",
    color: "text-orange-400",
    bg: "bg-orange-500/10",
    dot: "bg-orange-400",
  },
  {
    name: "Elasticsearch",
    status: "Connected",
    latency: "42ms",
    color: "text-purple-400",
    bg: "bg-purple-500/10",
    dot: "bg-purple-400",
  },
];

export default function ToolCallStatus() {
  return (
    <div className="rounded-xl border border-border bg-card overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-border px-4 py-3">
        <h3 className="text-xs font-semibold uppercase tracking-widest text-muted-foreground">
          Tool Call Status
        </h3>
        <span className="flex items-center gap-1 text-[10px] text-green-400">
          <Wifi className="h-3 w-3" />
          All systems live
        </span>
      </div>

      {/* Tool list — vertical, compact */}
      <ul className="divide-y divide-border">
        {TOOLS.map(({ name, status, latency, color, bg, dot }) => (
          <li key={name} className="flex items-center gap-3 px-4 py-3">
            {/* Icon */}
            <div className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-lg ${bg}`}>
              <Plug className={`h-3.5 w-3.5 ${color}`} />
            </div>

            {/* Name + latency */}
            <div className="flex-1 min-w-0">
              <p className="text-xs font-semibold text-foreground truncate">{name}</p>
              <p className="flex items-center gap-1 text-[10px] text-muted-foreground">
                <Clock className="h-2.5 w-2.5" />
                {latency}
              </p>
            </div>

            {/* Status pill — no bg-success (doesn't exist in theme) */}
            <span className="flex shrink-0 items-center gap-1 rounded-full bg-green-500/10 px-2 py-0.5 text-[10px] font-medium text-green-400 border border-green-500/20">
              <span className={`h-1.5 w-1.5 rounded-full ${dot} animate-pulse`} />
              {status}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}
