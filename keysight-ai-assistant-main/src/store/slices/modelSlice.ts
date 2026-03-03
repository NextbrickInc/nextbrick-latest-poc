// ─── store/slices/modelSlice.ts ───────────────────────────────────────────────
// Manages LLM / backend health information fetched on app startup.
// Drives the model badge in the ChatPanel header.
import { createAsyncThunk, createSlice, PayloadAction } from "@reduxjs/toolkit";

export interface ModelState {
    name: string;
    url: string | null;
    esHost: string | null;
    configured: boolean;
    status: "idle" | "loading" | "ready" | "error";
    error: string | null;
}

const initialState: ModelState = {
    name: "…",
    url: null,
    esHost: null,
    configured: false,
    status: "idle",
    error: null,
};

// ── Async thunk — calls GET /api/health ──────────────────────────────────────
export const fetchModelHealth = createAsyncThunk(
    "model/fetchHealth",
    async (_, { rejectWithValue }) => {
        const res = await fetch("/api/health");
        if (!res.ok) return rejectWithValue(`HTTP ${res.status}`);
        return (await res.json()) as {
            ok: boolean;
            model_configured: boolean;
            model_name: string;
            model_url: string | null;
            es_host: string | null;
        };
    }
);

const modelSlice = createSlice({
    name: "model",
    initialState,
    reducers: {
        setModelName(state, action: PayloadAction<string>) {
            state.name = action.payload;
        },
    },
    extraReducers: (builder) => {
        builder
            .addCase(fetchModelHealth.pending, (state) => {
                state.status = "loading";
                state.error = null;
            })
            .addCase(fetchModelHealth.fulfilled, (state, { payload }) => {
                state.status = "ready";
                state.name = payload.model_name ?? "unknown";
                state.url = payload.model_url ?? null;
                state.esHost = payload.es_host ?? null;
                state.configured = payload.model_configured;
            })
            .addCase(fetchModelHealth.rejected, (state, { payload }) => {
                state.status = "error";
                state.error = String(payload ?? "Network error");
                state.name = "backend offline";
            });
    },
});

export const { setModelName } = modelSlice.actions;
export const modelReducer = modelSlice.reducer;
