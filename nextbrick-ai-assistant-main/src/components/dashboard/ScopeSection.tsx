import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { CheckCircle2, XCircle } from "lucide-react";

const inScope = [
  "Multi-turn agentic chatbot with RAG",
  "Multilingual search (EN, DE, FR, ES)",
  "Tool orchestration (Salesforce, Confluence, AEM)",
  "On-prem + Cloud deployment comparison",
  "Elasticsearch vector + keyword hybrid search",
  "Performance benchmarking & metrics",
];

const outOfScope = [
  "Production-grade deployment",
  "SSO / enterprise auth integration",
  "Custom model fine-tuning",
  "Real-time data streaming pipelines",
  "Mobile application interfaces",
  "Data migration services",
];

const ScopeSection = () => (
  <section className="mx-auto max-w-6xl px-6 py-6">
    <h2 className="mb-4 text-xl font-bold text-foreground">Scope</h2>
    <div className="grid gap-4 md:grid-cols-2">
      <Card className="border-success/30 bg-success/5">
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-base text-success">
            <CheckCircle2 className="h-5 w-5" />
            In Scope
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          {inScope.map((item) => (
            <div key={item} className="flex items-start gap-2 text-sm text-foreground">
              <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-success" />
              {item}
            </div>
          ))}
        </CardContent>
      </Card>
      <Card className="border-destructive/30 bg-destructive/5">
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-base text-destructive">
            <XCircle className="h-5 w-5" />
            Out of Scope
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          {outOfScope.map((item) => (
            <div key={item} className="flex items-start gap-2 text-sm text-foreground">
              <XCircle className="mt-0.5 h-4 w-4 shrink-0 text-destructive" />
              {item}
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  </section>
);

export default ScopeSection;
