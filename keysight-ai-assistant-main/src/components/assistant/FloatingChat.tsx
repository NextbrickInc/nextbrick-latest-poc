import React, { useState, useEffect, useRef } from "react";
import { MessageSquare, X, Bot, User, Send } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";

const THINKING_STEPS = [
  { label: "Planning", icon: "🧠", color: "text-blue-500" },
  { label: "Retrieving", icon: "🔍", color: "text-purple-500" },
  { label: "Acting", icon: "⚡", color: "text-yellow-500" }
];

function ThinkingSteps() {
  const [step, setStep] = useState(0);
  useEffect(() => {
    const interval = setInterval(() => setStep(s => (s < 2 ? s + 1 : s)), 2000);
    return () => clearInterval(interval);
  }, []);
  return (
    <div className="space-y-2 py-1">
      {THINKING_STEPS.map((s, i) => (
        <div key={s.label} className={"flex items-center gap-2 text-[11px] transition-opacity duration-500 " + (i > step ? "opacity-30" : "opacity-100")}>
          <span className={i <= step ? "text-green-500" : s.color}>{i <= step ? "✓" : s.icon}</span>
          <span className="font-medium text-foreground/80">{s.label}{i === step ? "..." : ""}</span>
        </div>
      ))}
    </div>
  );
}

export default function FloatingChat() {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState([{ role: "assistant", content: "Hello! I am Keysight's AI Assistant. How can I help you today?" }]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;
    
    const userMsg = input.trim();
    setInput("");
    setMessages(prev => [...prev, { role: "user", content: userMsg }]);
    setIsLoading(true);

    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ history: messages, new_message: userMsg }),
      });
      const data = await res.json();
      setMessages(prev => [...prev, { role: "assistant", content: data.output }]);
    } catch (err) {
      setMessages(prev => [...prev, { role: "assistant", content: "Sorry, there was an error." }]);
    } finally {
      setIsLoading(false);
    }
  };

  if (!open) {
    return (
      <Button onClick={() => setOpen(true)} className="fixed bottom-6 right-6 h-14 w-14 rounded-full shadow-lg" size="icon">
        <MessageSquare className="h-6 w-6" />
      </Button>
    );
  }

  return (
    <div className="fixed bottom-6 right-6 flex h-[500px] w-[380px] flex-col overflow-hidden rounded-2xl border bg-background shadow-2xl z-50">
      <div className="flex items-center justify-between border-b p-4 bg-muted/30">
        <div className="flex items-center gap-2">
          <Bot className="h-5 w-5 text-primary" />
          <span className="font-semibold">Keysight AI</span>
          <Badge variant="outline" className="gap-1 border-green-500/40 bg-green-500/10 text-green-600 text-[10px]">
            <span className="h-1.5 w-1.5 rounded-full bg-green-500 animate-pulse" /> Live
          </Badge>
        </div>
        <Button variant="ghost" size="icon" className="h-8 w-8 rounded-full" onClick={() => setOpen(false)}>
          <X className="h-4 w-4" />
        </Button>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((m, i) => (
          <div key={i} className={"flex gap-2 " + (m.role === "user" ? "flex-row-reverse" : "")}>
            <div className={"flex h-7 w-7 items-center justify-center rounded-full shrink-0 " + (m.role === "user" ? "bg-muted" : "bg-primary")}>
              {m.role === "user" ? <User className="h-3.5 w-3.5 text-muted-foreground" /> : <Bot className="h-3.5 w-3.5 text-primary-foreground" />}
            </div>
            <div className={"rounded-2xl px-4 py-2.5 max-w-[80%] text-sm " + (m.role === "user" ? "bg-primary text-primary-foreground rounded-tr-sm" : "bg-muted rounded-tl-sm")}>
              {m.content}
            </div>
          </div>
        ))}
        
        {isLoading && (
          <div className="flex gap-2.5">
            <div className="flex h-7 w-7 items-center justify-center rounded-full bg-primary shrink-0">
              <Bot className="h-3.5 w-3.5 text-primary-foreground" />
            </div>
            <div className="flex flex-col gap-1.5 rounded-2xl rounded-tl-sm bg-muted px-4 py-3 min-w-[160px]">
              <ThinkingSteps />
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      <div className="border-t p-3 bg-background">
        <form onSubmit={handleSubmit} className="flex gap-2">
          <Input 
            value={input} 
            onChange={(e) => setInput(e.target.value)} 
            placeholder="Ask Keysight AI..." 
            disabled={isLoading}
            className="flex-1"
          />
          <Button type="submit" size="icon" disabled={isLoading || !input.trim()}>
            <Send className="h-4 w-4" />
          </Button>
        </form>
      </div>
    </div>
  );
}
