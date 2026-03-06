// ─── store/slices/chatSlice.ts ────────────────────────────────────────────────
// Core state for multi-turn conversations.
// One "session" = one chat thread. Multiple sessions are listed in ChatHistory.
// The `sendMessage` thunk hits POST /api/chat and auto-records metrics.
import { createAction, createAsyncThunk, createSlice, PayloadAction } from "@reduxjs/toolkit";
import { recordRequest } from "./metricsSlice";
import { nanoid } from "@reduxjs/toolkit";

// ── Types ────────────────────────────────────────────────────────────────────

export type ChatRole = "user" | "assistant";

export interface ToolCall {
    tool: string;
    status: string;
    detail: string;
}

export interface ChatMessage {
    id: string;
    role: ChatRole;
    text: string;
    citations: string[];
    tool_calls: ToolCall[];
    /** Reasoning/thinking steps for UI (tool calls, search strategy). */
    thinkingSteps?: string[];
    latencyMs: number | null;
    inputTokens?: number | null;
    outputTokens?: number | null;
    model: string | null;
    timestamp: number;
    error?: boolean;
}

export interface ChatSession {
    id: string;
    title: string;
    createdAt: number;
    updatedAt: number;
    messages: ChatMessage[];
}

export type PendingFulfillPayload = {
    sessionId: string;
    pendingId: string;
    userMsgId: string;
    response: ChatApiResponse;
};

export interface ChatState {
    sessions: ChatSession[];
    activeSessionId: string;
    status: "idle" | "sending" | "error";
    error: string | null;
    /** When the last sendMessage request started (for min thinking time). */
    sentAt: number | null;
    /** Delayed apply: show response after at least 5s thinking. */
    pendingFulfill: { payload: PendingFulfillPayload; mergeAt: number } | null;
}

// ── Helpers ──────────────────────────────────────────────────────────────────

function makeSession(): ChatSession {
    const id = nanoid();
    return {
        id,
        title: "New Chat",
        createdAt: Date.now(),
        updatedAt: Date.now(),
        messages: [
            {
                id: nanoid(),
                role: "assistant",
                text: "Hi! I'm your Keysight AI Assistant. How can I help you today?",
                citations: [],
                tool_calls: [],
                latencyMs: null,
                model: null,
                timestamp: Date.now(),
            },
        ],
    };
}

const firstSession = makeSession();

// Minimum "thinking" time before showing a response.
// Set to 0 to surface the backend reply as soon as it arrives.
const THINKING_MIN_MS = 0;

/** Dispatched after min thinking time to apply delayed chat response. */
export const mergePendingResponse = createAction("chat/mergePendingResponse");

const initialState: ChatState = {
    sessions: [firstSession],
    activeSessionId: firstSession.id,
    status: "idle",
    error: null,
    sentAt: null,
    pendingFulfill: null,
};

// ── Async thunk — POST /api/chat ─────────────────────────────────────────────

interface SendMessageArg {
    sessionId: string;
    message: string;
    modelProfile?: string;
    dataSource?: string;
    language?: string;
}

interface ChatApiResponse {
    reply: string;
    citations: string[];
    tool_calls: ToolCall[];
    thinking_steps?: string[];
    latency_ms: number | null;
    input_tokens?: number | null;
    output_tokens?: number | null;
    model: string;
}

export const sendMessage = createAsyncThunk<
    { sessionId: string; pendingId: string; userMsgId: string; response: ChatApiResponse },
    SendMessageArg,
    { rejectValue: string }
>(
    "chat/sendMessage",
    async ({ sessionId, message, modelProfile, dataSource, language }, { getState, rejectWithValue, dispatch, requestId }) => {
        // Build history from current session state AT TIME OF CALL
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        const state = (getState() as any).chat as ChatState;
        const session = state.sessions.find((s) => s.id === sessionId);
        if (!session) return rejectWithValue("Session not found");

        const history = session.messages
            .filter((m) => !m.error)
            .map((m) => ({ role: m.role as string, content: m.text }));

        // requestId is unique per dispatch call — safe for concurrent sends
        const pendingId = `pending-${requestId}`;
        const userMsgId = nanoid();

        try {
            const res = await fetch("/api/chat", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    message,
                    history,
                    session_id: sessionId,
                    model_profile: modelProfile,
                    data_source: dataSource,
                    language: language ?? "en",
                }),
            });
            if (!res.ok) {
                const detail = await res.text().catch(() => `HTTP ${res.status}`);
                return rejectWithValue(detail);
            }
            const data: ChatApiResponse = await res.json();

            dispatch(
                recordRequest({
                    id: userMsgId,
                    prompt: message.slice(0, 60),
                    latencyMs: data.latency_ms ?? 0,
                    toolsCount: data.tool_calls?.length ?? 0,
                    model: data.model ?? "unknown",
                    timestamp: Date.now(),
                })
            );

            return { sessionId, pendingId, userMsgId, response: data };
        } catch (e) {
            return rejectWithValue(e instanceof Error ? e.message : "Network error");
        }
    }
);

// ── Slice ────────────────────────────────────────────────────────────────────

const chatSlice = createSlice({
    name: "chat",
    initialState,
    reducers: {
        // Create a brand-new session and switch to it
        createSession(state) {
            const s = makeSession();
            state.sessions.unshift(s);
            state.activeSessionId = s.id;
            state.status = "idle";
            state.error = null;
        },
        // Switch active session by id
        setActiveSession(state, { payload }: PayloadAction<string>) {
            if (state.sessions.some((s) => s.id === payload)) {
                state.activeSessionId = payload;
                state.status = "idle";
                state.error = null;
            }
        },
        // Delete session
        deleteSession(state, { payload }: PayloadAction<string>) {
            state.sessions = state.sessions.filter((s) => s.id !== payload);
            if (state.sessions.length === 0) {
                const s = makeSession();
                state.sessions.push(s);
                state.activeSessionId = s.id;
            } else if (state.activeSessionId === payload) {
                state.activeSessionId = state.sessions[0].id;
            }
        },
        clearError(state) {
            state.error = null;
        },
    },
    extraReducers: (builder) => {
        builder

            // PENDING — optimistically add user message; record time for min thinking display
            .addCase(sendMessage.pending, (state, { meta }) => {
                state.status = "sending";
                state.error = null;
                state.sentAt = Date.now();
                state.pendingFulfill = null;
                const { sessionId, message } = meta.arg;
                const pendingId = `pending-${meta.requestId}`;
                const session = state.sessions.find((s) => s.id === sessionId);
                if (session) {
                    session.messages.push({
                        id: pendingId,
                        role: "user",
                        text: message,
                        citations: [],
                        tool_calls: [],
                        latencyMs: null,
                        model: null,
                        timestamp: Date.now(),
                    });
                    session.updatedAt = Date.now();
                    if (session.messages.filter((m) => m.role === "user").length === 1) {
                        session.title = message.slice(0, 40) + (message.length > 40 ? "…" : "");
                    }
                }
            })

            // FULFILLED — show response after min 5s thinking, or immediately if already past 5s
            .addCase(sendMessage.fulfilled, (state, { payload }) => {
                const elapsed = state.sentAt != null ? Date.now() - state.sentAt : 0;
                state.sentAt = null;
                if (elapsed < THINKING_MIN_MS) {
                    state.pendingFulfill = {
                        payload,
                        mergeAt: Date.now() + (THINKING_MIN_MS - elapsed),
                    };
                    state.status = "sending";
                    return;
                }
                state.pendingFulfill = null;
                state.status = "idle";
                const { sessionId, pendingId, userMsgId, response } = payload;
                const session = state.sessions.find((s) => s.id === sessionId);
                if (!session) return;
                const pending = session.messages.find((m) => m.id === pendingId);
                if (pending) pending.id = userMsgId;
                session.messages.push({
                    id: nanoid(),
                    role: "assistant",
                    text: response.reply,
                    citations: response.citations ?? [],
                    tool_calls: response.tool_calls ?? [],
                    thinkingSteps: response.thinking_steps ?? [],
                    latencyMs: response.latency_ms,
                    inputTokens: response.input_tokens ?? null,
                    outputTokens: response.output_tokens ?? null,
                    model: response.model,
                    timestamp: Date.now(),
                });
                session.updatedAt = Date.now();
            })

            // Apply delayed response (after 5s thinking minimum)
            .addCase(mergePendingResponse, (state) => {
                const pf = state.pendingFulfill;
                if (!pf) return;
                state.pendingFulfill = null;
                state.status = "idle";
                const { sessionId, pendingId, userMsgId, response } = pf.payload;
                const session = state.sessions.find((s) => s.id === sessionId);
                if (!session) return;
                const pending = session.messages.find((m) => m.id === pendingId);
                if (pending) pending.id = userMsgId;
                session.messages.push({
                    id: nanoid(),
                    role: "assistant",
                    text: response.reply,
                    citations: response.citations ?? [],
                    tool_calls: response.tool_calls ?? [],
                    thinkingSteps: response.thinking_steps ?? [],
                    latencyMs: response.latency_ms,
                    inputTokens: response.input_tokens ?? null,
                    outputTokens: response.output_tokens ?? null,
                    model: response.model,
                    timestamp: Date.now(),
                });
                session.updatedAt = Date.now();
            })

            // REJECTED — promote pending id and add error bubble
            .addCase(sendMessage.rejected, (state, { payload, meta }) => {
                state.sentAt = null;
                state.pendingFulfill = null;
                state.status = "error";
                state.error = payload ?? "Unknown error";
                const { sessionId } = meta.arg;
                const pendingId = `pending-${meta.requestId}`;
                const session = state.sessions.find((s) => s.id === sessionId);
                if (session) {
                    const pending = session.messages.find((m) => m.id === pendingId);
                    if (pending) pending.id = nanoid();
                    session.messages.push({
                        id: nanoid(),
                        role: "assistant",
                        text: `⚠️ Backend unreachable: ${payload ?? "Unknown error"}. Make sure the Python server is running on port 8000.`,
                        citations: [],
                        tool_calls: [],
                        latencyMs: null,
                        model: null,
                        timestamp: Date.now(),
                        error: true,
                    });
                }
            });
    },
});

export const { createSession, setActiveSession, deleteSession, clearError } =
    chatSlice.actions;
export const chatReducer = chatSlice.reducer;

// ── Selectors ────────────────────────────────────────────────────────────────

import type { RootState } from "../index";

export const selectActiveSession = (state: RootState) =>
    state.chat.sessions.find((s) => s.id === state.chat.activeSessionId) ?? null;

export const selectActiveMessages = (state: RootState) =>
    selectActiveSession(state)?.messages ?? [];

export const selectChatStatus = (state: RootState) => state.chat.status;
export const selectChatError = (state: RootState) => state.chat.error;
export const selectPendingFulfill = (state: RootState) => state.chat.pendingFulfill;
export const selectSessions = (state: RootState) => state.chat.sessions;
export const selectActiveSessionId = (state: RootState) => state.chat.activeSessionId;
