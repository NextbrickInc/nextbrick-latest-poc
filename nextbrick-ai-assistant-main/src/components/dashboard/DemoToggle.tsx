import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Server, Cloud } from "lucide-react";

interface DemoToggleProps {
  activeDemo: "onprem" | "cloud";
  onToggle: (demo: "onprem" | "cloud") => void;
}

const onPremStack = ["gpt-oss-20b", "bge-m3", "Elasticsearch OSS", "Kafka", "Spark", "LangChain", "LangGraph"];
const cloudStack = ["Claude Sonnet 4.5", "Elastic Cloud", "GCP"];

const DemoToggle = ({ activeDemo, onToggle }: DemoToggleProps) => (
  <section className="mx-auto max-w-6xl px-6 py-8">
    <div className="mb-6 flex items-center justify-center gap-2">
      <button
        onClick={() => onToggle("onprem")}
        className={`flex items-center gap-2 rounded-lg px-6 py-3 text-sm font-semibold transition-all ${
          activeDemo === "onprem"
            ? "bg-primary text-primary-foreground shadow-lg shadow-primary/25"
            : "bg-secondary text-secondary-foreground hover:bg-secondary/80"
        }`}
      >
        <Server className="h-4 w-4" />
        On-Prem Demo
      </button>
      <button
        onClick={() => onToggle("cloud")}
        className={`flex items-center gap-2 rounded-lg px-6 py-3 text-sm font-semibold transition-all ${
          activeDemo === "cloud"
            ? "bg-primary text-primary-foreground shadow-lg shadow-primary/25"
            : "bg-secondary text-secondary-foreground hover:bg-secondary/80"
        }`}
      >
        <Cloud className="h-4 w-4" />
        Cloud Demo
      </button>
    </div>

    <Card className="border-primary/20 bg-accent/50">
      <CardContent className="p-6">
        {activeDemo === "onprem" ? (
          <div className="text-center">
            <p className="mb-1 text-sm font-medium text-muted-foreground">Infrastructure</p>
            <p className="mb-4 text-lg font-bold text-foreground">Mac Studio · Santa Clara Data Center</p>
            <div className="flex flex-wrap justify-center gap-2">
              {onPremStack.map((t) => (
                <Badge key={t} variant="secondary" className="border border-primary/20 bg-card text-foreground">
                  {t}
                </Badge>
              ))}
            </div>
          </div>
        ) : (
          <div className="text-center">
            <p className="mb-1 text-sm font-medium text-muted-foreground">Infrastructure</p>
            <p className="mb-4 text-lg font-bold text-foreground">Elastic Cloud · Google Cloud Platform</p>
            <div className="flex flex-wrap justify-center gap-2">
              {cloudStack.map((t) => (
                <Badge key={t} variant="secondary" className="border border-primary/20 bg-card text-foreground">
                  {t}
                </Badge>
              ))}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  </section>
);

export default DemoToggle;
