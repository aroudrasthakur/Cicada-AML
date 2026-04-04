import { useEffect, useMemo, useState, type FormEvent } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { Hexagon, LogIn, MailCheck, RefreshCcw, Shield, UserRoundPlus } from "lucide-react";
import { supabase } from "@/api/supabase";
import { checkEmailInUse, checkUsernameAvailability, resolveLoginEmail } from "@/api/auth";
import {
  getPasswordChecks,
  getPasswordStrengthLabel,
  getPasswordStrengthScore,
  isValidEmail,
  isValidUsername,
  mapSupabaseAuthError,
  sanitizeUsername,
} from "@/utils/auth";
import type { AuthMessage } from "@/types/auth";

type Mode = "signin" | "signup" | "forgot" | "otp";
type FieldState = "idle" | "checking" | "valid" | "invalid";

function alertClass(tone: AuthMessage["tone"]) {
  if (tone === "error") return "border-[#f87171]/40 bg-[#f87171]/10 text-[#fecaca]";
  if (tone === "success") return "border-[#34d399]/40 bg-[#34d399]/10 text-[#a7f3d0]";
  return "border-[#7dd3fc]/40 bg-[#0c2535] text-[#bae6fd]";
}

function helperClass(state: FieldState) {
  if (state === "valid") return "text-[#86efac]";
  if (state === "invalid") return "text-[#fca5a5]";
  if (state === "checking") return "text-[#93c5fd]";
  return "text-[#6b7c90]";
}

export default function AuthPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const [mode, setMode] = useState<Mode>("signin");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [msg, setMsg] = useState<AuthMessage | null>(null);

  const [loginIdentifier, setLoginIdentifier] = useState("");
  const [loginPassword, setLoginPassword] = useState("");
  const [forgotEmail, setForgotEmail] = useState("");
  const [otpEmail, setOtpEmail] = useState("");
  const [otpCode, setOtpCode] = useState("");

  const [username, setUsername] = useState("");
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [signupEmail, setSignupEmail] = useState("");
  const [signupPassword, setSignupPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");

  const [usernameState, setUsernameState] = useState<FieldState>("idle");
  const [usernameText, setUsernameText] = useState("3-30 chars: a-z 0-9 . _ -");
  const [emailState, setEmailState] = useState<FieldState>("idle");
  const [emailText, setEmailText] = useState("We will verify this email with OTP.");

  const passwordChecks = useMemo(() => getPasswordChecks(signupPassword), [signupPassword]);
  const passwordScore = getPasswordStrengthScore(passwordChecks);
  const strengthLabel = getPasswordStrengthLabel(passwordScore);

  useEffect(() => {
    const params = new URLSearchParams(location.search);
    if (params.get("verified") === "1") {
      setMode("signin");
      setMsg({ tone: "success", text: "Email verification completed. Sign in to continue." });
    }
  }, [location.search]);

  useEffect(() => {
    if (mode !== "signup") return;
    const next = sanitizeUsername(username);
    if (!next) {
      setUsernameState("idle");
      setUsernameText("3-30 chars: a-z 0-9 . _ -");
      return;
    }
    if (!isValidUsername(next)) {
      setUsernameState("invalid");
      setUsernameText("Invalid format.");
      return;
    }
    setUsernameState("checking");
    setUsernameText("Checking username...");
    const id = window.setTimeout(() => {
      checkUsernameAvailability(next)
        .then((ok) => {
          setUsernameState(ok ? "valid" : "invalid");
          setUsernameText(ok ? "Username available." : "Username already taken.");
        })
        .catch(() => {
          setUsernameState("invalid");
          setUsernameText("Could not validate username.");
        });
    }, 400);
    return () => window.clearTimeout(id);
  }, [mode, username]);

  useEffect(() => {
    if (mode !== "signup") return;
    const next = signupEmail.trim().toLowerCase();
    if (!next) {
      setEmailState("idle");
      setEmailText("We will verify this email with OTP.");
      return;
    }
    if (!isValidEmail(next)) {
      setEmailState("invalid");
      setEmailText("Invalid email format.");
      return;
    }
    setEmailState("checking");
    setEmailText("Checking email...");
    const id = window.setTimeout(() => {
      checkEmailInUse(next)
        .then((inUse) => {
          setEmailState(inUse ? "invalid" : "valid");
          setEmailText(inUse ? "Email already in use." : "Email available.");
        })
        .catch(() => {
          setEmailState("invalid");
          setEmailText("Could not validate email.");
        });
    }, 400);
    return () => window.clearTimeout(id);
  }, [mode, signupEmail]);

  async function onSignIn(e: FormEvent) {
    e.preventDefault();
    setMsg(null);
    if (!loginIdentifier.trim() || !loginPassword) {
      setMsg({ tone: "error", text: "Enter username/email and password." });
      return;
    }
    setIsSubmitting(true);
    try {
      let email = loginIdentifier.trim().toLowerCase();
      if (!email.includes("@")) {
        const resolved = await resolveLoginEmail(email);
        if (!resolved) {
          setMsg({ tone: "error", text: "Username not found." });
          setIsSubmitting(false);
          return;
        }
        email = resolved;
      }
      const { error } = await supabase.auth.signInWithPassword({ email, password: loginPassword });
      if (error) {
        setMsg({ tone: "error", text: mapSupabaseAuthError(error.message) });
        setIsSubmitting(false);
        return;
      }
      setMsg({ tone: "success", text: "Sign in successful. Redirecting..." });
      window.setTimeout(() => navigate("/dashboard", { replace: true }), 650);
    } catch {
      setMsg({ tone: "error", text: "Unable to sign in right now." });
      setIsSubmitting(false);
    }
  }

  async function onSignUp(e: FormEvent) {
    e.preventDefault();
    setMsg(null);
    const u = sanitizeUsername(username);
    const eaddr = signupEmail.trim().toLowerCase();
    if (!u || !firstName.trim() || !lastName.trim() || !eaddr || !signupPassword || !confirmPassword) {
      setMsg({ tone: "error", text: "Complete all sign-up fields." });
      return;
    }
    if (!isValidUsername(u)) return setMsg({ tone: "error", text: "Invalid username format." });
    if (!isValidEmail(eaddr)) return setMsg({ tone: "error", text: "Invalid email format." });
    if (signupPassword !== confirmPassword) return setMsg({ tone: "error", text: "Passwords do not match." });
    if (passwordScore < 5) return setMsg({ tone: "error", text: "Password strength requirements are not met." });

    setIsSubmitting(true);
    try {
      const [available, inUse] = await Promise.all([checkUsernameAvailability(u), checkEmailInUse(eaddr)]);
      if (!available) {
        setMsg({ tone: "error", text: "Username is already taken." });
        setIsSubmitting(false);
        return;
      }
      if (inUse) {
        setMsg({ tone: "error", text: "Email is already in use." });
        setIsSubmitting(false);
        return;
      }
      const { error } = await supabase.auth.signUp({
        email: eaddr,
        password: signupPassword,
        options: {
          data: { username: u, first_name: firstName.trim(), last_name: lastName.trim() },
        },
      });
      if (error) {
        setMsg({ tone: "error", text: mapSupabaseAuthError(error.message) });
        setIsSubmitting(false);
        return;
      }
      setOtpEmail(eaddr);
      setOtpCode("");
      setMode("otp");
      setMsg({ tone: "success", text: "Sign up successful. OTP sent to your email." });
      setIsSubmitting(false);
    } catch {
      setMsg({ tone: "error", text: "Unable to complete sign up." });
      setIsSubmitting(false);
    }
  }

  async function onForgot(e: FormEvent) {
    e.preventDefault();
    setMsg(null);
    const email = forgotEmail.trim().toLowerCase();
    if (!isValidEmail(email)) return setMsg({ tone: "error", text: "Enter a valid email." });
    setIsSubmitting(true);
    const { error } = await supabase.auth.resetPasswordForEmail(email, {
      redirectTo: `${window.location.origin}/reset-password`,
    });
    if (error) {
      setMsg({ tone: "error", text: mapSupabaseAuthError(error.message) });
      setIsSubmitting(false);
      return;
    }
    setMsg({ tone: "info", text: "Reset link sent. Check your inbox." });
    setIsSubmitting(false);
  }

  async function onVerifyOtp(e: FormEvent) {
    e.preventDefault();
    setMsg(null);
    const email = otpEmail.trim().toLowerCase();
    if (!isValidEmail(email) || !otpCode.trim()) {
      setMsg({ tone: "error", text: "Enter email and OTP code." });
      return;
    }
    setIsSubmitting(true);
    const { error } = await supabase.auth.verifyOtp({ email, token: otpCode.trim(), type: "signup" });
    if (error) {
      setMsg({ tone: "error", text: mapSupabaseAuthError(error.message) });
      setIsSubmitting(false);
      return;
    }
    setMsg({ tone: "success", text: "OTP verified. Redirecting..." });
    window.setTimeout(() => navigate("/dashboard", { replace: true }), 650);
  }

  async function resendOtp() {
    setMsg(null);
    const email = otpEmail.trim().toLowerCase();
    if (!isValidEmail(email)) return setMsg({ tone: "error", text: "Enter a valid email." });
    setIsSubmitting(true);
    const { error } = await supabase.auth.resend({
      type: "signup",
      email,
    });
    if (error) {
      setMsg({ tone: "error", text: mapSupabaseAuthError(error.message) });
      setIsSubmitting(false);
      return;
    }
    setMsg({ tone: "info", text: "A fresh OTP has been sent." });
    setIsSubmitting(false);
  }

  return (
    <div className="min-h-screen bg-[#060810] text-[#e6edf3]">
      <div className="mx-auto flex min-h-screen max-w-[1100px] flex-col lg:flex-row">
        <section className="flex flex-1 flex-col justify-center px-8 py-12 lg:max-w-[56%]">
          <Link to="/" className="mb-8 inline-flex items-center gap-2 font-display text-lg font-bold tracking-tight">
            <span className="flex h-8 w-8 items-center justify-center rounded-md border border-[#34d399]/35 bg-[#0d1117]">
              <Hexagon className="h-5 w-5 text-[#34d399]" aria-hidden />
            </span>
            AEGIS AML
          </Link>
          <h1 className="font-display text-3xl font-bold tracking-tight">Secure Access</h1>
          <p className="mt-2 max-w-md font-data text-sm text-[#9aa7b8]">Sign in, create an account, verify OTP, or recover your password.</p>

          <div className="mt-6 flex max-w-md rounded-lg border border-[var(--color-aegis-border)] bg-[#0d1117] p-1">
            {(["signin", "signup", "forgot"] as const).map((tab) => (
              <button
                key={tab}
                type="button"
                onClick={() => { setMode(tab); setMsg(null); }}
                className={`flex-1 rounded-md px-3 py-2 font-data text-xs ${mode === tab ? "bg-[#060810] text-[#34d399]" : "text-[#9aa7b8]"}`}
              >
                {tab === "signin" ? "Sign in" : tab === "signup" ? "Sign up" : "Forgot"}
              </button>
            ))}
          </div>

          {msg && <div className={`mt-4 max-w-md rounded-lg border px-3 py-2 font-data text-[12px] ${alertClass(msg.tone)}`}>{msg.text}</div>}

          {mode === "signin" && (
            <form className="mt-6 max-w-md space-y-4" onSubmit={onSignIn}>
              <input value={loginIdentifier} onChange={(e) => setLoginIdentifier(e.target.value)} placeholder="Username or email" className="w-full rounded-md border border-[var(--color-aegis-border)] bg-[#0d1117] px-3 py-2.5 font-mono text-sm outline-none focus:border-[#34d399]/45" />
              <input type="password" value={loginPassword} onChange={(e) => setLoginPassword(e.target.value)} placeholder="Password" className="w-full rounded-md border border-[var(--color-aegis-border)] bg-[#0d1117] px-3 py-2.5 font-mono text-sm outline-none focus:border-[#34d399]/45" />
              <button type="submit" disabled={isSubmitting} className="flex w-full items-center justify-center gap-2 rounded-md border border-[#3d4a5c] bg-[#0d1117] px-4 py-3 font-data text-sm disabled:opacity-60"><LogIn className="h-4 w-4 text-[#34d399]" />{isSubmitting ? "Signing in..." : "Sign in"}</button>
            </form>
          )}

          {mode === "signup" && (
            <form className="mt-6 max-w-md space-y-3" onSubmit={onSignUp}>
              <input value={username} onChange={(e) => setUsername(e.target.value)} placeholder="Username" className="w-full rounded-md border border-[var(--color-aegis-border)] bg-[#0d1117] px-3 py-2.5 font-mono text-sm outline-none focus:border-[#34d399]/45" />
              <p className={`font-data text-[11px] ${helperClass(usernameState)}`}>{usernameText}</p>
              <div className="grid grid-cols-2 gap-3">
                <input value={firstName} onChange={(e) => setFirstName(e.target.value)} placeholder="First name" className="w-full rounded-md border border-[var(--color-aegis-border)] bg-[#0d1117] px-3 py-2.5 font-mono text-sm outline-none focus:border-[#34d399]/45" />
                <input value={lastName} onChange={(e) => setLastName(e.target.value)} placeholder="Last name" className="w-full rounded-md border border-[var(--color-aegis-border)] bg-[#0d1117] px-3 py-2.5 font-mono text-sm outline-none focus:border-[#34d399]/45" />
              </div>
              <input type="email" value={signupEmail} onChange={(e) => setSignupEmail(e.target.value)} placeholder="Email" className="w-full rounded-md border border-[var(--color-aegis-border)] bg-[#0d1117] px-3 py-2.5 font-mono text-sm outline-none focus:border-[#34d399]/45" />
              <p className={`font-data text-[11px] ${helperClass(emailState)}`}>{emailText}</p>
              <input type="password" value={signupPassword} onChange={(e) => setSignupPassword(e.target.value)} placeholder="Password" className="w-full rounded-md border border-[var(--color-aegis-border)] bg-[#0d1117] px-3 py-2.5 font-mono text-sm outline-none focus:border-[#34d399]/45" />
              <input type="password" value={confirmPassword} onChange={(e) => setConfirmPassword(e.target.value)} placeholder="Confirm password" className="w-full rounded-md border border-[var(--color-aegis-border)] bg-[#0d1117] px-3 py-2.5 font-mono text-sm outline-none focus:border-[#34d399]/45" />
              <div className="rounded-md border border-[var(--color-aegis-border)] bg-[#060810] p-3 font-data text-[11px] text-[#9aa7b8]">
                <div className="mb-2 flex items-center justify-between"><span>Password strength</span><span>{strengthLabel}</span></div>
                <ul className="space-y-1">
                  <li className={passwordChecks.minLength ? "text-[#86efac]" : undefined}>At least 12 characters</li>
                  <li className={passwordChecks.hasUppercase ? "text-[#86efac]" : undefined}>One uppercase letter</li>
                  <li className={passwordChecks.hasLowercase ? "text-[#86efac]" : undefined}>One lowercase letter</li>
                  <li className={passwordChecks.hasNumber ? "text-[#86efac]" : undefined}>One number</li>
                  <li className={passwordChecks.hasSpecial ? "text-[#86efac]" : undefined}>One special character</li>
                </ul>
              </div>
              <button type="submit" disabled={isSubmitting} className="flex w-full items-center justify-center gap-2 rounded-md border border-[#34d399]/35 bg-[#34d399]/10 px-4 py-3 font-data text-sm text-[#a7f3d0] disabled:opacity-60"><UserRoundPlus className="h-4 w-4" />{isSubmitting ? "Creating..." : "Create account"}</button>
            </form>
          )}

          {mode === "forgot" && (
            <form className="mt-6 max-w-md space-y-4" onSubmit={onForgot}>
              <input type="email" value={forgotEmail} onChange={(e) => setForgotEmail(e.target.value)} placeholder="Account email" className="w-full rounded-md border border-[var(--color-aegis-border)] bg-[#0d1117] px-3 py-2.5 font-mono text-sm outline-none focus:border-[#34d399]/45" />
              <button type="submit" disabled={isSubmitting} className="flex w-full items-center justify-center gap-2 rounded-md border border-[#7dd3fc]/35 bg-[#0c2535] px-4 py-3 font-data text-sm text-[#bae6fd] disabled:opacity-60"><MailCheck className="h-4 w-4" />{isSubmitting ? "Sending..." : "Send reset link"}</button>
            </form>
          )}

          {mode === "otp" && (
            <form className="mt-6 max-w-md space-y-4" onSubmit={onVerifyOtp}>
              <input type="email" value={otpEmail} onChange={(e) => setOtpEmail(e.target.value)} placeholder="Verified email" className="w-full rounded-md border border-[var(--color-aegis-border)] bg-[#0d1117] px-3 py-2.5 font-mono text-sm outline-none focus:border-[#34d399]/45" />
              <input value={otpCode} onChange={(e) => setOtpCode(e.target.value)} placeholder="OTP code" className="w-full rounded-md border border-[var(--color-aegis-border)] bg-[#0d1117] px-3 py-2.5 font-mono text-sm tracking-[0.2em] outline-none focus:border-[#34d399]/45" />
              <button type="submit" disabled={isSubmitting} className="w-full rounded-md border border-[#34d399]/35 bg-[#34d399]/10 px-4 py-3 font-data text-sm text-[#a7f3d0] disabled:opacity-60">Verify OTP</button>
              <button type="button" disabled={isSubmitting} onClick={() => { void resendOtp(); }} className="flex w-full items-center justify-center gap-2 rounded-md border border-[var(--color-aegis-border)] bg-[#0d1117] px-4 py-2.5 font-data text-sm disabled:opacity-60"><RefreshCcw className="h-4 w-4" />Resend OTP</button>
            </form>
          )}
        </section>

        <aside className="flex flex-1 flex-col justify-center border-t border-[var(--color-aegis-border)] bg-[#0d1117] px-8 py-12 lg:border-l lg:border-t-0">
          <div className="grid grid-cols-2 gap-3">
            <div className="rounded-lg border border-[var(--color-aegis-border)] bg-[#060810]/70 p-4"><p className="font-display text-2xl text-[#34d399]">12.8k</p><p className="mt-1 font-mono text-[10px] text-[#9aa7b8]">Transactions scored today</p></div>
            <div className="rounded-lg border border-[var(--color-aegis-border)] bg-[#060810]/70 p-4"><p className="font-display text-2xl text-[#7dd3fc]">53+</p><p className="mt-1 font-mono text-[10px] text-[#9aa7b8]">Active risk alerts</p></div>
            <div className="rounded-lg border border-[var(--color-aegis-border)] bg-[#060810]/70 p-4"><p className="font-display text-2xl text-[#a78bfa]">0.934</p><p className="mt-1 font-mono text-[10px] text-[#9aa7b8]">PR-AUC meta model</p></div>
            <div className="rounded-lg border border-[var(--color-aegis-border)] bg-[#060810]/70 p-4"><p className="font-display text-2xl text-[#fbbf24]">185</p><p className="mt-1 font-mono text-[10px] text-[#9aa7b8]">Typology rules active</p></div>
          </div>
          <div className="mt-8 flex items-center justify-center gap-6 font-mono text-[10px] text-[#6b7c90]">
            <span className="inline-flex items-center gap-1.5"><Shield className="h-3.5 w-3.5" />SOC 2 Type II</span>
            <span>AES-256</span>
            <span>99.9% Uptime</span>
          </div>
        </aside>
      </div>
    </div>
  );
}
