import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { BarChart3 } from "lucide-react";

const metrics = [
  { metric: "Tokens In", paid: "~4,000", oss: "~4,200" },
  { metric: "Tokens Out", paid: "~1,200", oss: "~1,400" },
  { metric: "Setup Time", paid: "2 hours", oss: "8 hours" },
  { metric: "LLM Latency", paid: "0.8s", oss: "1.4s" },
  { metric: "ES Latency", paid: "45ms", oss: "120ms" },
  { metric: "Tool Calls", paid: "3 avg", oss: "3 avg" },
  { metric: "Accuracy", paid: "94%", oss: "87%" },
];

const MetricsTable = () => (
  <section className="mx-auto max-w-6xl px-6 py-6 pb-16">
    <h2 className="mb-4 text-xl font-bold text-foreground">Metrics Comparison</h2>
    <Card className="border-border/60 overflow-hidden">
      <CardContent className="p-0">
        <Table>
          <TableHeader>
            <TableRow className="bg-secondary/50">
              <TableHead className="font-semibold text-foreground">Metric</TableHead>
              <TableHead className="font-semibold text-foreground">Paid (Cloud)</TableHead>
              <TableHead className="font-semibold text-foreground">OSS (On-Prem)</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {metrics.map((m) => (
              <TableRow key={m.metric}>
                <TableCell className="font-medium text-foreground">{m.metric}</TableCell>
                <TableCell className="text-muted-foreground">{m.paid}</TableCell>
                <TableCell className="text-muted-foreground">{m.oss}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  </section>
);

export default MetricsTable;
