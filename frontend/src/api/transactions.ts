import client from "./client";
import type { Transaction, TransactionScore } from "../types/transaction";

export async function fetchTransactions(params?: {
  page?: number;
  limit?: number;
  label?: string;
  min_risk?: number;
}) {
  const { data } = await client.get<Transaction[]>("/transactions", { params });
  return data;
}

export async function fetchTransaction(id: string) {
  const { data } = await client.get<Transaction>(`/transactions/${id}`);
  return data;
}

export async function scoreTransactions() {
  const { data } = await client.post<{ scored: number }>("/transactions/score");
  return data;
}

export async function fetchTransactionScore(transactionId: string) {
  const { data } = await client.get<TransactionScore>(`/transactions/${transactionId}/score`);
  return data;
}
