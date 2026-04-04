export function formatNumber(value: number, decimals = 2): string {
  return new Intl.NumberFormat("en-US", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(value);
}

export function formatCurrency(value: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
  }).format(value);
}

export function formatDate(value: string): string {
  return new Date(value).toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function formatRiskLevel(score: number | null): {
  label: string;
  color: string;
} {
  if (score === null) return { label: "Unknown", color: "text-gray-400" };
  if (score >= 0.75) return { label: "Critical", color: "text-red-400" };
  if (score >= 0.5) return { label: "High", color: "text-orange-400" };
  if (score >= 0.25) return { label: "Medium", color: "text-yellow-400" };
  return { label: "Low", color: "text-green-400" };
}

export function truncateAddress(address: string, chars = 6): string {
  if (address.length <= chars * 2 + 2) return address;
  return `${address.slice(0, chars)}...${address.slice(-chars)}`;
}
