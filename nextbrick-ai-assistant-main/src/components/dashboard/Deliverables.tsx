import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { ClipboardList } from "lucide-react";

const deliverables = [
  { text: "Agentic chatbot with multi-turn RAG pipeline", done: true },
  { text: "Hybrid search (vector + BM25) across 5,000 docs", done: true },
  { text: "Tool calling integration (Salesforce, Confluence, AEM)", done: true },
  { text: "On-prem vs Cloud deployment comparison report", done: false },
  { text: "Performance benchmark suite with 6 test cases", done: false },
  { text: "Architecture documentation and handoff package", done: false },
];

const Deliverables = () => (
  <section className="mx-auto max-w-6xl px-6 py-6">
    <h2 className="mb-4 text-xl font-bold text-foreground">Key Deliverables</h2>
    <Card className="border-border/60">
      <CardContent className="space-y-3 p-6">
        {deliverables.map((d, i) => (
          <div key={i} className="flex items-center gap-3">
            <Checkbox checked={d.done} className="pointer-events-none" />
            <span className={`text-sm ${d.done ? "text-muted-foreground line-through" : "text-foreground font-medium"}`}>
              {d.text}
            </span>
          </div>
        ))}
      </CardContent>
    </Card>
  </section>
);

export default Deliverables;
