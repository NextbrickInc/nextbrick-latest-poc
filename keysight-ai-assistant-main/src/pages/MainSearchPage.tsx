// pages/MainSearchPage.tsx
// Global product search — keysight.com style
import { useEffect, useRef, useState } from "react";
import { useSearchParams, useNavigate } from "react-router-dom";
import {
    Search, Loader2, Bookmark, Grid3X3, List,
    ArrowRight, Calendar, Tag, FileText, Box,
} from "lucide-react";
import { useAppDispatch, useAppSelector } from "@/store/hooks";
import {
    executeSearch,
    clearSearch,
    toggleFilter,
    setSortBy,
    setTab,
    setPage,
    selectSearchResults,
    selectSearchFacets,
    selectSearchTotal,
    selectSearchStatus,
    selectSearchQuery,
    selectSearchPage,
    selectSearchPageSize,
    selectSearchSortBy,
    selectSearchTab,
    selectSearchFilters,
    selectSearchTabCounts,
    selectSearchLatency,
} from "@/store/slices/searchSlice";
import Navbar from "@/components/assistant/Navbar";

const TABS = ["All", "Products", "Solutions", "Learn", "Software"];

const TYPE_ICON: Record<string, React.ElementType> = {
    Product: Box,
    Manual: FileText,
    Datasheet: FileText,
    Software: Box,
    default: Tag,
};

export default function MainSearchPage() {
    const dispatch = useAppDispatch();
    const navigate = useNavigate();
    const [searchParams, setSearchParams] = useSearchParams();
    const initialQuery = searchParams.get("q") || "";
    const [inputValue, setInputValue] = useState(initialQuery);
    const [viewMode, setViewMode] = useState<"list" | "grid">("list");
    const hasMounted = useRef(false);

    const results = useAppSelector(selectSearchResults);
    const facets = useAppSelector(selectSearchFacets);
    const total = useAppSelector(selectSearchTotal);
    const status = useAppSelector(selectSearchStatus);
    const query = useAppSelector(selectSearchQuery);
    const page = useAppSelector(selectSearchPage);
    const pageSize = useAppSelector(selectSearchPageSize);
    const sortBy = useAppSelector(selectSearchSortBy);
    const activeTab = useAppSelector(selectSearchTab) || "All";
    const activeFilters = useAppSelector(selectSearchFilters);
    const tabCounts = useAppSelector(selectSearchTabCounts);
    const latencyMs = useAppSelector(selectSearchLatency);

    const isLoading = status === "loading";

    // On mount: clear stale results, then search if ?q= present
    useEffect(() => {
        if (hasMounted.current) return;
        hasMounted.current = true;
        dispatch(clearSearch());
        if (initialQuery) {
            dispatch(executeSearch({
                query: initialQuery,
                pageType: "main_site",
                filters: {},
                sortBy: "relevance",
                page: 1,
                tab: null,
                includeGeneratedAnswer: false,
            }));
        }
    }, []); // eslint-disable-line react-hooks/exhaustive-deps

    const doSearch = (q: string, tabFilter?: string | null) => {
        const newQ = q.trim();
        if (!newQ) return;
        setSearchParams({ q: newQ }, { replace: true });
        dispatch(executeSearch({
            query: newQ,
            pageType: "main_site",
            filters: activeFilters,
            sortBy,
            page: 1,
            tab: (tabFilter ?? activeTab) === "All" ? null : (tabFilter ?? activeTab),
            includeGeneratedAnswer: false,
        }));
    };

    const handleFilterChange = (facetName: string, value: string) => {
        dispatch(toggleFilter({ facetName, value }));
        const updated = { ...activeFilters };
        if (!updated[facetName]) updated[facetName] = [];
        const idx = updated[facetName].indexOf(value);
        if (idx >= 0) updated[facetName] = updated[facetName].filter(v => v !== value);
        else updated[facetName] = [...updated[facetName], value];
        dispatch(executeSearch({
            query: query || initialQuery,
            pageType: "main_site",
            filters: updated,
            sortBy,
            page: 1,
            tab: activeTab === "All" ? null : activeTab,
            includeGeneratedAnswer: false,
        }));
    };

    const handleTabChange = (tab: string) => {
        dispatch(setTab(tab));
        dispatch(executeSearch({
            query: query || initialQuery,
            pageType: "main_site",
            filters: activeFilters,
            sortBy,
            page: 1,
            tab: tab === "All" ? null : tab,
            includeGeneratedAnswer: false,
        }));
    };

    const handleSortChange = (s: "relevance" | "date") => {
        dispatch(setSortBy(s));
        dispatch(executeSearch({
            query: query || initialQuery,
            pageType: "main_site",
            filters: activeFilters,
            sortBy: s,
            page: 1,
            tab: activeTab === "All" ? null : activeTab,
            includeGeneratedAnswer: false,
        }));
    };

    const handlePaginate = (newPage: number) => {
        dispatch(setPage(newPage));
        dispatch(executeSearch({
            query: query || initialQuery,
            pageType: "main_site",
            filters: activeFilters,
            sortBy,
            page: newPage,
            tab: activeTab === "All" ? null : activeTab,
            includeGeneratedAnswer: false,
        }));
        window.scrollTo({ top: 0, behavior: "smooth" });
    };

    const totalPages = Math.ceil(total / pageSize);

    return (
        <div className="min-h-screen bg-background text-foreground">
            {/* Shared Navbar */}
            <Navbar />

            {/* ── Search bar strip ─────────────────────────────────────────────── */}
            <div className="border-b border-border bg-card/60 py-5">
                <div className="mx-auto max-w-5xl px-6">
                    <form
                        onSubmit={(e) => { e.preventDefault(); doSearch(inputValue); }}
                        className="flex items-center rounded-md border border-border bg-background shadow-sm overflow-hidden h-12 focus-within:ring-2 focus-within:ring-primary/40"
                    >
                        <span className="pl-4 text-muted-foreground">
                            <Search className="h-4 w-4" />
                        </span>
                        <input
                            type="text"
                            value={inputValue}
                            onChange={(e) => setInputValue(e.target.value)}
                            placeholder="Search products, solutions, documentation..."
                            className="flex-1 bg-transparent px-3 text-sm outline-none placeholder:text-muted-foreground/60"
                            autoFocus
                        />
                        {inputValue && (
                            <button
                                type="button"
                                onClick={() => { setInputValue(""); dispatch(clearSearch()); }}
                                className="px-2 text-muted-foreground hover:text-foreground text-lg leading-none"
                            >×</button>
                        )}
                        <button
                            type="submit"
                            className="h-full px-6 bg-primary hover:bg-primary/90 text-primary-foreground text-sm font-semibold transition-colors"
                        >
                            Search
                        </button>
                    </form>

                    {/* Tabs */}
                    {(query || initialQuery) && (
                        <div className="mt-4 flex items-center gap-1 overflow-x-auto no-scrollbar">
                            {TABS.map((tab) => {
                                const cnt = tab === "All" ? tabCounts["All"] || total : (tabCounts[tab] || 0);
                                return (
                                    <button
                                        key={tab}
                                        onClick={() => handleTabChange(tab)}
                                        className={`shrink-0 rounded-full px-3 py-0.5 text-xs font-medium transition-colors ${activeTab === tab
                                                ? "bg-primary text-primary-foreground"
                                                : "bg-muted text-muted-foreground hover:bg-accent hover:text-foreground"
                                            }`}
                                    >
                                        {tab}
                                        {cnt > 0 && <span className="ml-1 opacity-70">({cnt.toLocaleString()})</span>}
                                    </button>
                                );
                            })}
                        </div>
                    )}
                </div>
            </div>

            {/* ── Results area ─────────────────────────────────────────────────── */}
            <div className="mx-auto max-w-7xl px-6 py-8 flex gap-8">
                {/* Sidebar */}
                {facets.length > 0 && (
                    <aside className="hidden lg:block w-64 shrink-0">
                        <div className="sticky top-20 space-y-6">
                            {facets.map((facet) => (
                                <div key={facet.name}>
                                    <h4 className="mb-2 text-xs font-bold uppercase tracking-wider text-muted-foreground">
                                        {facet.display_name}
                                    </h4>
                                    <ul className="space-y-1">
                                        {facet.values.slice(0, 8).map((v) => (
                                            <li key={v.label}>
                                                <label className="flex cursor-pointer items-center gap-2 rounded-md px-2 py-1 text-xs hover:bg-accent">
                                                    <input
                                                        type="checkbox"
                                                        checked={v.selected}
                                                        onChange={() => handleFilterChange(facet.name, v.label)}
                                                        className="h-3 w-3 accent-primary"
                                                    />
                                                    <span className="flex-1 text-foreground/80">{v.label}</span>
                                                    <span className="text-muted-foreground/60">({v.count})</span>
                                                </label>
                                            </li>
                                        ))}
                                    </ul>
                                </div>
                            ))}
                        </div>
                    </aside>
                )}

                {/* Main */}
                <main className="flex-1 min-w-0">
                    {/* Stats bar */}
                    {query && !isLoading && (
                        <div className="mb-5 flex items-center justify-between text-xs text-muted-foreground border-b border-border/50 pb-3">
                            <span>
                                <strong className="text-foreground">{total.toLocaleString()}</strong> results for{" "}
                                <strong className="text-foreground">"{query}"</strong>
                                {latencyMs != null && <span className="ml-2 opacity-60">· {latencyMs}ms</span>}
                            </span>
                            <div className="flex items-center gap-3">
                                <span>Sort:</span>
                                {(["relevance", "date"] as const).map((s) => (
                                    <button
                                        key={s}
                                        onClick={() => handleSortChange(s)}
                                        className={`font-semibold capitalize transition-colors ${sortBy === s ? "text-primary" : "hover:text-foreground"
                                            }`}
                                    >
                                        {s}
                                    </button>
                                ))}
                                <span className="mx-2 text-border">|</span>
                                <button onClick={() => setViewMode("list")} className={viewMode === "list" ? "text-primary" : "text-muted-foreground"}>
                                    <List className="h-3.5 w-3.5" />
                                </button>
                                <button onClick={() => setViewMode("grid")} className={viewMode === "grid" ? "text-primary" : "text-muted-foreground"}>
                                    <Grid3X3 className="h-3.5 w-3.5" />
                                </button>
                            </div>
                        </div>
                    )}

                    {/* Loading */}
                    {isLoading && (
                        <div className="flex flex-col items-center justify-center py-24 gap-4">
                            <Loader2 className="h-10 w-10 animate-spin text-primary" />
                            <p className="text-sm font-medium text-muted-foreground">Searching Keysight catalog…</p>
                        </div>
                    )}

                    {/* Grid view */}
                    {!isLoading && results.length > 0 && viewMode === "grid" && (
                        <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4">
                            {results.map((r) => {
                                const Icon = TYPE_ICON[r.content_type || ""] || TYPE_ICON.default;
                                return (
                                    <a
                                        key={r.id}
                                        href={r.url || "#"}
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        className="group flex flex-col rounded-xl border border-border bg-card hover:border-primary/40 hover:shadow-md transition-all p-4 gap-2"
                                    >
                                        <div className="flex items-center gap-2">
                                            <span className="flex h-8 w-8 items-center justify-center rounded-md bg-primary/10">
                                                <Icon className="h-4 w-4 text-primary" />
                                            </span>
                                            {r.content_type && (
                                                <span className="text-[10px] font-medium text-muted-foreground uppercase tracking-wide">
                                                    {r.content_type}
                                                </span>
                                            )}
                                        </div>
                                        <p className="text-sm font-semibold text-foreground group-hover:text-primary line-clamp-2 leading-snug">
                                            {r.title || "Untitled"}
                                        </p>
                                        {r.description && (
                                            <p className="text-xs text-muted-foreground line-clamp-2 leading-relaxed">{r.description}</p>
                                        )}
                                        {r.category && (
                                            <span className="mt-auto self-start text-[10px] font-medium bg-primary/10 text-primary rounded-full px-2 py-0.5">
                                                {r.category}
                                            </span>
                                        )}
                                    </a>
                                );
                            })}
                        </div>
                    )}

                    {/* List view */}
                    {!isLoading && results.length > 0 && viewMode === "list" && (
                        <div className="divide-y divide-border/40">
                            {results.map((r) => {
                                const Icon = TYPE_ICON[r.content_type || ""] || TYPE_ICON.default;
                                return (
                                    <div key={r.id} className="group flex gap-4 py-5 hover:bg-accent/20 -mx-2 px-2 rounded-lg transition-colors">
                                        {/* Icon */}
                                        <div className="shrink-0 mt-0.5 flex h-9 w-9 items-center justify-center rounded-lg bg-primary/10">
                                            <Icon className="h-4 w-4 text-primary" />
                                        </div>
                                        <div className="flex-1 min-w-0">
                                            <div className="flex items-start justify-between gap-3">
                                                <a
                                                    href={r.url || "#"}
                                                    target="_blank"
                                                    rel="noopener noreferrer"
                                                    className="text-base font-semibold text-primary hover:underline line-clamp-1"
                                                >
                                                    {r.title || "Untitled"}
                                                </a>
                                                <button className="shrink-0 opacity-0 group-hover:opacity-100 transition-opacity">
                                                    <Bookmark className="h-4 w-4 text-muted-foreground hover:text-foreground" />
                                                </button>
                                            </div>
                                            {r.description && (
                                                <p className="mt-1 text-sm text-foreground/75 line-clamp-2 leading-relaxed max-w-2xl">
                                                    {r.description}
                                                </p>
                                            )}
                                            <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted-foreground">
                                                {r.category && (
                                                    <span className="font-medium bg-primary/10 text-primary rounded-full px-2 py-0.5">
                                                        {r.category}
                                                    </span>
                                                )}
                                                {r.content_type && <span>{r.content_type}</span>}
                                                {r.date && (
                                                    <span className="flex items-center gap-1">
                                                        <Calendar className="h-3 w-3" />{r.date}
                                                    </span>
                                                )}
                                                {r.url && (
                                                    <a
                                                        href={r.url}
                                                        target="_blank"
                                                        rel="noopener noreferrer"
                                                        className="flex items-center gap-0.5 hover:text-foreground hover:underline ml-auto"
                                                    >
                                                        View <ArrowRight className="h-3 w-3" />
                                                    </a>
                                                )}
                                            </div>
                                        </div>
                                    </div>
                                );
                            })}
                        </div>
                    )}

                    {/* Empty state */}
                    {!isLoading && query && results.length === 0 && (
                        <div className="text-center py-20">
                            <Search className="h-10 w-10 text-muted-foreground/30 mx-auto mb-4" />
                            <h3 className="text-lg font-semibold mb-2">No results for "{query}"</h3>
                            <p className="text-sm text-muted-foreground">Try different terms or remove filters.</p>
                        </div>
                    )}

                    {/* Landing state */}
                    {!isLoading && !query && !initialQuery && (
                        <div className="text-center py-20">
                            <Search className="h-10 w-10 text-muted-foreground/30 mx-auto mb-4" />
                            <h3 className="text-lg font-semibold">Search Keysight</h3>
                            <p className="text-sm text-muted-foreground mt-2">Products, documentation, solutions and more.</p>
                        </div>
                    )}

                    {/* Pagination */}
                    {totalPages > 1 && !isLoading && (
                        <div className="flex items-center justify-center gap-2 mt-10 pt-6 border-t border-border/40">
                            <button
                                onClick={() => handlePaginate(page - 1)}
                                disabled={page <= 1}
                                className="px-4 py-1.5 text-sm border border-border rounded-md hover:bg-muted disabled:opacity-40 disabled:cursor-not-allowed"
                            >
                                ← Previous
                            </button>
                            {Array.from({ length: Math.min(totalPages, 5) }).map((_, i) => {
                                const p = page <= 3 ? i + 1 : page - 2 + i;
                                if (p < 1 || p > totalPages) return null;
                                return (
                                    <button
                                        key={p}
                                        onClick={() => handlePaginate(p)}
                                        className={`w-8 h-8 text-sm rounded-md border transition-colors ${p === page
                                                ? "bg-primary text-primary-foreground border-primary"
                                                : "border-border hover:bg-muted"
                                            }`}
                                    >
                                        {p}
                                    </button>
                                );
                            })}
                            <button
                                onClick={() => handlePaginate(page + 1)}
                                disabled={page >= totalPages}
                                className="px-4 py-1.5 text-sm border border-border rounded-md hover:bg-muted disabled:opacity-40 disabled:cursor-not-allowed"
                            >
                                Next →
                            </button>
                        </div>
                    )}
                </main>
            </div>
        </div>
    );
}
