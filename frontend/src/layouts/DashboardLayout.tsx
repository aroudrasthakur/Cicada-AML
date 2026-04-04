import { useMemo, useState } from "react";
import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import type { LucideIcon } from "lucide-react";
import {
  LayoutDashboard,
  ArrowLeftRight,
  Wallet,
  Network,
  GitBranch,
  FileText,
  Bell,
  Upload,
  Play,
  FileWarning,
  Hexagon,
  LogOut,
} from "lucide-react";
import { ScoringModeProvider, useScoringMode } from "@/contexts/ScoringModeContext";
import { useAuth } from "@/contexts/AuthContext";
import ScoringModeBanner from "@/components/ScoringModeBanner";

const NAV_MAIN: {
  to: string;
  label: string;
  icon: LucideIcon;
  badge: string | null;
}[] = [
  { to: "/dashboard", label: "Dashboard", icon: LayoutDashboard, badge: "3" },
  { to: "/dashboard/transactions", label: "Transactions", icon: ArrowLeftRight, badge: "1.2k" },
  { to: "/dashboard/wallets", label: "Wallets", icon: Wallet, badge: null },
  { to: "/dashboard/networks", label: "Network Cases", icon: Network, badge: "7" },
];

const NAV_ANALYSIS: {
  to: string;
  label: string;
  icon: LucideIcon;
  badge: string | null;
}[] = [
  { to: "/dashboard/explorer", label: "Flow Explorer", icon: GitBranch, badge: null },
  { to: "/dashboard/reports", label: "Reports", icon: FileText, badge: null },
];

function pageTitleForPath(pathname: string): string {
  if (pathname === "/dashboard" || pathname === "/dashboard/") return "Dashboard";
  if (pathname.startsWith("/dashboard/transactions")) return "Transactions";
  if (pathname.startsWith("/dashboard/wallets")) return "Wallets";
  if (pathname.startsWith("/dashboard/networks")) return "Network cases";
  if (pathname.startsWith("/dashboard/explorer")) return "Flow explorer";
  if (pathname.startsWith("/dashboard/reports")) return "Reports";
  return "Operations";
}

function NavBlock({
  title,
  items,
}: {
  title: string;
  items: { to: string; label: string; icon: LucideIcon; badge: string | null }[];
}) {
  return (
    <div className="mt-5 px-2">
      <p className="px-3 font-mono text-[10px] font-medium uppercase tracking-[0.18em] text-[#5c6b7e]">
        {title}
      </p>
      <div className="mt-1.5 flex flex-col gap-0.5">
        {items.map(({ to, label, icon: Icon, badge }) => (
          <NavLink
            key={to}
            to={to}
            end={to === "/dashboard"}
            className={({ isActive }) =>
              `flex items-center justify-between gap-2 rounded-lg px-3 py-2.5 font-data text-[13px] transition-colors ${
                isActive
                  ? "bg-[#060810] text-[#34d399]"
                  : "text-[#9aa7b8] hover:bg-[#060810]/80 hover:text-[#e6edf3]"
              }`
            }
          >
            <span className="flex items-center gap-2.5">
              <Icon className="h-4 w-4 shrink-0 opacity-80" aria-hidden />
              {label}
            </span>
            {badge != null && (
              <span className="rounded bg-[#060810] px-1.5 py-0.5 font-mono text-[10px] text-[#7d8a99]">
                {badge}
              </span>
            )}
          </NavLink>
        ))}
      </div>
    </div>
  );
}

function DashboardShell() {
  const [notif] = useState(4);
  const [logoutOpen, setLogoutOpen] = useState(false);
  const [isLoggingOut, setIsLoggingOut] = useState(false);
  const { mode } = useScoringMode();
  const { profile, user, signOut } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const pageTitle = useMemo(
    () => pageTitleForPath(location.pathname),
    [location.pathname],
  );
  const isDashboardHome =
    location.pathname === "/dashboard" || location.pathname === "/dashboard/";
  const overviewDate = new Date().toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
  const displayName = useMemo(() => {
    if (profile) {
      return `${profile.first_name} ${profile.last_name}`.trim();
    }
    const metadataName = [user?.user_metadata?.first_name, user?.user_metadata?.last_name]
      .filter(Boolean)
      .join(" ")
      .trim();
    if (metadataName) return metadataName;
    return user?.email ?? "Authenticated User";
  }, [profile, user]);
  const displaySecondary = useMemo(() => {
    if (profile?.username) return `@${profile.username}`;
    return user?.email ?? "Analyst";
  }, [profile, user]);
  const initials = useMemo(() => {
    const source = displayName.split(" ").filter(Boolean);
    if (source.length >= 2) {
      return `${source[0][0]}${source[1][0]}`.toUpperCase();
    }
    if (source.length === 1) {
      return source[0].slice(0, 2).toUpperCase();
    }
    return "AU";
  }, [displayName]);

  return (
    <div className="flex min-h-screen bg-[#060810] text-[#e6edf3]">
      {logoutOpen && (
        <div
          className="fixed inset-0 z-[100] flex items-center justify-center bg-black/55 px-4 backdrop-blur-[2px]"
          role="presentation"
          onClick={() => setLogoutOpen(false)}
        >
          <div
            role="dialog"
            onClick={(e) => e.stopPropagation()}
            aria-modal="true"
            aria-labelledby="logout-title"
            className="w-full max-w-sm rounded-xl border border-[var(--color-aegis-border)] bg-[#0d1117] p-6 shadow-xl"
          >
            <h2 id="logout-title" className="font-display text-lg font-semibold text-[#e6edf3]">
              Sign out?
            </h2>
            <p className="mt-2 font-data text-sm text-[#9aa7b8]">
              You will need to sign in again to access the risk queue and case workspace.
            </p>
            <div className="mt-6 flex flex-wrap justify-end gap-2">
              <button
                type="button"
                onClick={() => setLogoutOpen(false)}
                className="rounded-lg border border-[var(--color-aegis-border)] bg-[#060810] px-4 py-2 font-data text-sm text-[#e6edf3] hover:border-[#34d399]/35"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={async () => {
                  if (isLoggingOut) return;
                  setIsLoggingOut(true);
                  const { error } = await signOut();
                  setIsLoggingOut(false);
                  setLogoutOpen(false);
                  navigate("/login", { replace: true });
                  if (error) {
                    console.error("Sign out failed:", error);
                  }
                }}
                className="rounded-lg border border-[#f87171]/40 bg-[#f87171]/10 px-4 py-2 font-data text-sm font-medium text-[#fca5a5] hover:bg-[#f87171]/15"
              >
                {isLoggingOut ? "Signing out..." : "Sign out"}
              </button>
            </div>
          </div>
        </div>
      )}

      <aside className="fixed left-0 top-0 z-40 flex h-screen w-[240px] flex-col border-r border-[var(--color-aegis-border)] bg-[#0d1117]">
        <div className="border-b border-[var(--color-aegis-border)] px-4 py-5">
          <div className="flex items-center gap-2">
            <span className="flex h-8 w-8 items-center justify-center rounded-md border border-[#34d399]/30 bg-[#060810]">
              <Hexagon className="h-5 w-5 text-[#34d399]" aria-hidden />
            </span>
            <div>
              <div className="font-display text-sm font-bold tracking-tight text-[#e6edf3]">
                AEGIS AML
              </div>
              <p className="font-mono text-[10px] uppercase tracking-wider text-[#6b7c90]">
                Intelligence
              </p>
            </div>
          </div>
        </div>

        <div className="mx-3 mt-4 flex items-center gap-3 rounded-lg border border-[var(--color-aegis-border)] bg-[#060810] p-3">
          <div
            className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-[#34d399]/15 font-display text-sm font-semibold text-[#6ee7b7]"
            aria-hidden
          >
            {initials}
          </div>
          <div className="min-w-0">
            <p className="truncate font-data text-sm font-medium text-[#e6edf3]">{displayName}</p>
            <p className="truncate font-mono text-[10px] text-[#7d8a99]">{displaySecondary}</p>
          </div>
        </div>

        <nav className="mt-1 flex flex-1 flex-col overflow-y-auto pb-2">
          <NavBlock title="Main" items={NAV_MAIN} />
          <NavBlock title="Analysis" items={NAV_ANALYSIS} />
        </nav>

        <div className="border-t border-[var(--color-aegis-border)] p-3">
          <div className="flex items-center gap-2 rounded-lg border border-[var(--color-aegis-border)]/80 bg-[#060810] px-3 py-2">
            <span className="relative flex h-2 w-2">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-[#34d399]/35" />
              <span className="relative inline-flex h-2 w-2 rounded-full bg-[#34d399]" />
            </span>
            <span className="font-mono text-[10px] font-medium uppercase tracking-wide text-[#9aa7b8]">
              {mode}
            </span>
          </div>
          <button
            type="button"
            onClick={() => setLogoutOpen(true)}
            className="mt-2 flex w-full items-center justify-center gap-2 rounded-lg border border-[var(--color-aegis-border)] bg-transparent px-3 py-2 font-data text-[13px] text-[#9aa7b8] transition-colors hover:border-[#f87171]/35 hover:text-[#fca5a5]"
          >
            <LogOut className="h-4 w-4" aria-hidden />
            Log out
          </button>
        </div>
      </aside>

      <div className="ml-[240px] flex min-h-screen flex-1 flex-col">
        <header className="sticky top-0 z-30 flex flex-wrap items-center justify-between gap-4 border-b border-[var(--color-aegis-border)] bg-[#060810]/95 px-6 py-4 backdrop-blur-sm">
          <div>
            <h1 className="font-display text-lg font-semibold text-[#e6edf3]">{pageTitle}</h1>
            <p className="font-data text-[11px] text-[var(--color-aegis-muted)]">
              {isDashboardHome ? (
                <>
                  Overview · <span className="tabular-nums text-[#c8d4e0]">{overviewDate}</span>
                </>
              ) : (
                <>
                  Last updated{" "}
                  <span className="tabular-nums text-[#c8d4e0]">
                    {new Date().toLocaleString()}
                  </span>
                </>
              )}
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <button
              type="button"
              className="inline-flex items-center gap-2 rounded-lg border border-[var(--color-aegis-border)] bg-[#0d1117] px-3 py-2 font-data text-xs text-[#e6edf3] hover:border-[#34d399]/35"
            >
              <Upload className="h-4 w-4" aria-hidden />
              Upload CSV
            </button>
            <button
              type="button"
              className="inline-flex items-center gap-2 rounded-lg border border-[var(--color-aegis-border)] bg-[#0d1117] px-3 py-2 font-data text-xs text-[#e6edf3] hover:border-[#34d399]/35"
            >
              <Play className="h-4 w-4" aria-hidden />
              Run Pipeline
            </button>
            <button
              type="button"
              className="inline-flex items-center gap-2 rounded-lg border border-[#34d399]/35 bg-[#34d399]/10 px-3 py-2 font-data text-xs text-[#6ee7b7]"
            >
              <FileWarning className="h-4 w-4" aria-hidden />
              Generate SAR
            </button>
            <button
              type="button"
              className="relative rounded-lg border border-[var(--color-aegis-border)] p-2 text-[#9aa7b8] hover:text-[#e6edf3]"
              aria-label="Notifications"
            >
              <Bell className="h-5 w-5" />
              {notif > 0 && (
                <span className="absolute -right-0.5 -top-0.5 flex h-4 min-w-[16px] items-center justify-center rounded-full bg-[#f87171] px-1 font-data text-[10px] text-white">
                  {notif}
                </span>
              )}
            </button>
          </div>
        </header>

        {isDashboardHome && <ScoringModeBanner variant="strip" />}

        <main className="flex-1 px-6 py-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}

export default function DashboardLayout() {
  return (
    <ScoringModeProvider>
      <DashboardShell />
    </ScoringModeProvider>
  );
}
