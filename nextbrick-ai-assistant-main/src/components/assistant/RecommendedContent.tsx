// ─── components/assistant/RecommendedContent.tsx ─────────────────────────────
// Recommended documents / use-cases panel — mirrors the Keysight right panel.
import { FileText, ExternalLink, Star } from "lucide-react";
import { Badge } from "@/components/ui/badge";

const ITEMS = [
  {
    title: "VSA & Oscilloscopes — How to undersample safely?",
    source: "Confluence",
    sourceColor: "border-teal-500/40 bg-teal-500/10 text-teal-400",
    stars: 5,
    tag: "Article",
  },
  {
    title: "OTU2 Pulse Mask Template File for use with Oscilloscope",
    source: "AEM DAM",
    sourceColor: "border-orange-500/40 bg-orange-500/10 text-orange-400",
    stars: 4,
    tag: "PDF",
  },
  {
    title: "U1610A Handheld Oscilloscope — Quick Start Guide",
    source: "AEM DAM",
    sourceColor: "border-orange-500/40 bg-orange-500/10 text-orange-400",
    stars: 5,
    tag: "Manual",
  },
  {
    title: "Case deflection: Calibration certificate process overview",
    source: "Salesforce",
    sourceColor: "border-blue-500/40 bg-blue-500/10 text-blue-400",
    stars: 4,
    tag: "Case",
  },
  {
    title: "DSOX1202A Product Page — pricing & specs",
    source: "PIM",
    sourceColor: "border-purple-500/40 bg-purple-500/10 text-purple-400",
    stars: 3,
    tag: "Product",
  },
];

export default function RecommendedContent() {
  return (
    <div className="glass-panel overflow-hidden">
      <div className="border-b border-border px-4 py-3">
        <h3 className="text-xs font-semibold uppercase tracking-widest text-muted-foreground">
          Recommended For You
        </h3>
      </div>
      <ul className="divide-y divide-border">
        {ITEMS.map(({ title, source, sourceColor, stars, tag }) => (
          <li key={title} className="flex items-start gap-3 px-4 py-3 hover:bg-accent transition-colors group cursor-pointer">
            <FileText className="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground group-hover:text-primary transition-colors" />
            <div className="flex-1 min-w-0">
              <p className="text-xs text-foreground/80 group-hover:text-foreground transition-colors line-clamp-2 leading-snug">
                {title}
              </p>
              <div className="mt-1 flex items-center gap-2">
                <Badge variant="outline" className={`text-[9px] h-4 px-1.5 ${sourceColor}`}>
                  {source}
                </Badge>
                <Badge variant="outline" className="text-[9px] h-4 px-1.5 border-border text-muted-foreground">
                  {tag}
                </Badge>
                <span className="flex items-center gap-0.5">
                  {Array.from({ length: stars }).map((_, i) => (
                    <Star key={i} className="h-2.5 w-2.5 fill-yellow-500 text-yellow-500" />
                  ))}
                </span>
              </div>
            </div>
            <ExternalLink className="mt-0.5 h-3 w-3 shrink-0 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity" />
          </li>
        ))}
      </ul>
    </div>
  );
}
