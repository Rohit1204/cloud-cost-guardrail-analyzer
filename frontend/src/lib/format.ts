export function formatMoney(value: number | null | undefined, currency = "USD"): string {
  const v = value ?? 0;
  const abs = Math.abs(v);
  const maximumFractionDigits = abs >= 100 ? 0 : abs >= 1 ? 2 : 4;
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency,
    maximumFractionDigits,
  }).format(v);
}

/** Invoice API totals: extra fraction digits so small deltas vs the console are visible. */
export function formatInvoiceMoney(value: number | null | undefined, currency = "USD"): string {
  const v = value ?? 0;
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency,
    minimumFractionDigits: 2,
    maximumFractionDigits: 6,
  }).format(v);
}

export function formatDate(value: string | null | undefined): string {
  if (!value) {
    return "-";
  }
  const trimmed = String(value ?? "").trim();
  const d = /^\d{4}-\d{2}-\d{2}$/.test(trimmed)
    ? new Date(`${trimmed}T00:00:00.000Z`)
    : new Date(trimmed);
  return new Intl.DateTimeFormat("en", {
    month: "short",
    day: "numeric",
    year: "numeric",
    timeZone: "UTC",
  }).format(d);
}

export function sentenceCase(value: string): string {
  return value.replace(/_/g, " ").replace(/\b\w/g, (char) => char.toUpperCase());
}

export function metadataValue(metadata: Record<string, unknown>, key: string): string | null {
  const value = metadata[key];
  return typeof value === "string" && value.length > 0 ? value : null;
}
