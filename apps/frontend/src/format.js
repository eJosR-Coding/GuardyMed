const dateFmt = new Intl.DateTimeFormat("en-GB", { weekday: "short", day: "numeric", month: "short" });
const monthFmt = new Intl.DateTimeFormat("en-GB", { month: "long", year: "numeric" });
const stampFmt = new Intl.DateTimeFormat("en-GB", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });

// "2026-10-22" -> local Date (no timezone shift)
export function parseDay(iso) {
  const [y, m, d] = iso.split("-").map(Number);
  return new Date(y, m - 1, d);
}

export function isoDay(date) {
  const pad = (n) => String(n).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
}

export const today = () => isoDay(new Date());
export const fmtDay = (iso) => dateFmt.format(parseDay(iso));
export const fmtMonth = (year, month) => monthFmt.format(new Date(year, month - 1, 1));
export const fmtStamp = (value) => stampFmt.format(new Date(value));
export const fmtTime = (value) => String(value).slice(0, 5);
export const fmtRange = (a) => `${fmtTime(a.start_time)}–${fmtTime(a.end_time)}`;
export const isNight = (a) => fmtTime(a.start_time) >= "18:00";

export function words(value) {
  const text = String(value || "").replace(/[_.]/g, " ").trim();
  return text ? text[0].toUpperCase() + text.slice(1) : "";
}

export const firstName = (name) => String(name || "").split(" ")[0];
export const initial = (name) => String(name || "?").trim()[0] || "?";

// status -> chip tone. Green/amber/red are reserved for status.
export function tone(status) {
  if (["approved", "accepted", "verified", "active", "closed"].includes(status)) return "ok";
  if (["pending", "in_review", "needs_review"].includes(status)) return "warn";
  if (["rejected", "not_verified"].includes(status)) return "bad";
  if (status === "draft") return "accent";
  return "";
}

const STATUS_TEXT = {
  in_review: "In review",
  needs_review: "Needs review",
  not_verified: "Not verified",
  no_record: "No record",
};
export const statusText = (status) => STATUS_TEXT[status] || words(status);

export const ASSIGNMENT_TYPES = [
  { value: "guard_shift", label: "Guard shift" },
  { value: "shift_lead", label: "Shift lead" },
  { value: "on_call", label: "On call" },
];

export const REQUEST_TYPES = [
  { value: "replacement", label: "Someone covers my shift" },
  { value: "swap", label: "Swap with a colleague" },
  { value: "adjustment", label: "Adjust the hours" },
  { value: "incident", label: "Report an incident" },
];

export const typeLabel = (list, value) => list.find((item) => item.value === value)?.label || words(value);
