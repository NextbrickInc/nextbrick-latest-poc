// components/search/GeneratedAnswer.tsx
// Collapsible AI-generated answer section for the support search page.
import { useState } from "react";
import { ChevronDown, ChevronUp, Sparkles } from "lucide-react";
import { MarkdownMessage } from "@/components/assistant/MarkdownMessage";
import { Badge } from "@/components/ui/badge";

interface GeneratedAnswerProps {
  answer: string | null;
  isLoading?: boolean;
}

export function GeneratedAnswer({ answer, isLoading }: GeneratedAnswerProps) {
  const [enabled, setEnabled] = useState(true);
  const [expanded, setExpanded] = useState(true);

  if (!answer && !isLoading) return null;

  return (
    <div className="rounded-lg border border-border bg-card mb-4">
      <div className="flex items-center justify-between px-4 py-2.5">
        <button
          type="button"
          onClick={() => setExpanded(!expanded)}
          className="flex items-center gap-2"
        >
          <Badge
            variant="outline"
            className="gap-1 border-primary/30 bg-primary/5 text-primary text-xs"
          >
            <Sparkles className="h-3 w-3" />
            Generated Answer
          </Badge>
          {expanded ? (
            <ChevronUp className="h-4 w-4 text-muted-foreground" />
          ) : (
            <ChevronDown className="h-4 w-4 text-muted-foreground" />
          )}
        </button>

        {/* Toggle switch */}
        <button
          type="button"
          onClick={() => setEnabled(!enabled)}
          className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors ${
            enabled ? "bg-primary" : "bg-muted-foreground/30"
          }`}
        >
          <span
            className={`inline-block h-3.5 w-3.5 transform rounded-full bg-white shadow transition-transform ${
              enabled ? "translate-x-4.5" : "translate-x-0.5"
            }`}
            style={{ transform: enabled ? "translateX(18px)" : "translateX(2px)" }}
          />
        </button>
      </div>

      {expanded && enabled && (
        <div className="border-t border-border px-4 py-3">
          {isLoading ? (
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <div className="h-4 w-4 animate-spin rounded-full border-2 border-primary border-t-transparent" />
              Generating answer...
            </div>
          ) : answer ? (
            <div className="prose prose-sm max-w-none text-sm">
              <MarkdownMessage content={answer} />
            </div>
          ) : null}
          <p className="mt-2 text-[10px] text-muted-foreground italic">
            This response is AI generated for your convenience. Keysight Technologies is not liable
            for inaccuracies. Contact our Support team for validation.
          </p>
        </div>
      )}
    </div>
  );
}
