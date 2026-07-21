const styles: Record<string, string> = {
  connected: "bg-gravel text-ink",
  succeeded: "bg-gravel text-ink",
  pending: "bg-amber-100 text-amber-900",
  queued: "bg-amber-100 text-amber-900",
  running: "bg-blue-100 text-blue-900",
  processing: "bg-blue-100 text-blue-900",
  failed: "bg-red-100 text-red-800",
  error: "bg-red-100 text-red-800",
  revoked: "bg-moss/10 text-moss/60",
};

export function StatusBadge({ status }: { status: string }) {
  return (
    <span className={`rounded-full px-3 py-1 text-xs font-black uppercase tracking-wide ${styles[status] ?? "bg-fog text-moss/70"}`}>
      {status.replaceAll("_", " ")}
    </span>
  );
}
