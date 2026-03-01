import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { useEffect } from "react";
import { useAppDispatch } from "@/store/hooks";
import { fetchModelHealth } from "@/store/slices/modelSlice";
import Index from "./pages/Index";
import NotFound from "./pages/NotFound";

// ── Boot component: fetches model health once on startup ──────────────────────
function ModelInitializer() {
  const dispatch = useAppDispatch();
  useEffect(() => {
    dispatch(fetchModelHealth());
    // Re-poll every 60 s to detect backend restart
    const id = setInterval(() => dispatch(fetchModelHealth()), 60_000);
    return () => clearInterval(id);
  }, [dispatch]);
  return null;
}

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: 1, staleTime: 30_000 } },
});

const App = () => (
  <QueryClientProvider client={queryClient}>
    <TooltipProvider>
      <Toaster />
      <Sonner />
      <BrowserRouter>
        <ModelInitializer />
        <Routes>
          <Route path="/" element={<Index />} />
          {/* ADD ALL CUSTOM ROUTES ABOVE THE CATCH-ALL "*" ROUTE */}
          <Route path="*" element={<NotFound />} />
        </Routes>
      </BrowserRouter>
    </TooltipProvider>
  </QueryClientProvider>
);

export default App;
