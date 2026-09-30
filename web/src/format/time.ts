// Times (UI-SPEC §9): every result time is shown in New York time, `2026-09-14 10:00 ET`.
const ET = new Intl.DateTimeFormat("en-CA", {
  timeZone: "America/New_York",
  year: "numeric",
  month: "2-digit",
  day: "2-digit",
  hour: "2-digit",
  minute: "2-digit",
  hourCycle: "h23",
});

/** An ISO 8601 time with its offset, as `YYYY-MM-DD HH:MM ET`. */
export function timeET(iso: string): string {
  const parts = Object.fromEntries(ET.formatToParts(new Date(iso)).map((p) => [p.type, p.value]));
  return `${parts.year}-${parts.month}-${parts.day} ${parts.hour}:${parts.minute} ET`;
}
