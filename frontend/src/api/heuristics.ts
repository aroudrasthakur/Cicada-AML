import client from "./client";
import type { HeuristicResult, HeuristicRegistryEntry } from "../types/heuristic";

export async function fetchHeuristicRegistry() {
  const { data } = await client.get<HeuristicRegistryEntry[]>("/heuristics/registry");
  return data;
}

export async function fetchHeuristicResults(transactionId: string) {
  const { data } = await client.get<HeuristicResult>(`/heuristics/${transactionId}`);
  return data;
}

export async function fetchHeuristicStats() {
  const { data } = await client.get("/heuristics/stats");
  return data;
}
