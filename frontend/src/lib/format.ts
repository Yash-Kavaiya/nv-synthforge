export function formatCompact(value: number): string {
  return new Intl.NumberFormat("en-IN", { notation: "compact", maximumFractionDigits: 1 }).format(value);
}

export function formatRelative(dateValue: string, now = Date.now()): string {
  const timestamp = new Date(dateValue).getTime();
  if (Number.isNaN(timestamp)) return "Unknown time";
  const minutes = Math.max(0, Math.round((now - timestamp) / 60_000));
  if (minutes < 1) return "Just now";
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.round(hours / 24)}d ago`;
}

export function scoreTone(score: number): "excellent" | "good" | "review" {
  if (score >= 97) return "excellent";
  if (score >= 90) return "good";
  return "review";
}
