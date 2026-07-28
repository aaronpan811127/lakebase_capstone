export const currency = (n: number | null | undefined): string =>
  n == null ? "—" : n.toLocaleString("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 });

export const num = (n: number | null | undefined): string =>
  n == null ? "—" : n.toLocaleString("en-US");

export const pct = (n: number | null | undefined): string =>
  n == null ? "—" : `${Math.round(n * 100)}%`;

export const SEGMENT_NAMES: Record<string, string> = {
  S1: "Champions",
  S2: "Loyal",
  S3: "Potential Loyalists",
  S4: "New Customers",
  S5: "At Risk",
  S6: "Hibernating",
  S7: "Price Sensitive",
  S8: "About to Churn",
};

export const segmentName = (id: string): string => SEGMENT_NAMES[id] ?? id;

// churn -> color band
export const churnTone = (score: number): string =>
  score >= 0.7 ? "danger" : score >= 0.4 ? "warn" : "ok";
