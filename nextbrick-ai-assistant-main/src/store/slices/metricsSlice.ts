// ─── store/slices/metricsSlice.ts ─────────────────────────────────────────────
// Tracks per-session performance metrics for the POC comparison table.
// Updated automatically by chatSlice after every successful LLM response.
import { createSlice, PayloadAction } from "@reduxjs/toolkit";

export interface RequestMetric {
    id: string;           // message id
    prompt: string;       // first 60 chars
    latencyMs: number;
    toolsCount: number;
    model: string;
    timestamp: number;    // Date.now()
}

export interface MetricsState {
    requests: RequestMetric[];
    totalRequests: number;
    avgLatencyMs: number;
    totalToolCalls: number;
}

const initialState: MetricsState = {
    requests: [],
    totalRequests: 0,
    avgLatencyMs: 0,
    totalToolCalls: 0,
};

const metricsSlice = createSlice({
    name: "metrics",
    initialState,
    reducers: {
        recordRequest(state, { payload }: PayloadAction<RequestMetric>) {
            state.requests.unshift(payload); // newest first
            if (state.requests.length > 50) state.requests.pop(); // rolling 50
            state.totalRequests += 1;
            state.totalToolCalls += payload.toolsCount;
            const total = state.requests.reduce((s, r) => s + r.latencyMs, 0);
            state.avgLatencyMs = Math.round(total / state.requests.length);
        },
        clearMetrics(state) {
            Object.assign(state, initialState);
        },
    },
});

export const { recordRequest, clearMetrics } = metricsSlice.actions;
export const metricsReducer = metricsSlice.reducer;
