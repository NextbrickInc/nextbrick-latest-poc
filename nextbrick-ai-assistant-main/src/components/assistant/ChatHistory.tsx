// ─── ChatHistory.tsx ──────────────────────────────────────────────────────────
// Sidebar session list. Reads from Redux chatSlice, dispatches createSession /
// setActiveSession / deleteSession.
import { MessageSquare, Clock, Trash2, Settings, Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useAppDispatch, useAppSelector } from "@/store/hooks";
import {
  createSession,
  setActiveSession,
  deleteSession,
  selectSessions,
  selectActiveSessionId,
} from "@/store/slices/chatSlice";

function relativeTime(ts: number) {
  const diff = Date.now() - ts;
  const mins = Math.floor(diff / 60_000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins} min ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs} hour${hrs > 1 ? "s" : ""} ago`;
  return `${Math.floor(hrs / 24)} day${Math.floor(hrs / 24) > 1 ? "s" : ""} ago`;
}

const ChatHistory = () => {
  const dispatch = useAppDispatch();
  const sessions = useAppSelector(selectSessions);
  const activeId = useAppSelector(selectActiveSessionId);

  return (
    <div className="flex h-full flex-col rounded-2xl border border-border bg-card shadow-lg">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-border px-4 py-3">
        <h3 className="text-sm font-semibold text-foreground">Chat History &amp; Settings</h3>
        <Button variant="ghost" size="icon" className="h-7 w-7 text-muted-foreground">
          <Settings className="h-3.5 w-3.5" />
        </Button>
      </div>

      {/* New Chat */}
      <div className="p-3">
        <Button
          variant="outline"
          size="sm"
          className="w-full gap-2 text-xs rounded-full"
          onClick={() => dispatch(createSession())}
        >
          <Plus className="h-3.5 w-3.5" />
          New Chat
        </Button>
      </div>

      {/* Session list */}
      <div className="flex-1 overflow-y-auto px-3 pb-3 space-y-1">
        {sessions.map((session) => {
          const isActive = session.id === activeId;
          const msgCount = session.messages.length;
          const title = session.messages.find((m) => m.role === "user")?.text ?? session.title;
          return (
            <div key={session.id} className="group relative flex items-center">
              <button
                className={`flex w-full items-start gap-3 rounded-lg px-3 py-2.5 text-left transition-colors hover:bg-accent ${isActive ? "bg-accent" : ""
                  }`}
                onClick={() => dispatch(setActiveSession(session.id))}
              >
                <MessageSquare
                  className={`mt-0.5 h-4 w-4 shrink-0 ${isActive ? "text-primary" : "text-muted-foreground"
                    }`}
                />
                <div className="min-w-0 flex-1 pr-6">
                  <p
                    className={`text-xs font-medium truncate ${isActive ? "text-foreground" : "text-foreground/80"
                      }`}
                  >
                    {title}
                  </p>
                  <div className="mt-0.5 flex items-center gap-2">
                    <span className="text-[10px] text-muted-foreground flex items-center gap-1">
                      <Clock className="h-2.5 w-2.5" />
                      {relativeTime(session.updatedAt)}
                    </span>
                    <span className="text-[10px] text-muted-foreground">
                      {msgCount} msg{msgCount !== 1 ? "s" : ""}
                    </span>
                  </div>
                </div>
              </button>

              {/* Delete button — appears on hover */}
              <button
                className="absolute right-2 hidden group-hover:flex h-6 w-6 items-center justify-center rounded text-muted-foreground hover:text-destructive hover:bg-destructive/10 transition-colors"
                onClick={(e) => {
                  e.stopPropagation();
                  dispatch(deleteSession(session.id));
                }}
                aria-label="Delete session"
              >
                <Trash2 className="h-3.5 w-3.5" />
              </button>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default ChatHistory;
