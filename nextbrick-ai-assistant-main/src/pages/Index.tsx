import Navbar from "@/components/assistant/Navbar";
import ChatPanel from "@/components/assistant/ChatPanel";
import ChatHistory from "@/components/assistant/ChatHistory";
import AIToolsGrid from "@/components/assistant/AIToolsGrid";
import RecommendedContent from "@/components/assistant/RecommendedContent";
import SearchResults from "@/components/assistant/SearchResults";
import FrequentQuestions from "@/components/assistant/FrequentQuestions";
import DevicesBar from "@/components/assistant/DevicesBar";
import AgentStatus from "@/components/assistant/AgentStatus";
import FloatingChat from "@/components/assistant/FloatingChat";
import { Search, Mic, Sparkles } from "lucide-react";

import { Badge } from "@/components/ui/badge";

const STACK = ["gpt-oss-20b", "bge-m3", "Elasticsearch OSS", "Kafka", "Spark"];

const Index = () => {
  return (
    <div className="min-h-screen bg-background">
      <Navbar />

      <main className="mx-auto w-full max-w-7xl px-6 py-6">
        {/* ── Main 3-column grid ─────────────────────────────────────────────── */}
        <div className="grid gap-6 lg:grid-cols-[420px,1fr,300px]">
          {/* Left column */}
          <aside className="space-y-6">
            <ChatPanel />
            <FrequentQuestions />
          </aside>

          {/* Center column */}
          <section className="space-y-6">
            {/* ─── Hero Banner ─── */}
            <div className="glass-panel relative overflow-hidden p-6">
              <div className="absolute -right-16 -top-16 h-48 w-48 rounded-full bg-primary/10 blur-3xl" />
              <div className="absolute -left-10 bottom-0 h-32 w-32 rounded-full bg-primary/5 blur-2xl" />

              <div className="relative flex items-center gap-6">
                {/* Left: headline + search */}
                <div className="flex-1 min-w-0">
                  <div className="mb-2 inline-flex items-center gap-1.5 rounded-full border border-primary/30 bg-primary/10 px-3 py-1 text-[11px] font-semibold text-primary">
                    <Sparkles className="h-3 w-3 shrink-0" />
                    Agentic AI · Plan → Retrieve → Act → Verify
                  </div>
                  <h1 className="text-2xl font-extrabold text-foreground leading-tight">
                    Your Intelligent<br />
                    <span className="text-primary">Agentic Assistant</span>
                  </h1>
                  <p className="mt-1 text-sm text-muted-foreground">
                    Multi-turn AI agent with tool orchestration across Salesforce, Confluence, AEM &amp; Elasticsearch.
                  </p>

                  <div className="mt-4 flex items-center gap-2 rounded-full border border-border bg-background/80 px-4 py-2 shadow-sm">
                    <Search className="h-4 w-4 shrink-0 text-muted-foreground" />
                    <input
                      type="text"
                      placeholder="Search or ask anything..."
                      className="min-w-0 flex-1 bg-transparent text-sm outline-none placeholder:text-muted-foreground"
                    />
                    <button className="shrink-0 rounded-full bg-primary px-4 py-1.5 text-xs font-semibold text-primary-foreground">
                      Search
                    </button>
                    <button className="shrink-0 rounded-full border border-border bg-background px-2.5 py-1 text-muted-foreground">
                      <Mic className="h-3.5 w-3.5" />
                    </button>
                  </div>

                  <div className="mt-3 flex flex-wrap gap-2">
                    {STACK.map((item) => (
                      <Badge key={item} variant="outline" className="text-[10px]">
                        {item}
                      </Badge>
                    ))}
                  </div>
                </div>

                {/* Right: Robot + agent loop */}
                <div className="shrink-0 flex flex-col items-center gap-3 w-36">
                  <div className="relative">
                    <div className="absolute inset-0 rounded-full bg-primary/10 blur-2xl" />
                    <img
                      src="/image.png"
                      alt="Nextbrick Agentic AI"
                      className="relative h-28 w-28 object-contain drop-shadow-xl"
                    />
                  </div>
                  <div className="grid grid-cols-2 gap-1.5 w-full">
                    {[
                      { label: "Intent", color: "text-blue-400", bg: "bg-blue-500/10" },
                      { label: "Retrieve", color: "text-teal-400", bg: "bg-teal-500/10" },
                      { label: "Act", color: "text-orange-400", bg: "bg-orange-500/10" },
                      { label: "Verify", color: "text-green-400", bg: "bg-green-500/10" },
                    ].map(({ label, color, bg }) => (
                      <div key={label} className={`rounded-lg ${bg} px-2 py-1.5 text-center`}>
                        <span className={`text-[10px] font-bold ${color}`}>{label}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>


            <div className="grid gap-6 lg:grid-cols-2">
              <AIToolsGrid />
              <AgentStatus />
            </div>

            <SearchResults />
          </section>

          {/* Right column */}
          <aside className="space-y-6">
            <ChatHistory />
          </aside>
        </div>

        {/* ── Bottom row — full width so Recommended + Devices breathe ─────── */}
        <div className="mt-6 grid gap-6 lg:grid-cols-2">
          <RecommendedContent />
          <DevicesBar />
        </div>

        {/* Floating Chat Widget */}
        <FloatingChat />
      </main>
    </div>
  );
};

export default Index;
