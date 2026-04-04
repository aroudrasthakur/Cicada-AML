import type { PasswordChecks } from "@/types/auth";

const USERNAME_PATTERN = /^[a-z0-9](?:[a-z0-9._-]{1,28}[a-z0-9])?$/;
const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export function sanitizeUsername(value: string): string {
  return value.trim().toLowerCase();
}

export function isValidUsername(value: string): boolean {
  return USERNAME_PATTERN.test(sanitizeUsername(value));
}

export function isValidEmail(value: string): boolean {
  return EMAIL_PATTERN.test(value.trim().toLowerCase());
}

export function getPasswordChecks(password: string): PasswordChecks {
  return {
    minLength: password.length >= 12,
    hasUppercase: /[A-Z]/.test(password),
    hasLowercase: /[a-z]/.test(password),
    hasNumber: /\d/.test(password),
    hasSpecial: /[^A-Za-z0-9]/.test(password),
  };
}

export function getPasswordStrengthScore(checks: PasswordChecks): number {
  return Number(checks.minLength)
    + Number(checks.hasUppercase)
    + Number(checks.hasLowercase)
    + Number(checks.hasNumber)
    + Number(checks.hasSpecial);
}

export function getPasswordStrengthLabel(score: number): string {
  if (score <= 2) return "Weak";
  if (score <= 4) return "Moderate";
  return "Strong";
}

export function mapSupabaseAuthError(rawMessage?: string): string {
  const message = (rawMessage ?? "").toLowerCase();

  if (message.includes("invalid login credentials")) {
    return "Invalid username/email or password.";
  }
  if (message.includes("email not confirmed")) {
    return "Your email is not verified yet. Use the OTP sent to your inbox.";
  }
  if (message.includes("user already registered")) {
    return "This email is already registered.";
  }
  if (message.includes("password should be at least")) {
    return "Password does not meet the required complexity.";
  }
  if (message.includes("rate limit")) {
    return "Too many attempts. Please wait a minute and try again.";
  }

  return rawMessage ?? "Authentication failed. Please try again.";
}
