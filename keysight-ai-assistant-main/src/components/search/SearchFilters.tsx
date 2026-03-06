// components/search/SearchFilters.tsx
// Reusable sidebar filter panel with collapsible facet sections + checkboxes.
import { ChevronDown, ChevronUp, Search } from "lucide-react";
import { useState } from "react";
import type { SearchFacet } from "@/store/slices/searchSlice";

interface SearchFiltersProps {
  facets: SearchFacet[];
  activeFilters: Record<string, string[]>;
  onFilterChange: (facetName: string, value: string) => void;
}

export function SearchFilters({ facets, activeFilters, onFilterChange }: SearchFiltersProps) {
  const [collapsed, setCollapsed] = useState<Record<string, boolean>>({});
  const [filterSearch, setFilterSearch] = useState<Record<string, string>>({});

  const toggle = (name: string) =>
    setCollapsed((prev) => ({ ...prev, [name]: !prev[name] }));

  return (
    <div className="space-y-5">
      <h3 className="text-sm font-semibold text-foreground uppercase tracking-wide">Filters</h3>
      {facets.map((facet) => {
        const isOpen = !collapsed[facet.name];
        const searchTerm = (filterSearch[facet.name] || "").toLowerCase();
        const filteredValues = searchTerm
          ? facet.values.filter((v) => v.label.toLowerCase().includes(searchTerm))
          : facet.values;
        const selected = activeFilters[facet.name] || [];

        return (
          <div key={facet.name} className="border-b border-border pb-3">
            <button
              type="button"
              onClick={() => toggle(facet.name)}
              className="flex w-full items-center justify-between py-1 text-sm font-medium text-foreground hover:text-primary transition-colors"
            >
              <span>{facet.display_name || facet.name}</span>
              {isOpen ? (
                <ChevronUp className="h-4 w-4 text-muted-foreground" />
              ) : (
                <ChevronDown className="h-4 w-4 text-muted-foreground" />
              )}
            </button>

            {isOpen && (
              <div className="mt-2 space-y-1.5">
                {/* Search within facet if many values */}
                {facet.values.length > 6 && (
                  <div className="relative mb-2">
                    <Search className="absolute left-2 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
                    <input
                      type="text"
                      placeholder="Enter Text to Search..."
                      value={filterSearch[facet.name] || ""}
                      onChange={(e) =>
                        setFilterSearch((prev) => ({ ...prev, [facet.name]: e.target.value }))
                      }
                      className="w-full rounded-md border border-input bg-background pl-7 pr-2 py-1.5 text-xs outline-none focus:border-primary"
                    />
                  </div>
                )}

                {filteredValues.map((val) => {
                  const isSelected = selected.includes(val.label);
                  return (
                    <label
                      key={val.label}
                      className="flex items-center gap-2 text-xs text-foreground/80 hover:text-foreground cursor-pointer"
                    >
                      <input
                        type="checkbox"
                        checked={isSelected}
                        onChange={() => onFilterChange(facet.name, val.label)}
                        className="h-3.5 w-3.5 rounded border-border text-primary focus:ring-primary/30"
                      />
                      <span className="flex-1 truncate">{val.label}</span>
                      <span className="text-muted-foreground">({val.count})</span>
                    </label>
                  );
                })}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
