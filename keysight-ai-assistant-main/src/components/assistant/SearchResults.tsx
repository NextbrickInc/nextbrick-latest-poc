// ─── components/assistant/SearchResults.tsx ─────────────────────────────────
// Semantic search results panel with relevance bars and source badges.
import { ExternalLink, FileText, BarChart3, Code2, Database, BookOpen, Search } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { Badge } from "@/components/ui/badge";

const SOURCE_COLORS: Record<string, string> = {
  Confluence: "border-teal-500/40 bg-teal-500/10 text-teal-400",
  Salesforce: "border-blue-500/40 bg-blue-500/10 text-blue-400",
  "AEM DAM": "border-orange-500/40 bg-orange-500/10 text-orange-400",
  "Knowledge Base": "border-purple-500/40 bg-purple-500/10 text-purple-400",
};

const RESULTS = [
  {
    title: "U1610A Oscilloscope — Instructions Manual",
    summary: "Full quick-start and calibration guide for the U1610A handheld oscilloscope. Covers measurement setup, waveform analysis, and SCPI commands.",
    source: "AEM DAM",
    relevance: 98,
    tag: "PDF Manual",
    icon: FileText,
  },
  {
    title: "Product Specification v3.2 — German Edition",
    summary: "Comprehensive German-language specifications covering dimensions, materials, and compliance certifications for the MX-400 series.",
    source: "Confluence",
    relevance: 96,
    tag: "Article",
    icon: BookOpen,
  },
  {
    title: "Q3 Pipeline Analysis Report",
    summary: "Quarterly pipeline analysis showing 34 active opportunities across Manufacturing, Logistics, and Healthcare verticals worth €2.4M.",
    source: "Salesforce",
    relevance: 91,
    tag: "Report",
    icon: BarChart3,
  },
  {
    title: "DAM Asset Catalog — Technical Diagrams",
    summary: "Collection of 128 technical diagrams and product renders for the current lineup, organized by product family.",
    source: "AEM DAM",
    relevance: 87,
    tag: "Asset",
    icon: Database,
  },
  {
    title: "Python Signal Analysis Script",
    summary: "Ready-to-use Python script for automating oscilloscope measurements using the PyVISA library.",
    source: "Knowledge Base",
    relevance: 84,
    tag: "Code",
    icon: Code2,
  },
];

export default function SearchResults() {
  const navigate = useNavigate();

  return (
    <div className="glass-panel overflow-hidden flex flex-col h-full">
      <div className="flex items-center justify-between border-b border-border px-4 py-3">
        <div>
          <h3 className="text-sm font-semibold text-foreground">AI Assistance Hub</h3>
          <p className="text-[11px] text-muted-foreground">
            Summaries and citations from your indexed sources.
          </p>
        </div>
        <span className="rounded-full bg-primary/10 px-2.5 py-0.5 text-[10px] font-medium text-primary">
          {RESULTS.length} results
        </span>
      </div>

      {/* Results list */}
      <ul className="divide-y divide-border">
        {RESULTS.map((r, i) => (
          <li
            key={i}
            className="group flex items-start gap-3 px-4 py-3 hover:bg-accent transition-colors cursor-pointer"
          >
            {/* Icon */}
            <div className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-secondary group-hover:bg-background transition-colors">
              <r.icon className="h-4 w-4 text-muted-foreground group-hover:text-primary transition-colors" />
            </div>

            {/* Content */}
            <div className="flex-1 min-w-0">
              <div className="flex items-start gap-2">
                <p className="flex-1 text-xs font-semibold text-foreground group-hover:text-primary transition-colors leading-snug">
                  {r.title}
                </p>
                <ExternalLink className="mt-0.5 h-3 w-3 shrink-0 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity" />
              </div>
              <p className="mt-0.5 text-[11px] text-muted-foreground line-clamp-2 leading-relaxed">
                {r.summary}
              </p>

              {/* Meta row */}
              <div className="mt-2 flex items-center gap-2 flex-wrap">
                <Badge
                  variant="outline"
                  className={`text-[10px] h-4 px-1.5 py-0 ${SOURCE_COLORS[r.source] ?? "border-border text-muted-foreground"}`}
                >
                  {r.source}
                </Badge>
                <Badge variant="outline" className="text-[10px] h-4 px-1.5 py-0 border-border text-muted-foreground">
                  {r.tag}
                </Badge>
                {/* Relevance bar */}
                <div className="flex items-center gap-1.5 ml-auto">
                  <div className="h-1.5 w-20 rounded-full bg-secondary overflow-hidden">
                    <div
                      className="h-full rounded-full bg-primary transition-all"
                      style={{ width: `${r.relevance}%` }}
                    />
                  </div>
                  <span className="text-[10px] text-muted-foreground font-medium">{r.relevance}%</span>
                </div>
              </div>
            </div>
          </li>
        ))}
      </ul>

      {/* View more link */}
      <div className="mt-auto border-t border-border bg-muted/20 p-3">
        <button
          onClick={() => navigate("/search")}
          className="flex w-full items-center justify-center gap-2 rounded-md bg-secondary px-3 py-2 text-xs font-medium text-foreground hover:bg-secondary/80 transition-colors"
        >
          <Search className="h-3.5 w-3.5" />
          Advanced Global Search
        </button>
      </div>
    </div>
  );
}
