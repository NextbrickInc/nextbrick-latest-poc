import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { MessageSquare, Send } from "lucide-react";

const sampleConversation = [
  { role: "user" as const, text: "Find product specs in German" },
  { role: "assistant" as const, text: "I found 12 product specification documents in German across your Confluence and AEM DAM repositories. The most relevant is 'Produktspezifikation_v3.2.pdf' from Q3 2024." },
  { role: "user" as const, text: "Summarize Q3 pipeline" },
  { role: "assistant" as const, text: "Q3 pipeline shows 34 active opportunities worth €2.4M total. Top segments: Manufacturing (40%), Logistics (28%), Healthcare (18%). 8 deals in final negotiation stage." },
];

const samplePrompts = ["Find product specs in German", "Summarize Q3 pipeline", "Compare vendor proposals", "List open support tickets"];

const ChatbotPanel = () => (
  <Card className="flex h-full flex-col border-border/60">
    <CardHeader className="border-b border-border/40 pb-4">
      <CardTitle className="flex items-center gap-2 text-lg">
        <MessageSquare className="h-5 w-5 text-primary" />
        Agentic Chatbot
      </CardTitle>
    </CardHeader>
    <CardContent className="flex flex-1 flex-col p-4">
      <div className="flex-1 space-y-3 overflow-y-auto">
        {sampleConversation.map((msg, i) => (
          <div key={i} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
            <div
              className={`max-w-[85%] rounded-xl px-4 py-2.5 text-sm ${
                msg.role === "user"
                  ? "bg-primary text-primary-foreground"
                  : "bg-secondary text-secondary-foreground"
              }`}
            >
              {msg.text}
            </div>
          </div>
        ))}
      </div>
      <div className="mt-4 flex flex-wrap gap-2">
        {samplePrompts.map((p) => (
          <Badge key={p} variant="outline" className="cursor-pointer text-xs hover:bg-accent">
            {p}
          </Badge>
        ))}
      </div>
      <div className="mt-3 flex items-center gap-2 rounded-lg border border-input bg-card px-3 py-2">
        <input
          type="text"
          placeholder="Ask a question..."
          className="flex-1 bg-transparent text-sm outline-none placeholder:text-muted-foreground"
          readOnly
        />
        <Send className="h-4 w-4 text-primary" />
      </div>
    </CardContent>
  </Card>
);

export default ChatbotPanel;
