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

export function formatDate(value: string | null | undefined): string {
  if (!value) {
    return "-";
  }
  return new Intl.DateTimeFormat("en", { month: "short", day: "numeric", year: "numeric" }).format(new Date(value));
}

export function sentenceCase(value: string): string {
  return value.replace(/_/g, " ").replace(/\b\w/g, (char) => char.toUpperCase());
}

export function metadataValue(metadata: Record<string, unknown>, key: string): string | null {
  const value = metadata[key];
  return typeof value === "string" && value.length > 0 ? value : null;
}
