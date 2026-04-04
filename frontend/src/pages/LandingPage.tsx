import { Link } from "react-router-dom";
import { useState, type ReactNode } from "react";
import { Activity, ArrowRight, Shield } from "lucide-react";
import { useScrollReveal } from "@/hooks/useScrollReveal";
import type { TypologySample } from "@/types/dashboard";

function Reveal({
  children,
  className = "",
  id,
}: {
  children: ReactNode;
  className?: string;
  id?: string;
}) {
  const { ref, revealed } = useScrollReveal<HTMLDivElement>();
  return (
    <div
      ref={ref}
      id={id}
      className={`transition-all duration-700 ease-out ${revealed ? "translate-y-0 opacity-100" : "translate-y-8 opacity-0"} ${className}`}
    >
      {children}
    </div>
  );
}

const PIPELINE_STAGES = [
  "Input",
  "Features",
  "Heuristics",
  "Lenses",
  "Meta-Learner",
  "Output",
] as const;

const LENS_CARDS = [
  { name: "Behavioral", desc: "Economic patterns & autoencoder anomaly.", tag: "XGB + AE" },
  { name: "Graph", desc: "GAT/GCN on wallet graphs.", tag: "PyG" },
  { name: "Entity", desc: "Louvain clusters & cluster risk.", tag: "Community" },
  { name: "Temporal", desc: "LSTM over wallet sequences.", tag: "Sequence" },
  { name: "Off-ramp", desc: "Exit & conversion patterns.", tag: "XGB" },
] as const;

const TICKER_ITEMS = [
  "TX 0x7a3… flagged · T-014 Layering · risk 0.91",
  "Wallet bc1q… · peel chain · CRITICAL",
  "Typology T-042 mixer · 5 lenses active",
  "Recall@50 0.91 · PR-AUC 0.88 · analyst efficiency 3.2×",
  "Heuristic H-203 triggered · confidence 0.94",
];

const CATEGORY_STATS: { category: string; count: number; fraction: number }[] = [
  { category: "Layering & structuring", count: 42, fraction: 0.23 },
  { category: "Mixers & obfuscation", count: 38, fraction: 0.21 },
  { category: "Exchange / off-ramp", count: 35, fraction: 0.19 },
  { category: "P2P & OTC", count: 28, fraction: 0.15 },
  { category: "Other / emerging", count: 42, fraction: 0.22 },
];

const SAMPLES: TypologySample[] = [
  { id: "T-014", label: "Layering via rapid hops", badge: "CRITICAL" },
  { id: "T-042", label: "Mixer aggregation", badge: "HIGH" },
  { id: "T-088", label: "AI-assisted path inference", badge: "AI-ENABLED" },
];

function badgeClass(b: TypologySample["badge"]) {
  if (b === "CRITICAL") return "border-[var(--color-aegis-red)] text-[var(--color-aegis-red)]";
  if (b === "HIGH") return "border-[var(--color-aegis-amber)] text-[var(--color-aegis-amber)]";
  return "border-[var(--color-aegis-purple)] text-[var(--color-aegis-purple)]";
}

export default function LandingPage() {
  const [stage, setStage] = useState<number | null>(2);

  return (
    <div className="min-h-screen bg-[#060810] text-[#e6edf3] aegis-grid">
      <header className="sticky top-0 z-50 border-b border-[var(--color-aegis-border)] bg-[#060810]/92 backdrop-blur-md">
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-6 py-4">
          <Link to="/" className="flex items-center gap-2 font-display text-lg font-bold tracking-tight">
            <Shield className="h-6 w-6 text-[#34d399]/90" aria-hidden />
            Aegis AML
          </Link>
          <nav className="hidden flex-1 items-center justify-center gap-8 md:flex">
            <a href="#pipeline" className="font-data text-sm text-[#9aa7b8] hover:text-[#e6edf3]">
              Pipeline
            </a>
            <a href="#lenses" className="font-data text-sm text-[#9aa7b8] hover:text-[#e6edf3]">
              Lenses
            </a>
            <a href="#typologies" className="font-data text-sm text-[#9aa7b8] hover:text-[#e6edf3]">
              Typologies
            </a>
          </nav>
          <div className="flex items-center gap-2 sm:gap-3">
            <Link
              to="/login"
              className="rounded-lg border border-[var(--color-aegis-border)] bg-transparent px-4 py-2 font-data text-sm text-[#c8d4e0] hover:border-[#34d399]/35 hover:text-[#e6edf3]"
            >
              Sign in
            </Link>
            <Link
              to="/login"
              className="rounded-lg border border-[#34d399]/40 bg-[#34d399]/12 px-4 py-2 font-data text-sm font-medium text-[#6ee7b7] hover:bg-[#34d399]/18"
            >
              Get started
            </Link>
          </div>
        </div>
      </header>

      <section className="relative mx-auto max-w-6xl px-6 pb-16 pt-20">
        <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-[var(--color-aegis-border)] bg-[#0d1117] px-3 py-1.5 font-data text-[11px] text-[#34d399]/95">
          <span className="relative flex h-2 w-2">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-[#34d399]/35" />
            <span className="relative inline-flex h-2 w-2 rounded-full bg-[#34d399]" />
          </span>
          <Activity className="h-3.5 w-3.5" aria-hidden />
          Live scoring · FULL_SCORING
        </div>
        <h1 className="font-display text-5xl font-extrabold leading-tight tracking-tight md:text-6xl">
          Detect. Rank.{" "}
          <span className="text-[#34d399]/95">Investigate.</span>
        </h1>
        <p className="mt-6 max-w-2xl font-data text-base leading-relaxed text-[#9aa7b8]">
          Heuristics-first AML for blockchain flows: five lenses, meta-learner fusion, and
          investigator-ready narratives — without noisy gradients on your surfaces.
        </p>
        <div className="mt-10 flex flex-wrap gap-4">
          <Link
            to="/login"
            className="inline-flex items-center gap-2 rounded-lg border border-[#34d399]/45 bg-[#34d399]/14 px-6 py-3 font-data text-sm font-semibold text-[#6ee7b7] hover:bg-[#34d399]/20"
          >
            Get started
            <ArrowRight className="h-4 w-4" />
          </Link>
          <a
            href="#pipeline"
            className="inline-flex items-center gap-2 rounded-lg border border-[var(--color-aegis-border)] px-6 py-3 font-data text-sm text-[#e6edf3] hover:border-[var(--color-aegis-green)]/40"
          >
            View pipeline
          </a>
        </div>
      </section>

      <div className="border-y border-[var(--color-aegis-border)] bg-[#0d1117]/50 py-3 overflow-hidden">
        <div className="aegis-ticker-track flex w-max gap-12 whitespace-nowrap font-data text-xs text-[#9aa7b8]">
          {[...TICKER_ITEMS, ...TICKER_ITEMS].map((t, i) => (
            <span key={i} className="inline-flex items-center gap-2">
              <span className="text-[var(--color-aegis-green)]">●</span>
              {t}
            </span>
          ))}
        </div>
      </div>

      <Reveal className="mx-auto max-w-6xl px-6 py-16">
        <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
          {[
            { k: "185", l: "Typologies" },
            { k: "5", l: "Models" },
            { k: "0.91", l: "Recall@50" },
            { k: "3.2×", l: "Analyst efficiency" },
          ].map((s) => (
            <div
              key={s.l}
              className="rounded-xl border border-[var(--color-aegis-border)] bg-[#0d1117] p-6 text-center"
            >
              <p className="font-display text-3xl font-bold text-[#34d399]/95">{s.k}</p>
              <p className="mt-1 font-data text-[11px] uppercase tracking-wide text-[var(--color-aegis-muted)]">
                {s.l}
              </p>
            </div>
          ))}
        </div>
      </Reveal>

      <Reveal className="mx-auto max-w-6xl px-6 py-12" id="pipeline">
        <h2 className="font-display text-2xl font-bold text-[#e6edf3]">Heuristics-first pipeline</h2>
        <p className="mt-2 max-w-2xl font-data text-sm text-[#9aa7b8]">
          Click a stage to highlight. Data flows left → right into the meta-learner.
        </p>
        <div className="mt-10 flex flex-wrap items-center justify-center gap-2 md:gap-3">
          {PIPELINE_STAGES.map((label, i) => (
            <div key={label} className="flex items-center gap-2 md:gap-3">
              <button
                type="button"
                onClick={() => setStage(i)}
                className={`rounded-lg border px-4 py-3 font-data text-xs transition-colors md:min-w-[100px] ${
                  stage === i
                    ? "border-[var(--color-aegis-green)] bg-[#00e5a0]/10 text-[var(--color-aegis-green)]"
                    : "border-[var(--color-aegis-border)] bg-[#0d1117] text-[#c8d4e0] hover:border-[var(--color-aegis-green)]/30"
                }`}
              >
                {label}
              </button>
              {i < PIPELINE_STAGES.length - 1 && (
                <span className="font-data text-[var(--color-aegis-muted)]">→</span>
              )}
            </div>
          ))}
        </div>
      </Reveal>

      <Reveal className="mx-auto max-w-6xl px-6 py-12" id="lenses">
        <h2 className="font-display text-2xl font-bold">Five lenses</h2>
        <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {LENS_CARDS.map((c) => (
            <div
              key={c.name}
              className="group relative overflow-hidden rounded-xl border border-[var(--color-aegis-border)] bg-[#0d1117] p-5"
            >
              <div className="absolute bottom-0 left-0 h-0.5 w-0 bg-[var(--color-aegis-green)] transition-all duration-500 group-hover:w-full" />
              <p className="font-data text-[10px] uppercase tracking-wider text-[var(--color-aegis-purple)]">
                {c.tag}
              </p>
              <h3 className="mt-2 font-display text-lg font-semibold text-[#e6edf3]">{c.name}</h3>
              <p className="mt-2 font-data text-sm text-[#9aa7b8]">{c.desc}</p>
            </div>
          ))}
        </div>
      </Reveal>

      <Reveal className="mx-auto max-w-6xl px-6 py-12" id="typologies">
        <h2 className="font-display text-2xl font-bold">Typology coverage</h2>
        <p className="mt-2 font-data text-sm text-[#9aa7b8]">185 typologies — category mix (illustrative).</p>
        <div className="mt-8 space-y-4">
          {CATEGORY_STATS.map((c) => (
            <div key={c.category}>
              <div className="flex justify-between font-data text-xs text-[#9aa7b8]">
                <span>{c.category}</span>
                <span>{c.count}</span>
              </div>
              <div className="mt-1 h-2 overflow-hidden rounded bg-[#060810]">
                <div
                  className="h-full rounded bg-[var(--color-aegis-green)]/70"
                  style={{ width: `${c.fraction * 100}%` }}
                />
              </div>
            </div>
          ))}
        </div>
        <ul className="mt-8 space-y-2">
          {SAMPLES.map((s) => (
            <li
              key={s.id}
              className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-[var(--color-aegis-border)] bg-[#0d1117] px-4 py-3 font-data text-sm"
            >
              <span className="text-[#e6edf3]">
                <span className="text-[var(--color-aegis-muted)]">{s.id}</span> · {s.label}
              </span>
              <span className={`rounded border px-2 py-0.5 text-[10px] font-medium ${badgeClass(s.badge)}`}>
                {s.badge}
              </span>
            </li>
          ))}
        </ul>
      </Reveal>

      <footer className="border-t border-[var(--color-aegis-border)] py-12 text-center">
        <Link
          to="/login"
          className="inline-flex items-center gap-2 rounded-lg border border-[#34d399]/45 bg-[#34d399]/14 px-8 py-3 font-data text-sm font-semibold text-[#6ee7b7] hover:bg-[#34d399]/20"
        >
          Sign in to the platform
          <ArrowRight className="h-4 w-4" />
        </Link>
        <p className="mt-6 font-data text-[11px] text-[var(--color-aegis-muted)]">
          Aegis AML · dark-terminal intelligence
        </p>
      </footer>
    </div>
  );
}
