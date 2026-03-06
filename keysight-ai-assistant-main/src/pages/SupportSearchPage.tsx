// pages/SupportSearchPage.tsx
// Support portal search — support.keysight.com style
import { useEffect, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import {
  Search, Loader2, FileText, HelpCircle, BookOpen,
  Wrench, LifeBuoy, ExternalLink, ChevronRight,
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
  selectSearchLatency,
} from "@/store/slices/searchSlice";
import Navbar from "@/components/assistant/Navbar";

const TABS = ["Home", "Hardware", "Software", "Product Help", "Other Support Services"];

const CONTENT_ICON: Record<string, React.ElementType> = {
  Manual: BookOpen,
  FAQ: HelpCircle,
  Datasheet: FileText,
  Troubleshooting: Wrench,
  "Knowledge Base": LifeBuoy,
  default: FileText,
};

const QUICK_LINKS = [
  { label: "Contact Support", icon: LifeBuoy, href: "#" },
  { label: "Manuals & Docs", icon: BookOpen, href: "#" },
  { label: "Software Downloads", icon: FileText, href: "#" },
  { label: "Warranty & Repair", icon: Wrench, href: "#" },
];

export default function SupportSearchPage() {
  const dispatch = useAppDispatch();
  const [searchParams, setSearchParams] = useSearchParams();
  const initialQuery = searchParams.get("q") || "";
  const [inputValue, setInputValue] = useState(initialQuery);
  const hasMounted = useRef(false);

  const results = useAppSelector(selectSearchResults);
  const facets = useAppSelector(selectSearchFacets);
  const total = useAppSelector(selectSearchTotal);
  const status = useAppSelector(selectSearchStatus);
  const query = useAppSelector(selectSearchQuery);
  const page = useAppSelector(selectSearchPage);
  const pageSize = useAppSelector(selectSearchPageSize);
  const sortBy = useAppSelector(selectSearchSortBy);
  const activeTab = useAppSelector(selectSearchTab) || "Home";
  const activeFilters = useAppSelector(selectSearchFilters);
  const latencyMs = useAppSelector(selectSearchLatency);

  const isLoading = status === "loading";

  // On mount: clear any stale global search results
  useEffect(() => {
    if (hasMounted.current) return;
    hasMounted.current = true;
    dispatch(clearSearch());
    if (initialQuery) {
      dispatch(executeSearch({
        query: initialQuery,
        pageType: "support",
        filters: {},
        sortBy: "relevance",
        page: 1,
        tab: null,
        includeGeneratedAnswer: false,
      }));
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const doSearch = (q: string, tab?: string) => {
    const newQ = q.trim();
    if (!newQ) return;
    setSearchParams({ q: newQ }, { replace: true });
    dispatch(executeSearch({
      query: newQ,
      pageType: "support",
      filters: activeFilters,
      sortBy,
      page: 1,
      tab: (tab ?? activeTab) === "Home" ? null : (tab ?? activeTab),
      includeGeneratedAnswer: false,
    }));
  };

  const handleTabChange = (tab: string) => {
    dispatch(setTab(tab));
    dispatch(executeSearch({
      query: query || initialQuery,
      pageType: "support",
      filters: activeFilters,
      sortBy,
      page: 1,
      tab: tab === "Home" ? null : tab,
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
      pageType: "support",
      filters: updated,
      sortBy,
      page: 1,
      tab: activeTab === "Home" ? null : activeTab,
      includeGeneratedAnswer: false,
    }));
  };

  const handleSortChange = (s: "relevance" | "date") => {
    dispatch(setSortBy(s));
    dispatch(executeSearch({
      query: query || initialQuery,
      pageType: "support",
      filters: activeFilters,
      sortBy: s,
      page: 1,
      tab: activeTab === "Home" ? null : activeTab,
      includeGeneratedAnswer: false,
    }));
  };

  const handlePaginate = (newPage: number) => {
    dispatch(setPage(newPage));
    dispatch(executeSearch({
      query: query || initialQuery,
      pageType: "support",
      filters: activeFilters,
      sortBy,
      page: newPage,
      tab: activeTab === "Home" ? null : activeTab,
      includeGeneratedAnswer: false,
    }));
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const totalPages = Math.ceil(total / pageSize);

  return (
    <div className="min-h-screen bg-background text-foreground">
      {/* Shared Navbar */}
      <Navbar />

      {/* ── Support hero / search bar ───────────────────────────────────── */}
      <div className="bg-gradient-to-r from-sky-950 to-slate-900 text-white py-8 px-6">
        <div className="mx-auto max-w-4xl">
          <p className="text-sky-400 text-xs font-semibold uppercase tracking-wider mb-1">Keysight Support</p>
          <h1 className="text-2xl font-bold mb-5">How can we help you?</h1>
          <form
            onSubmit={(e) => { e.preventDefault(); doSearch(inputValue); }}
            className="flex items-center rounded-lg overflow-hidden bg-white/10 border border-white/20 h-11 focus-within:ring-2 focus-within:ring-sky-400"
          >
            <span className="pl-4 text-white/60"><Search className="h-4 w-4" /></span>
            <input
              type="text"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              placeholder="Search product name, model number, article..."
              className="flex-1 bg-transparent px-3 text-sm outline-none placeholder:text-white/50 text-white"
              autoFocus
            />
            {inputValue && (
              <button
                type="button"
                onClick={() => { setInputValue(""); dispatch(clearSearch()); }}
                className="px-2 text-white/60 hover:text-white text-lg leading-none"
              >×</button>
            )}
            <button
              type="submit"
              className="h-full px-6 bg-sky-500 hover:bg-sky-400 text-white text-sm font-semibold transition-colors"
            >
              Search
            </button>
          </form>

          {/* Quick links (only when no query) */}
          {!query && !initialQuery && (
            <div className="mt-5 flex flex-wrap gap-2">
              {QUICK_LINKS.map(({ label, icon: Icon, href }) => (
                <a
                  key={label}
                  href={href}
                  className="flex items-center gap-1.5 rounded-full bg-white/10 hover:bg-white/20 border border-white/20 px-3 py-1.5 text-xs font-medium text-white/80 hover:text-white transition-colors"
                >
                  <Icon className="h-3.5 w-3.5" />
                  {label}
                </a>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* ── Tabs (only when search active) ─────────────────────────────── */}
      {(query || initialQuery) && (
        <div className="border-b border-border bg-card">
          <div className="mx-auto max-w-7xl px-6">
            <div className="flex items-center gap-0 overflow-x-auto no-scrollbar">
              {TABS.map((tab) => (
                <button
                  key={tab}
                  onClick={() => handleTabChange(tab)}
                  className={`shrink-0 px-4 py-3 text-sm font-medium border-b-2 transition-colors ${activeTab === tab
                      ? "border-sky-500 text-sky-600 dark:text-sky-400"
                      : "border-transparent text-muted-foreground hover:text-foreground hover:border-border"
                    }`}
                >
                  {tab}
                </button>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* ── Results area ─────────────────────────────────────────────────── */}
      <div className="mx-auto max-w-7xl px-6 py-8 flex gap-8">
        {/* Sidebar */}
        {facets.length > 0 && (
          <aside className="hidden lg:block w-56 shrink-0">
            <div className="sticky top-20 space-y-6">
              <h3 className="text-xs font-bold uppercase tracking-wider text-muted-foreground">Refine by</h3>
              {facets.map((facet) => (
                <div key={facet.name}>
                  <h4 className="mb-1.5 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground/70">
                    {facet.display_name}
                  </h4>
                  <ul className="space-y-1">
                    {facet.values.slice(0, 8).map((v) => (
                      <li key={v.label}>
                        <label className="flex cursor-pointer items-center gap-2 rounded px-1.5 py-1 text-xs hover:bg-accent">
                          <input
                            type="checkbox"
                            checked={v.selected}
                            onChange={() => handleFilterChange(facet.name, v.label)}
                            className="h-3 w-3 accent-sky-500"
                          />
                          <span className="flex-1 text-foreground/80">{v.label}</span>
                          <span className="text-muted-foreground/50">({v.count})</span>
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
          {/* Stats + sort */}
          {query && !isLoading && (
            <div className="mb-4 flex items-center justify-between border-b border-border/40 pb-3 text-xs text-muted-foreground">
              <span>
                <strong className="text-foreground">{total.toLocaleString()}</strong> results
                {latencyMs != null && <span className="ml-2 opacity-60">· {latencyMs}ms</span>}
              </span>
              <div className="flex items-center gap-2">
                Sort:
                {(["relevance", "date"] as const).map((s) => (
                  <button
                    key={s}
                    onClick={() => handleSortChange(s)}
                    className={`capitalize font-semibold transition-colors ${sortBy === s ? "text-sky-500" : "hover:text-foreground"
                      }`}
                  >
                    {s}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Loading */}
          {isLoading && (
            <div className="flex flex-col items-center justify-center py-24 gap-3">
              <Loader2 className="h-8 w-8 animate-spin text-sky-500" />
              <p className="text-sm text-muted-foreground">Searching support articles…</p>
            </div>
          )}

          {/* Results */}
          {!isLoading && results.length > 0 && (
            <div className="space-y-0 divide-y divide-border/40">
              {results.map((r) => {
                const Icon = CONTENT_ICON[r.content_type || ""] || CONTENT_ICON.default;
                return (
                  <div key={r.id} className="group flex gap-4 py-4 hover:bg-accent/10 -mx-2 px-2 rounded-lg transition-colors">
                    <div className="shrink-0 mt-0.5 flex h-8 w-8 items-center justify-center rounded-md bg-sky-500/10">
                      <Icon className="h-4 w-4 text-sky-500" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <a
                        href={r.url || "#"}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex items-center gap-1 text-sm font-semibold text-sky-600 dark:text-sky-400 hover:underline line-clamp-1"
                      >
                        {r.title || "Untitled"}
                        <ExternalLink className="h-3 w-3 shrink-0 opacity-0 group-hover:opacity-60 transition-opacity" />
                      </a>
                      {r.description && (
                        <p className="mt-0.5 text-xs text-foreground/70 line-clamp-2 leading-relaxed max-w-2xl">
                          {r.description}
                        </p>
                      )}
                      <div className="mt-1.5 flex flex-wrap items-center gap-x-3 gap-y-0.5 text-[11px] text-muted-foreground">
                        {r.content_type && (
                          <span className="font-medium text-foreground/60">{r.content_type}</span>
                        )}
                        {r.category && <span>{r.category}</span>}
                        {r.date && <span>{r.date}</span>}
                      </div>
                    </div>
                    <ChevronRight className="h-4 w-4 text-muted-foreground shrink-0 mt-1 opacity-0 group-hover:opacity-60 transition-opacity" />
                  </div>
                );
              })}
            </div>
          )}

          {/* Empty state */}
          {!isLoading && query && results.length === 0 && (
            <div className="text-center py-20">
              <HelpCircle className="h-10 w-10 text-muted-foreground/30 mx-auto mb-4" />
              <h3 className="text-base font-semibold mb-1">No articles found for "{query}"</h3>
              <p className="text-sm text-muted-foreground">Try different keywords or browse categories above.</p>
            </div>
          )}

          {/* Landing state */}
          {!isLoading && !query && !initialQuery && (
            <div className="grid sm:grid-cols-2 gap-4 mt-4">
              {[
                { icon: BookOpen, title: "Product Manuals", desc: "User guides, quick-start and reference manuals." },
                { icon: HelpCircle, title: "FAQs & How-to", desc: "Answers to common questions and how-to articles." },
                { icon: FileText, title: "Datasheets", desc: "Technical specifications and product datasheets." },
                { icon: Wrench, title: "Troubleshooting", desc: "Diagnose and resolve common product issues." },
              ].map(({ icon: Icon, title, desc }) => (
                <button
                  key={title}
                  onClick={() => doSearch(title)}
                  className="text-left flex gap-3 p-4 rounded-xl border border-border hover:border-sky-500/40 hover:bg-sky-500/5 transition-all group"
                >
                  <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-sky-500/10 group-hover:bg-sky-500/20 transition-colors">
                    <Icon className="h-4 w-4 text-sky-500" />
                  </div>
                  <div>
                    <p className="text-sm font-semibold">{title}</p>
                    <p className="text-xs text-muted-foreground mt-0.5">{desc}</p>
                  </div>
                </button>
              ))}
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
                        ? "bg-sky-500 text-white border-sky-500"
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
