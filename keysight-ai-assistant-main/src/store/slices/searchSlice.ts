// ─── store/slices/searchSlice.ts ────────────────────────────────────────────
// Redux state for the faceted search pages. Mirrors the backend SearchResponse.
import { createAsyncThunk, createSlice, PayloadAction } from "@reduxjs/toolkit";

// ── Types ────────────────────────────────────────────────────────────────────

export interface SearchResult {
  id: string;
  title: string;
  description: string;
  category: string | null;
  date: string | null;
  url: string | null;
  image_url: string | null;
  content_type: string | null;
  product_area: string | null;
  score: number;
  source_index: string | null;
}

export interface FacetValue {
  label: string;
  count: number;
  selected: boolean;
}

export interface SearchFacet {
  name: string;
  display_name: string;
  values: FacetValue[];
}

export interface SearchState {
  query: string;
  pageType: "support" | "main_site";
  results: SearchResult[];
  facets: SearchFacet[];
  activeFilters: Record<string, string[]>;
  tabCounts: Record<string, number>;
  total: number;
  page: number;
  pageSize: number;
  sortBy: "relevance" | "date";
  tab: string | null;
  status: "idle" | "loading" | "error";
  error: string | null;
  generatedAnswer: string | null;
  latencyMs: number | null;
}

const initialState: SearchState = {
  query: "",
  pageType: "support",
  results: [],
  facets: [],
  activeFilters: {},
  tabCounts: {},
  total: 0,
  page: 1,
  pageSize: 10,
  sortBy: "relevance",
  tab: null,
  status: "idle",
  error: null,
  generatedAnswer: null,
  latencyMs: null,
};

// ── Async thunk ──────────────────────────────────────────────────────────────

interface ExecuteSearchArg {
  query: string;
  pageType: "support" | "main_site";
  filters?: Record<string, string[]>;
  sortBy?: "relevance" | "date";
  page?: number;
  pageSize?: number;
  language?: string;
  tab?: string | null;
  includeGeneratedAnswer?: boolean;
}

interface SearchApiResponse {
  query: string;
  total: number;
  results: SearchResult[];
  facets: SearchFacet[];
  tab_counts: Record<string, number>;
  page: number;
  page_size: number;
  latency_ms: number;
  generated_answer: string | null;
}

export const executeSearch = createAsyncThunk<
  SearchApiResponse,
  ExecuteSearchArg,
  { rejectValue: string }
>("search/executeSearch", async (arg, { rejectWithValue }) => {
  try {
    const res = await fetch("/api/search", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        query: arg.query,
        page_type: arg.pageType,
        filters: arg.filters ?? {},
        sort_by: arg.sortBy ?? "relevance",
        page: arg.page ?? 1,
        page_size: arg.pageSize ?? 10,
        language: arg.language ?? "en",
        tab: arg.tab ?? null,
        include_generated_answer: arg.includeGeneratedAnswer ?? true,
      }),
    });
    if (!res.ok) {
      const detail = await res.text().catch(() => `HTTP ${res.status}`);
      return rejectWithValue(detail);
    }
    return await res.json();
  } catch (e) {
    return rejectWithValue(e instanceof Error ? e.message : "Network error");
  }
});

// ── Slice ────────────────────────────────────────────────────────────────────

const searchSlice = createSlice({
  name: "search",
  initialState,
  reducers: {
    setQuery(state, { payload }: PayloadAction<string>) {
      state.query = payload;
    },
    setPageType(state, { payload }: PayloadAction<"support" | "main_site">) {
      state.pageType = payload;
    },
    setSortBy(state, { payload }: PayloadAction<"relevance" | "date">) {
      state.sortBy = payload;
    },
    setTab(state, { payload }: PayloadAction<string | null>) {
      state.tab = payload;
      state.page = 1;
    },
    setPage(state, { payload }: PayloadAction<number>) {
      state.page = payload;
    },
    toggleFilter(
      state,
      { payload }: PayloadAction<{ facetName: string; value: string }>
    ) {
      const { facetName, value } = payload;
      if (!state.activeFilters[facetName]) {
        state.activeFilters[facetName] = [];
      }
      const idx = state.activeFilters[facetName].indexOf(value);
      if (idx >= 0) {
        state.activeFilters[facetName].splice(idx, 1);
        if (state.activeFilters[facetName].length === 0) {
          delete state.activeFilters[facetName];
        }
      } else {
        state.activeFilters[facetName].push(value);
      }
      state.page = 1;
    },
    clearFilters(state) {
      state.activeFilters = {};
      state.page = 1;
    },
    clearSearch(state) {
      Object.assign(state, initialState);
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(executeSearch.pending, (state, { meta }) => {
        state.status = "loading";
        state.error = null;
        state.query = meta.arg.query;
        state.pageType = meta.arg.pageType;
        if (meta.arg.sortBy) state.sortBy = meta.arg.sortBy;
        if (meta.arg.page) state.page = meta.arg.page;
        if (meta.arg.tab !== undefined) state.tab = meta.arg.tab;
      })
      .addCase(executeSearch.fulfilled, (state, { payload }) => {
        state.status = "idle";
        state.results = payload.results;
        state.facets = payload.facets;
        state.tabCounts = payload.tab_counts ?? {};
        state.total = payload.total;
        state.page = payload.page;
        state.pageSize = payload.page_size;
        state.latencyMs = payload.latency_ms;
        state.generatedAnswer = payload.generated_answer;
      })
      .addCase(executeSearch.rejected, (state, { payload }) => {
        state.status = "error";
        state.error = payload ?? "Search failed";
      });
  },
});

export const {
  setQuery,
  setPageType,
  setSortBy,
  setTab,
  setPage,
  toggleFilter,
  clearFilters,
  clearSearch,
} = searchSlice.actions;

export const searchReducer = searchSlice.reducer;

// ── Selectors ────────────────────────────────────────────────────────────────
import type { RootState } from "../index";

export const selectSearchResults = (state: RootState) => state.search.results;
export const selectSearchFacets = (state: RootState) => state.search.facets;
export const selectSearchTotal = (state: RootState) => state.search.total;
export const selectSearchStatus = (state: RootState) => state.search.status;
export const selectSearchQuery = (state: RootState) => state.search.query;
export const selectSearchPage = (state: RootState) => state.search.page;
export const selectSearchPageSize = (state: RootState) => state.search.pageSize;
export const selectSearchSortBy = (state: RootState) => state.search.sortBy;
export const selectSearchTab = (state: RootState) => state.search.tab;
export const selectSearchFilters = (state: RootState) => state.search.activeFilters;
export const selectSearchTabCounts = (state: RootState) => state.search.tabCounts;
export const selectGeneratedAnswer = (state: RootState) => state.search.generatedAnswer;
export const selectSearchLatency = (state: RootState) => state.search.latencyMs;
