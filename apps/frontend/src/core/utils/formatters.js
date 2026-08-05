export function periodLabel(period) {
  return `${period.year}-${String(period.month).padStart(2, "0")}`;
}

export function formatDateTime(value) {
  try {
    return new Date(value).toLocaleString();
  } catch {
    return value;
  }
}

export function badgeSeverity(status) {
  if (status === "approved" || status === "accepted" || status === "active") return "success";
  if (status === "rejected") return "danger";
  if (status === "in_review" || status === "pending" || status === "cancelled") return "warn";
  return "secondary";
}
