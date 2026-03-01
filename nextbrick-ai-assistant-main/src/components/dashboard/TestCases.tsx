import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { CheckCircle2, XCircle, Clock } from "lucide-react";

const tests = [
  { id: "TC-01", name: "Multilingual doc retrieval (EN→DE)", status: "pass" },
  { id: "TC-02", name: "Multi-turn conversation context retention", status: "pass" },
  { id: "TC-03", name: "Salesforce tool call with CRM data", status: "pass" },
  { id: "TC-04", name: "Confluence knowledge base search", status: "pass" },
  { id: "TC-05", name: "AEM DAM asset retrieval", status: "pending" },
  { id: "TC-06", name: "End-to-end latency under 2s target", status: "fail" },
];

const statusConfig = {
  pass: { icon: CheckCircle2, label: "Pass", className: "bg-success text-success-foreground" },
  fail: { icon: XCircle, label: "Fail", className: "bg-destructive text-destructive-foreground" },
  pending: { icon: Clock, label: "Pending", className: "bg-warning text-warning-foreground" },
};

const TestCases = () => (
  <section className="mx-auto max-w-6xl px-6 py-6">
    <h2 className="mb-4 text-xl font-bold text-foreground">Test Case Validation</h2>
    <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
      {tests.map((t) => {
        const cfg = statusConfig[t.status as keyof typeof statusConfig];
        const Icon = cfg.icon;
        return (
          <Card key={t.id} className="border-border/60">
            <CardContent className="flex items-center gap-3 p-4">
              <Icon className={`h-5 w-5 shrink-0 ${t.status === "pass" ? "text-success" : t.status === "fail" ? "text-destructive" : "text-warning"}`} />
              <div className="flex-1 min-w-0">
                <p className="text-xs font-mono text-muted-foreground">{t.id}</p>
                <p className="text-sm font-medium text-foreground truncate">{t.name}</p>
              </div>
              <Badge className={cfg.className}>{cfg.label}</Badge>
            </CardContent>
          </Card>
        );
      })}
    </div>
  </section>
);

export default TestCases;
