import { useContext } from "react";
import { RunCtx, type RunContextValue } from "@/contexts/runContext";

export function useRunContext(): RunContextValue {
  const ctx = useContext(RunCtx);
  if (!ctx) throw new Error("useRunContext must be inside <RunProvider>");
  return ctx;
}
