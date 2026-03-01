// ─── store/api/chatApi.ts ─────────────────────────────────────────────────────
// RTK-Query service for direct API calls that benefit from caching/polling.
// Currently handles: GET /api/health, GET /api/metrics (future).
// POST /api/chat is handled by the sendMessage async thunk in chatSlice
// because we need optimistic updates and side-effects (metrics recording).
import { createApi, fetchBaseQuery } from "@reduxjs/toolkit/query/react";

// ── Types ───────────────────────────────────────────────────────────────────

export interface HealthResponse {
    ok: boolean;
    model_configured: boolean;
    model_name: string;
    model_url: string | null;
    es_host: string | null;
}

export interface BackendMetrics {
    total_requests: number;
    avg_latency_ms: number;
    tool_calls_total: number;
    uptime_seconds: number;
}

// ── API Definition ───────────────────────────────────────────────────────────

export const chatApi = createApi({
    reducerPath: "chatApi",
    baseQuery: fetchBaseQuery({ baseUrl: "/" }),
    tagTypes: ["Health", "Metrics"],
    endpoints: (build) => ({
        getHealth: build.query<HealthResponse, void>({
            query: () => "api/health",
            providesTags: ["Health"],
            // Re-check every 30 s so the badge stays live if the backend restarts
            keepUnusedDataFor: 30,
        }),
        getBackendMetrics: build.query<BackendMetrics, void>({
            query: () => "api/metrics",
            providesTags: ["Metrics"],
            keepUnusedDataFor: 10,
        }),
    }),
});

export const { useGetHealthQuery, useGetBackendMetricsQuery } = chatApi;
