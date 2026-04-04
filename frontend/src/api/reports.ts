import client from "./client";
import type { Report } from "../types/report";

export async function fetchReports() {
  const { data } = await client.get<Report[]>("/reports");
  return data;
}

export async function generateReport(caseId: string) {
  const { data } = await client.post<Report>(`/reports/generate/${caseId}`);
  return data;
}

export async function downloadReport(reportId: string) {
  const { data } = await client.get(`/reports/${reportId}/download`, {
    responseType: "blob",
  });
  return data;
}
