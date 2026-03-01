import { Badge } from "@/components/ui/badge";

const HeroSection = () => (
  <section className="relative overflow-hidden bg-gradient-to-br from-primary via-primary/90 to-primary/70 px-6 py-16 text-primary-foreground md:py-20">
    <div className="absolute inset-0 bg-[radial-gradient(circle_at_30%_50%,hsl(199_89%_60%/0.3),transparent_60%)]" />
    <div className="relative mx-auto max-w-6xl text-center">
      <Badge className="mb-4 border-primary-foreground/20 bg-primary-foreground/10 text-primary-foreground hover:bg-primary-foreground/20">
        Enterprise AI POC
      </Badge>
      <h1 className="mb-3 text-4xl font-extrabold tracking-tight md:text-5xl lg:text-6xl">
        Recommendation: Nextbrick Solution
      </h1>
      <p className="mx-auto max-w-2xl text-lg text-primary-foreground/80">
        Agentic AI platform for intelligent document search, multi-turn conversations, and enterprise tool orchestration across on-prem and cloud environments.
      </p>
    </div>
  </section>
);

export default HeroSection;
