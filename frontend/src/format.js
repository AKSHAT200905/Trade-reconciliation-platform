const usd = new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 2 });
const compactUsd = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  notation: "compact",
  minimumFractionDigits: 0,
  maximumFractionDigits: 2,
});
const integer = new Intl.NumberFormat("en-US", { maximumFractionDigits: 0 });

export function formatMoney(value, compact = false) {
  const number = Number(value ?? 0);
  if (!Number.isFinite(number)) return "-";
  return compact ? compactUsd.format(number) : usd.format(number);
}

export function formatNumber(value) {
  const number = Number(value ?? 0);
  if (!Number.isFinite(number)) return "-";
  if (Number.isInteger(number)) return integer.format(number);
  return new Intl.NumberFormat("en-US", { maximumFractionDigits: 6 }).format(number);
}

export function formatPercent(value) {
  const number = Number(value);
  if (value === null || value === undefined || !Number.isFinite(number)) return "-";
  return `${number.toFixed(2)}%`;
}

export function formatDate(value) {
  if (!value) return "-";
  const [year, month, day] = String(value).slice(0, 10).split("-").map(Number);
  if (!year || !month || !day) return "-";
  return new Date(Date.UTC(year, month - 1, day)).toLocaleDateString("en-GB", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    timeZone: "UTC",
  });
}

export function formatDateTime(value) {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "-";
  return date.toLocaleString("en-GB", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" });
}

export function humanize(value) {
  if (!value) return "-";
  return String(value)
    .toLowerCase()
    .split("_")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}
