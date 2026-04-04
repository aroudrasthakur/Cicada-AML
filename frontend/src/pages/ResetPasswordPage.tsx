import { useEffect, useMemo, useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Hexagon, KeyRound } from "lucide-react";
import { supabase } from "@/api/supabase";
import {
  getPasswordChecks,
  getPasswordStrengthLabel,
  getPasswordStrengthScore,
  mapSupabaseAuthError,
} from "@/utils/auth";
import type { AuthMessage } from "@/types/auth";

export default function ResetPasswordPage() {
  const navigate = useNavigate();
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [recoveryReady, setRecoveryReady] = useState(false);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [message, setMessage] = useState<AuthMessage | null>(null);

  const checks = useMemo(() => getPasswordChecks(password), [password]);
  const score = getPasswordStrengthScore(checks);
  const strengthLabel = getPasswordStrengthLabel(score);

  useEffect(() => {
    let mounted = true;

    const initRecovery = async () => {
      const {
        data: { session },
      } = await supabase.auth.getSession();

      if (!mounted) return;
      setRecoveryReady(Boolean(session));
      setLoading(false);
    };

    void initRecovery();

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((event, session) => {
      if (!mounted) return;

      if (event === "PASSWORD_RECOVERY" || event === "SIGNED_IN") {
        setRecoveryReady(Boolean(session));
        setLoading(false);
      }
    });

    return () => {
      mounted = false;
      subscription.unsubscribe();
    };
  }, []);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setMessage(null);

    if (!recoveryReady) {
      setMessage({
        tone: "error",
        text: "Recovery session is missing. Open the reset link from your email again.",
      });
      return;
    }

    if (password !== confirmPassword) {
      setMessage({ tone: "error", text: "Password and confirm password do not match." });
      return;
    }

    if (score < 5) {
      setMessage({ tone: "error", text: "Use a stronger password that satisfies all requirements." });
      return;
    }

    setSubmitting(true);

    const { error } = await supabase.auth.updateUser({ password });

    if (error) {
      setMessage({ tone: "error", text: mapSupabaseAuthError(error.message) });
      setSubmitting(false);
      return;
    }

    setMessage({ tone: "success", text: "Password updated successfully. Redirecting to sign in..." });
    await supabase.auth.signOut();
    window.setTimeout(() => navigate("/login", { replace: true }), 1200);
  }

  return (
    <div className="min-h-screen bg-[#060810] text-[#e6edf3]">
      <div className="mx-auto flex min-h-screen w-full max-w-[1200px] items-center px-6 py-12">
        <section className="mx-auto w-full max-w-md rounded-2xl border border-[var(--color-aegis-border)] bg-[#0d1117] p-6 sm:p-8">
          <Link
            to="/"
            className="mb-6 inline-flex items-center gap-2 font-display text-lg font-bold tracking-tight text-[#e6edf3]"
          >
            <span className="relative flex h-8 w-8 items-center justify-center rounded-md border border-[#34d399]/35 bg-[#060810]">
              <Hexagon className="h-5 w-5 text-[#34d399]" aria-hidden />
            </span>
            AEGIS AML
          </Link>

          <h1 className="font-display text-2xl font-semibold tracking-tight">Reset password</h1>
          <p className="mt-2 font-data text-sm text-[#9aa7b8]">
            Set a new password for your account. This page is available from your recovery link.
          </p>

          {message && (
            <div
              className={`mt-5 rounded-lg border px-3 py-2 font-data text-[12px] ${
                message.tone === "error"
                  ? "border-[#f87171]/40 bg-[#f87171]/10 text-[#fecaca]"
                  : message.tone === "success"
                    ? "border-[#34d399]/40 bg-[#34d399]/10 text-[#a7f3d0]"
                    : "border-[#7dd3fc]/40 bg-[#0c2535] text-[#bae6fd]"
              }`}
            >
              {message.text}
            </div>
          )}

          {loading ? (
            <div className="mt-6 rounded-lg border border-[var(--color-aegis-border)] bg-[#060810] px-3 py-2 font-data text-sm text-[#9aa7b8]">
              Checking recovery session...
            </div>
          ) : (
            <form className="mt-6 space-y-4" onSubmit={onSubmit}>
              <div>
                <label
                  htmlFor="new-password"
                  className="font-data text-[11px] font-medium uppercase tracking-wide text-[#9aa7b8]"
                >
                  New password
                </label>
                <input
                  id="new-password"
                  type="password"
                  autoComplete="new-password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Enter a strong password"
                  className="mt-1.5 w-full rounded-md border border-[var(--color-aegis-border)] bg-[#060810] px-3 py-2.5 font-mono text-sm text-[#e6edf3] placeholder:text-[#5c6b7e] outline-none focus:border-[#34d399]/45"
                />
              </div>

              <div>
                <label
                  htmlFor="confirm-new-password"
                  className="font-data text-[11px] font-medium uppercase tracking-wide text-[#9aa7b8]"
                >
                  Confirm password
                </label>
                <input
                  id="confirm-new-password"
                  type="password"
                  autoComplete="new-password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  placeholder="Confirm your password"
                  className="mt-1.5 w-full rounded-md border border-[var(--color-aegis-border)] bg-[#060810] px-3 py-2.5 font-mono text-sm text-[#e6edf3] placeholder:text-[#5c6b7e] outline-none focus:border-[#34d399]/45"
                />
              </div>

              <div className="rounded-md border border-[var(--color-aegis-border)] bg-[#060810] p-3">
                <div className="flex items-center justify-between gap-3">
                  <span className="font-data text-[11px] uppercase tracking-wide text-[#9aa7b8]">
                    Password strength
                  </span>
                  <span
                    className={`font-data text-[11px] ${
                      score <= 2 ? "text-[#fca5a5]" : score <= 4 ? "text-[#fcd34d]" : "text-[#86efac]"
                    }`}
                  >
                    {strengthLabel}
                  </span>
                </div>
                <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-[#1a2533]">
                  <div
                    className={`h-full rounded-full transition-all ${
                      score <= 2 ? "bg-[#f87171]" : score <= 4 ? "bg-[#fbbf24]" : "bg-[#34d399]"
                    }`}
                    style={{ width: `${Math.max(10, (score / 5) * 100)}%` }}
                  />
                </div>
                <ul className="mt-3 space-y-1 font-data text-[11px] text-[#9aa7b8]">
                  <li className={checks.minLength ? "text-[#86efac]" : undefined}>At least 12 characters</li>
                  <li className={checks.hasUppercase ? "text-[#86efac]" : undefined}>One uppercase letter</li>
                  <li className={checks.hasLowercase ? "text-[#86efac]" : undefined}>One lowercase letter</li>
                  <li className={checks.hasNumber ? "text-[#86efac]" : undefined}>One number</li>
                  <li className={checks.hasSpecial ? "text-[#86efac]" : undefined}>One special character</li>
                </ul>
              </div>

              <button
                type="submit"
                disabled={submitting || !recoveryReady}
                className="flex w-full items-center justify-center gap-2 rounded-md border border-[#34d399]/35 bg-[#34d399]/10 px-4 py-3 font-data text-sm font-medium text-[#a7f3d0] transition-colors hover:bg-[#34d399]/15 disabled:cursor-not-allowed disabled:opacity-50"
              >
                <KeyRound className="h-4 w-4" aria-hidden />
                {submitting ? "Updating password..." : "Update password"}
              </button>
            </form>
          )}
        </section>
      </div>
    </div>
  );
}
