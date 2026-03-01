import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Search, ExternalLink } from "lucide-react";

const results = [
  {
    title: "Product Specification v3.2 — DE",
    summary: "Comprehensive German-language product specification covering dimensions, materials, and compliance certifications for the MX-400 series.",
    source: "Confluence",
    relevance: 0.96,
  },
  {
    title: "Q3 Pipeline Report",
    summary: "Quarterly pipeline analysis showing 34 active opportunities across Manufacturing, Logistics, and Healthcare verticals with €2.4M projected value.",
    source: "Salesforce",
    relevance: 0.91,
  },
  {
    title: "DAM Asset Catalog — Technical Diagrams",
    summary: "Collection of 128 technical diagrams and product renders for the current product lineup, organized by product family.",
    source: "AEM DAM",
    relevance: 0.87,
  },
];

const SearchResultsPanel = () => (
  <Card className="flex h-full flex-col border-border/60">
    <CardHeader className="border-b border-border/40 pb-4">
      <CardTitle className="flex items-center gap-2 text-lg">
        <Search className="h-5 w-5 text-primary" />
        Search Results
      </CardTitle>
    </CardHeader>
    <CardContent className="flex-1 space-y-4 p-4">
      {results.map((r, i) => (
        <div key={i} className="rounded-lg border border-border/40 bg-secondary/30 p-4">
          <div className="mb-2 flex items-start justify-between gap-2">
            <h4 className="text-sm font-semibold text-foreground">{r.title}</h4>
            <ExternalLink className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
          </div>
          <p className="mb-3 text-xs leading-relaxed text-muted-foreground">{r.summary}</p>
          <div className="flex items-center gap-2">
            <Badge variant="outline" className="text-xs">{r.source}</Badge>
            <span className="text-xs text-muted-foreground">Relevance: {(r.relevance * 100).toFixed(0)}%</span>
          </div>
        </div>
      ))}
    </CardContent>
  </Card>
);

export default SearchResultsPanel;
