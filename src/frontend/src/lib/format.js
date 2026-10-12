export function fmtNum(n, digits = 0) {
  if (n == null || Number.isNaN(n)) return '—';
  return new Intl.NumberFormat('en-US', {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  }).format(n);
}

export const mbToGb = (mb) => mb / 1024;

export function fmtMB(mb) {
  if (mb == null) return '—';
  return mb >= 1024 ? `${fmtNum(mb / 1024, 2)} GB` : `${fmtNum(mb, 1)} MB`;
}

export const fmtGB = (gb) => (gb == null ? '—' : `${fmtNum(gb, 2)} GB`);

function toDate(iso) {
  if (!iso) return null;
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? null : d;
}

export function fmtDateTime(iso) {
  const d = toDate(iso);
  if (!d) return '—';
  return d.toLocaleString(undefined, { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' });
}

export function fmtTime(iso) {
  const d = toDate(iso);
  if (!d) return '—';
  return d.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' });
}

export function timeAgo(iso) {
  const d = toDate(iso);
  if (!d) return '—';
  const sec = Math.round((Date.now() - d.getTime()) / 1000);
  if (sec < 45) return 'just now';
  if (sec < 3600) return `${Math.round(sec / 60)} min ago`;
  if (sec < 86400) return `${Math.round(sec / 3600)} h ago`;
  return `${Math.round(sec / 86400)} d ago`;
}

export function duration(start, end) {
  const a = toDate(start);
  const b = toDate(end);
  if (!a || !b) return '—';
  const ms = b - a;
  if (ms < 1000) return '<1 s';
  const s = Math.round(ms / 1000);
  return s < 60 ? `${s} s` : `${Math.floor(s / 60)} min ${s % 60} s`;
}

export const plural = (n, one, many = `${one}s`) => `${fmtNum(n)} ${n === 1 ? one : many}`;

// Convert between <input type="datetime-local"> values and ISO strings.
export const localInputToIso = (v) => (v ? new Date(v).toISOString() : undefined);
export function nowLocalInput(date = new Date()) {
  const pad = (n) => String(n).padStart(2, '0');
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}
