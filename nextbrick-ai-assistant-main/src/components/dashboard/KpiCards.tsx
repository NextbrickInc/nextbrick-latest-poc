import { Card, CardContent } from "@/components/ui/card";
import { FileText, Globe, Zap, Clock } from "lucide-react";

const kpis = [
  { label: "Indexed Docs", value: "5,000", icon: FileText, color: "text-primary" },
  { label: "Languages", value: "4–8", icon: Globe, color: "text-primary" },
  { label: "Target QPS", value: "20–30", icon: Zap, color: "text-primary" },
  { label: "Latency", value: "<2s", icon: Clock, color: "text-primary" },
];

const KpiCards = () => (
  <section className="mx-auto max-w-6xl px-6 py-6">
    <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
      {kpis.map((kpi) => (
        <Card key={kpi.label} className="border-border/60 shadow-sm">
          <CardContent className="flex flex-col items-center p-6 text-center">
            <kpi.icon className={`mb-3 h-8 w-8 ${kpi.color}`} />
            <p className="text-3xl font-extrabold text-foreground">{kpi.value}</p>
            <p className="mt-1 text-sm font-medium text-muted-foreground">{kpi.label}</p>
          </CardContent>
        </Card>
      ))}
    </div>
  </section>
);

export default KpiCards;
