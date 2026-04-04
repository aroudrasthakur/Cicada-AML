import { useCallback, useRef, useState, type DragEvent } from "react";
import { Upload, X, FileText, AlertCircle, Loader2 } from "lucide-react";
import { createRun, startRun } from "@/api/runs";
import { useRunContext } from "@/contexts/useRunContext";

interface Props {
  open: boolean;
  onClose: () => void;
}

const MAX_FILES = 3;
const REQUIRED_HEADERS = [
  "transaction_id",
  "sender_wallet",
  "receiver_wallet",
  "amount",
  "timestamp",
];

export default function UploadModal({ open, onClose }: Props) {
  const { trackRun, refreshRuns } = useRunContext();
  const inputRef = useRef<HTMLInputElement>(null);
  const [files, setFiles] = useState<File[]>([]);
  const [label, setLabel] = useState("");
  const [dragOver, setDragOver] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const addFiles = useCallback(
    (incoming: FileList | File[]) => {
      const arr = Array.from(incoming).filter((f) =>
        f.name.toLowerCase().endsWith(".csv"),
      );
      if (arr.length === 0) {
        setError("Only .csv files are accepted");
        return;
      }
      setFiles((prev) => {
        const combined = [...prev, ...arr].slice(0, MAX_FILES);
        return combined;
      });
      setError(null);
    },
    [],
  );

  const removeFile = useCallback((idx: number) => {
    setFiles((prev) => prev.filter((_, i) => i !== idx));
  }, []);

  const handleDrop = useCallback(
    (e: DragEvent) => {
      e.preventDefault();
      setDragOver(false);
      if (e.dataTransfer.files.length) addFiles(e.dataTransfer.files);
    },
    [addFiles],
  );

  const handleSubmit = useCallback(async () => {
    if (files.length === 0) return;
    setUploading(true);
    setError(null);
    try {
      const res = await createRun(files, label || undefined);
      const { run_id } = res;
      await startRun(run_id);
      trackRun(run_id);
      await refreshRuns();
      setFiles([]);
      setLabel("");
      onClose();
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: { message?: string } | string } } })
          ?.response?.data?.detail;
      if (typeof msg === "string") {
        setError(msg);
      } else if (msg && typeof msg === "object" && "message" in msg) {
        setError((msg as { message: string }).message);
      } else {
        setError("Upload failed. Please try again.");
      }
    } finally {
      setUploading(false);
    }
  }, [files, label, onClose, trackRun, refreshRuns]);

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-[100] flex items-center justify-center bg-black/60 px-4 backdrop-blur-[2px]"
      role="presentation"
      onClick={onClose}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="upload-title"
        onClick={(e) => e.stopPropagation()}
        className="w-full max-w-lg rounded-xl border border-[var(--color-aegis-border)] bg-[#0d1117] shadow-xl"
      >
        {/* Header */}
        <div className="flex items-center justify-between border-b border-[var(--color-aegis-border)] px-5 py-4">
          <h2
            id="upload-title"
            className="font-display text-lg font-semibold text-[#e6edf3]"
          >
            Upload Transaction CSVs
          </h2>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg p-1 text-[#9aa7b8] hover:text-[#e6edf3]"
            aria-label="Close"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Body */}
        <div className="space-y-4 px-5 py-5">
          {/* Drop zone */}
          <div
            onDragOver={(e) => {
              e.preventDefault();
              setDragOver(true);
            }}
            onDragLeave={() => setDragOver(false)}
            onDrop={handleDrop}
            onClick={() => inputRef.current?.click()}
            className={`flex cursor-pointer flex-col items-center gap-2 rounded-lg border-2 border-dashed px-6 py-10 text-center transition-colors ${
              dragOver
                ? "border-[#34d399] bg-[#34d399]/5"
                : "border-[var(--color-aegis-border)] hover:border-[#34d399]/40"
            }`}
          >
            <Upload className="h-8 w-8 text-[#6b7c90]" />
            <p className="font-data text-sm text-[#9aa7b8]">
              Drag & drop up to {MAX_FILES} CSV files, or click to browse
            </p>
            <p className="font-mono text-[10px] text-[#6b7c90]">
              Required: {REQUIRED_HEADERS.join(", ")}
            </p>
            <input
              ref={inputRef}
              type="file"
              accept=".csv"
              multiple
              className="hidden"
              onChange={(e) => {
                if (e.target.files) addFiles(e.target.files);
                e.target.value = "";
              }}
            />
          </div>

          {/* File list */}
          {files.length > 0 && (
            <ul className="space-y-1">
              {files.map((f, i) => (
                <li
                  key={`${f.name}-${i}`}
                  className="flex items-center justify-between rounded-lg border border-[var(--color-aegis-border)] bg-[#060810] px-3 py-2"
                >
                  <span className="flex items-center gap-2 font-data text-sm text-[#c8d4e0]">
                    <FileText className="h-4 w-4 text-[#34d399]" />
                    {f.name}
                    <span className="text-[10px] text-[#6b7c90]">
                      ({(f.size / 1024).toFixed(1)} KB)
                    </span>
                  </span>
                  <button
                    type="button"
                    onClick={() => removeFile(i)}
                    className="text-[#9aa7b8] hover:text-[#f87171]"
                    aria-label={`Remove ${f.name}`}
                  >
                    <X className="h-4 w-4" />
                  </button>
                </li>
              ))}
            </ul>
          )}

          {/* Label */}
          <input
            type="text"
            placeholder="Run label (optional)"
            value={label}
            onChange={(e) => setLabel(e.target.value)}
            className="w-full rounded-lg border border-[var(--color-aegis-border)] bg-[#060810] px-3 py-2 font-data text-sm text-[#e6edf3] placeholder-[#6b7c90] focus:border-[#34d399]/50 focus:outline-none"
          />

          {/* Error */}
          {error && (
            <div className="flex items-start gap-2 rounded-lg border border-[#f87171]/30 bg-[#f87171]/5 px-3 py-2">
              <AlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-[#f87171]" />
              <p className="font-data text-sm text-[#fca5a5]">{error}</p>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex justify-end gap-2 border-t border-[var(--color-aegis-border)] px-5 py-4">
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg border border-[var(--color-aegis-border)] bg-[#060810] px-4 py-2 font-data text-sm text-[#e6edf3] hover:border-[#34d399]/35"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={handleSubmit}
            disabled={files.length === 0 || uploading}
            className="inline-flex items-center gap-2 rounded-lg border border-[#34d399]/40 bg-[#34d399]/10 px-4 py-2 font-data text-sm font-medium text-[#6ee7b7] hover:bg-[#34d399]/15 disabled:opacity-40"
          >
            {uploading ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                Uploading…
              </>
            ) : (
              <>
                <Upload className="h-4 w-4" />
                Upload & Run
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
