import client from "./client";
import type { Wallet } from "../types/wallet";

export async function fetchWallets(params?: { page?: number; limit?: number }) {
  const { data } = await client.get<Wallet[]>("/wallets", { params });
  return data;
}

export async function fetchWallet(address: string) {
  const { data } = await client.get<Wallet>(`/wallets/${address}`);
  return data;
}

export async function fetchWalletGraph(address: string) {
  const { data } = await client.get(`/wallets/${address}/graph`);
  return data;
}
