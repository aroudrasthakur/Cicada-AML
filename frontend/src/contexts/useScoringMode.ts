import { useContext } from "react";
import { ScoringModeCtx } from "@/contexts/scoringModeContext";

export function useScoringMode() {
  const ctx = useContext(ScoringModeCtx);
  if (!ctx) {
    throw new Error("useScoringMode must be used within ScoringModeProvider");
  }
  return ctx;
}
