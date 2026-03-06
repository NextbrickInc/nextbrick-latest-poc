// ─── components/assistant/Navbar.tsx ─────────────────────────────────────────
// Top sticky navigation bar — Keysight brand style
import { useEffect, useState } from "react";
import {
  ChevronDown,
  Cpu,
  Globe,
  ShoppingCart,
  User,
  Database,
  Layers,
  BookOpen,
  Cloud,
  FileText,
  Search,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { useAppSelector } from "@/store/hooks";
import { Badge } from "@/components/ui/badge";
import { useNavigate } from "react-router-dom";
import {
  DropdownMenu,
  DropdownMenuTrigger,
  DropdownMenuContent,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuItem,
} from "@/components/ui/dropdown-menu";

const NAV_ITEMS = ["Products", "Solutions", "Learn", "Buy", "Support"];

const Navbar = () => {
  const modelName = useAppSelector((s) => s.model.name);
  const configured = useAppSelector((s) => s.model.configured);
  const navigate = useNavigate();

  const [language, setLanguage] = useState<string>("en");

  useEffect(() => {
    if (typeof window !== "undefined") {
      const stored = window.localStorage.getItem("keysight.language");
      if (stored) setLanguage(stored);
    }
  }, []);

  const languageLabel =
    {
      en: "English",
      de: "German",
      es: "Spanish",
      "zh-Hans": "简体中文",
      "zh-Hant": "繁體中文",
      ja: "日本語",
      ko: "한국어",
      fr: "Français",
    }[language] || "English";

  return (
    <header className="sticky top-0 z-50 border-b border-border bg-card/95 backdrop-blur">
      <div className="flex h-16 items-center justify-between px-6">
        {/* Brand + nav */}
        <div className="flex items-center gap-6">
          {/* Keysight logo wordmark — click to go home with chatbot */}
          <span
            className="flex items-center gap-1.5 select-none cursor-pointer"
            onClick={() => navigate("/")}
          >
            <span className="text-xl font-extrabold tracking-tight text-primary leading-none">
              Keysight
            </span>
            <span className="rounded-full bg-primary/10 px-2 py-0.5 text-[10px] font-semibold text-primary">
              Agentic AI
            </span>
          </span>

          <nav className="hidden items-center gap-0.5 md:flex">
            {NAV_ITEMS.map((item) => (
              <Button
                key={item}
                variant="ghost"
                size="sm"
                onClick={() => {
                  if (item === "Support") navigate("/support/search");
                }}
                className="text-sm text-muted-foreground hover:text-foreground h-8"
              >
                {item}
                <ChevronDown className="ml-1 h-3 w-3 opacity-60" />
              </Button>
            ))}
          </nav>
        </div>

        {/* Model status + actions */}
        <div className="flex items-center gap-3">
          {/* Model indicator */}
          {configured && (
            <Badge
              variant="outline"
              className="hidden gap-1.5 border-primary/30 bg-primary/10 text-primary sm:flex"
            >
              <Cpu className="h-3 w-3" />
              {modelName}
            </Badge>
          )}

          {/* Data source selector */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                variant="outline"
                size="sm"
                className="hidden items-center gap-2 rounded-full px-3.5 py-1 text-xs font-medium md:inline-flex"
              >
                <Database className="h-3.5 w-3.5 text-primary" />
                <span>Data Source</span>
                <ChevronDown className="h-3 w-3 opacity-70" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="min-w-[260px]">
              <DropdownMenuLabel className="text-[11px]">
                Connected data sources
              </DropdownMenuLabel>
              <DropdownMenuSeparator />

              <DropdownMenuItem className="flex items-start gap-2 py-2 text-xs">
                <Cloud className="mt-0.5 h-3.5 w-3.5 text-primary" />
                <div className="flex flex-col">
                  <span className="font-semibold text-foreground">Coveo</span>
                  <span className="text-[11px] text-muted-foreground">
                    Unified relevance platform for enterprise search.
                  </span>
                </div>
              </DropdownMenuItem>

              <DropdownMenuItem className="flex items-start gap-2 py-2 text-xs">
                <Layers className="mt-0.5 h-3.5 w-3.5 text-orange-500" />
                <div className="flex flex-col">
                  <span className="font-semibold text-foreground">AEM DAM</span>
                  <span className="text-[11px] text-muted-foreground">
                    Adobe Experience Manager digital asset management.
                  </span>
                </div>
              </DropdownMenuItem>

              <DropdownMenuItem className="flex items-start gap-2 py-2 text-xs">
                <FileText className="mt-0.5 h-3.5 w-3.5 text-blue-500" />
                <div className="flex flex-col">
                  <span className="font-semibold text-foreground">AEM Pages</span>
                  <span className="text-[11px] text-muted-foreground">
                    Experience Manager sites and documentation pages.
                  </span>
                </div>
              </DropdownMenuItem>

              <DropdownMenuItem className="flex items-start gap-2 py-2 text-xs">
                <BookOpen className="mt-0.5 h-3.5 w-3.5 text-sky-600" />
                <div className="flex flex-col">
                  <span className="font-semibold text-foreground">Confluence</span>
                  <span className="text-[11px] text-muted-foreground">
                    Knowledge base articles and engineering notes.
                  </span>
                </div>
              </DropdownMenuItem>

              <DropdownMenuItem className="flex items-start gap-2 py-2 text-xs">
                <Layers className="mt-0.5 h-3.5 w-3.5 text-indigo-500" />
                <div className="flex flex-col">
                  <span className="font-semibold text-foreground">Salesforce</span>
                  <span className="text-[11px] text-muted-foreground">
                    Cases, emails, KB, service notes, and service orders.
                  </span>
                </div>
              </DropdownMenuItem>

              <DropdownMenuItem className="flex items-start gap-2 py-2 text-xs">
                <Database className="mt-0.5 h-3.5 w-3.5 text-emerald-500" />
                <div className="flex flex-col">
                  <span className="font-semibold text-foreground">PIM</span>
                  <span className="text-[11px] text-muted-foreground">
                    Product information management (specs, hierarchy, pricing).
                  </span>
                </div>
              </DropdownMenuItem>

              <DropdownMenuItem className="flex items-start gap-2 py-2 text-xs">
                <BookOpen className="mt-0.5 h-3.5 w-3.5 text-purple-500" />
                <div className="flex flex-col">
                  <span className="font-semibold text-foreground">Skilljar LMS</span>
                  <span className="text-[11px] text-muted-foreground">
                    Training courses, labs, and certification content.
                  </span>
                </div>
              </DropdownMenuItem>

              <DropdownMenuItem className="flex items-start gap-2 py-2 text-xs">
                <Database className="mt-0.5 h-3.5 w-3.5 text-red-500" />
                <div className="flex flex-col">
                  <span className="font-semibold text-foreground">Oracle</span>
                  <span className="text-[11px] text-muted-foreground">
                    Parts, pricing, and sales order data.
                  </span>
                </div>
              </DropdownMenuItem>

              <DropdownMenuItem className="flex items-start gap-2 py-2 text-xs">
                <SnowflakeIcon />
                <div className="flex flex-col">
                  <span className="font-semibold text-foreground">Snowflake</span>
                  <span className="text-[11px] text-muted-foreground">
                    Enterprise data warehouse and analytics signals.
                  </span>
                </div>
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>

          <Button variant="outline" size="sm" className="rounded-full px-4">
            Contact Us
          </Button>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                variant="ghost"
                size="sm"
                className="text-muted-foreground h-8 px-3 gap-1 rounded-full"
              >
                <Globe className="h-4 w-4" />
                <span className="hidden text-xs sm:inline">{languageLabel}</span>
                <ChevronDown className="h-3 w-3 opacity-60" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="min-w-[180px]">
              <DropdownMenuLabel className="text-[11px]">Language</DropdownMenuLabel>
              <DropdownMenuSeparator />
              {[
                { id: "en", label: "English" },
                { id: "de", label: "German" },
                { id: "es", label: "Spanish" },
                { id: "zh-Hans", label: "Simplified Chinese" },
                { id: "zh-Hant", label: "Traditional Chinese" },
                { id: "ja", label: "Japanese" },
                { id: "ko", label: "Korean" },
                { id: "fr", label: "French" },
              ].map((lang) => (
                <DropdownMenuItem
                  key={lang.id}
                  className="text-[11px]"
                  onClick={() => {
                    setLanguage(lang.id);
                    if (typeof window !== "undefined") {
                      window.localStorage.setItem("keysight.language", lang.id);
                    }
                  }}
                >
                  {lang.label}
                </DropdownMenuItem>
              ))}
            </DropdownMenuContent>
          </DropdownMenu>
          <Button variant="ghost" size="icon" className="text-muted-foreground h-8 w-8">
            <ShoppingCart className="h-4 w-4" />
          </Button>
          <Button variant="ghost" size="icon" className="text-muted-foreground h-8 w-8">
            <User className="h-4 w-4" />
          </Button>
          <Button
            variant="ghost"
            size="icon"
            className="text-muted-foreground h-8 w-8 ml-2"
            onClick={() => navigate('/search')}
          >
            <Search className="h-5 w-5" />
          </Button>
        </div>
      </div>
    </header>
  );
};

const SnowflakeIcon = () => (
  <span className="mt-0.5 inline-flex h-3.5 w-3.5 items-center justify-center rounded-full bg-sky-500/10 text-[10px] text-sky-500">
    ✻
  </span>
);

export default Navbar;
