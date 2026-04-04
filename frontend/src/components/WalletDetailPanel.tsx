import type { Wallet, WalletScore } from "../types/wallet";
import { formatCurrency, formatDate, formatNumber } from "../utils/formatters";

export interface WalletDetailPanelProps {
  wallet: Wallet | null;
  score?: WalletScore | null;
}

function scoreBarColor(value: number): string {
  if (value >= 0.75) return "bg-red-500";
  if (value >= 0.5) return "bg-orange-500";
  if (value >= 0.25) return "bg-yellow-500";
  return "bg-green-500";
}

function SubScoreRow({
  label,
  value,
}: {
  label: string;
  value: number | null | undefined;
}) {
  if (value == null) {
    return (
      <div className="flex items-center justify-between gap-2 text-sm">
        <span className="text-gray-500">{label}</span>
        <span className="text-gray-600">—</span>
      </div>
    );
  }
  const pct = Math.min(100, Math.max(0, value * 100));
  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between gap-2 text-sm">
        <span className="text-gray-400">{label}</span>
        <span className="tabular-nums text-gray-200">
          {formatNumber(value, 2)}
        </span>
      </div>
      <div className="h-1.5 overflow-hidden rounded-full bg-gray-800">
        <div
          className={`h-full rounded-full ${scoreBarColor(value)}`}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}

export default function WalletDetailPanel({
  wallet,
  score,
}: WalletDetailPanelProps) {
  if (!wallet) {
    return (
      <aside className="h-full rounded-xl border border-gray-800 bg-gray-900 p-6 text-gray-100">
        <p className="text-sm text-gray-500">Select a wallet to view details.</p>
      </aside>
    );
  }

  const risk = score?.risk_score ?? null;
  const riskPct = risk == null ? 0 : Math.min(100, Math.max(0, risk * 100));

  return (
    <aside className="h-full rounded-xl border border-gray-800 bg-gray-900 p-6 text-gray-100">
      <h2 className="text-lg font-semibold text-white">Wallet</h2>
      <p className="mt-2 break-all font-mono text-xs text-gray-300">
        {wallet.wallet_address}
      </p>
      {wallet.chain_id && (
        <p className="mt-1 text-xs text-gray-500">Chain: {wallet.chain_id}</p>
      )}

      <dl className="mt-6 space-y-3 text-sm">
        <div className="flex justify-between gap-2">
          <dt className="text-gray-500">First seen</dt>
          <dd className="text-right text-gray-200">
            {wallet.first_seen ? formatDate(wallet.first_seen) : "—"}
          </dd>
        </div>
        <div className="flex justify-between gap-2">
          <dt className="text-gray-500">Last seen</dt>
          <dd className="text-right text-gray-200">
            {wallet.last_seen ? formatDate(wallet.last_seen) : "—"}
          </dd>
        </div>
        <div className="flex justify-between gap-2">
          <dt className="text-gray-500">Total in</dt>
          <dd className="tabular-nums text-gray-200">
            {formatCurrency(wallet.total_in)}
          </dd>
        </div>
        <div className="flex justify-between gap-2">
          <dt className="text-gray-500">Total out</dt>
          <dd className="tabular-nums text-gray-200">
            {formatCurrency(wallet.total_out)}
          </dd>
        </div>
      </dl>

      <div className="mt-8">
        <h3 className="text-sm font-medium text-gray-300">Risk score</h3>
        {risk == null ? (
          <p className="mt-2 text-sm text-gray-500">No score available.</p>
        ) : (
          <>
            <div className="mt-2 flex items-baseline justify-between gap-2">
              <span className="text-2xl font-semibold tabular-nums text-white">
                {(risk * 100).toFixed(0)}%
              </span>
              <span className="text-xs text-gray-500">0–100</span>
            </div>
            <div className="mt-2 h-2 overflow-hidden rounded-full bg-gray-800">
              <div
                className={`h-full rounded-full ${scoreBarColor(risk)}`}
                style={{ width: `${riskPct}%` }}
              />
            </div>
          </>
        )}
      </div>

      {score && (
        <div className="mt-8 space-y-4 border-t border-gray-800 pt-6">
          <h3 className="text-sm font-medium text-gray-300">Score breakdown</h3>
          <SubScoreRow label="Fan-in" value={score.fan_in_score} />
          <SubScoreRow label="Fan-out" value={score.fan_out_score} />
          <SubScoreRow label="Velocity" value={score.velocity_score} />
          <SubScoreRow label="Exposure" value={score.exposure_score} />
        </div>
      )}
    </aside>
  );
}
