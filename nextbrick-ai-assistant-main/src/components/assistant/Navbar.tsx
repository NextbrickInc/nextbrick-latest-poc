// ─── components/assistant/Navbar.tsx ─────────────────────────────────────────
// Top sticky navigation bar — Nextbrick brand style
import { ChevronDown, Cpu, Globe, ShoppingCart, User } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useAppSelector } from "@/store/hooks";
import { Badge } from "@/components/ui/badge";

const NAV_ITEMS = ["Products", "Solutions", "Learn", "Buy", "Support"];

const Navbar = () => {
  const modelName = useAppSelector((s) => s.model.name);
  const configured = useAppSelector((s) => s.model.configured);

  return (
    <header className="sticky top-0 z-50 border-b border-border bg-card/95 backdrop-blur">
      <div className="flex h-16 items-center justify-between px-6">
        {/* Brand + nav */}
        <div className="flex items-center gap-6">
          {/* Nextbrick logo wordmark */}
          <span className="flex items-center gap-1.5 select-none">
            <span className="text-xl font-extrabold tracking-tight text-primary leading-none">
              next
            </span>
            <span className="text-xl font-extrabold tracking-tight text-foreground leading-none">
              brick
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

          <Button variant="outline" size="sm" className="rounded-full px-4">
            Contact Us
          </Button>
          <Button variant="ghost" size="icon" className="text-muted-foreground h-8 w-8">
            <Globe className="h-4 w-4" />
          </Button>
          <Button variant="ghost" size="icon" className="text-muted-foreground h-8 w-8">
            <ShoppingCart className="h-4 w-4" />
          </Button>
          <Button variant="ghost" size="icon" className="text-muted-foreground h-8 w-8">
            <User className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </header>
  );
};

export default Navbar;
