// ─── store/index.ts ───────────────────────────────────────────────────────────
// Root Redux store. Combines all slice reducers + RTK-Query middleware.
import { configureStore } from "@reduxjs/toolkit";
import { chatReducer } from "./slices/chatSlice";
import { modelReducer } from "./slices/modelSlice";
import { metricsReducer } from "./slices/metricsSlice";
import { chatApi } from "./api/chatApi";

export const store = configureStore({
    reducer: {
        chat: chatReducer,
        model: modelReducer,
        metrics: metricsReducer,
        [chatApi.reducerPath]: chatApi.reducer,
    },
    middleware: (getDefaultMiddleware) =>
        getDefaultMiddleware().concat(chatApi.middleware),
    devTools: import.meta.env.MODE !== "production",
});

// ── Exported types ───────────────────────────────────────────────────────────
export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;
