import client from "./client";
import type { NetworkCase } from "../types/network";

export async function fetchNetworkCases(params?: { page?: number; limit?: number }) {
  const { data } = await client.get<NetworkCase[]>("/networks", { params });
  return data;
}

export async function fetchNetworkCase(id: string) {
  const { data } = await client.get<NetworkCase>(`/networks/${id}`);
  return data;
}

export async function fetchNetworkGraph(id: string) {
  const { data } = await client.get(`/networks/${id}/graph`);
  return data;
}

export async function detectNetworks() {
  const { data } = await client.post("/networks/detect");
  return data;
}
