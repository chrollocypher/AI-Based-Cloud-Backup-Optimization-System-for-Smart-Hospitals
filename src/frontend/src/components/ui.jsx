import { createContext, useCallback, useContext, useEffect, useRef, useState } from 'react';
import { AlertTriangle, CheckCircle2, Inbox, Info, Loader2, X } from 'lucide-react';
import { fmtGB } from '../lib/format.js';

/* ---------- Tags ---------- */

const CRITICALITY = { CRITICAL: 'Critical', HIGH: 'High', MEDIUM: 'Medium', LOW: 'Low' };
export const CRITICALITY_RANK = { CRITICAL: 4, HIGH: 3, MEDIUM: 2, LOW: 1 };

// Triage-tag colours: the same red / orange / yellow / green a ward uses.
export function CriticalityTag({ level }) {
  const key = (level || '').toUpperCase();
  return <span className={`tag tag-${key.toLowerCase()}`}>{CRITICALITY[key] || level || '—'}</span>;
}

const STATUS = {
  PENDING: 'Pending',
  SCHEDULED: 'Scheduled',
  IN_PROGRESS: 'In progress',
  COMPLETED: 'Completed',
  FAILED: 'Failed',
};

export function StatusTag({ status }) {
  const key = (status || '').toUpperCase();
  return (
    <span className={`status status-${key.toLowerCase().replace('_', '-')}`}>
      <i aria-hidden="true" />
      {STATUS[key] || status || '—'}
    </span>
  );
}

const ACTION = {
  BACKUP_NOW: ['Back up now', 'now'],
  BACKUP_NEXT: ['Next round', 'next'],
  DEFER: ['Deferred', 'defer'],
};

export function ActionTag({ action }) {
  const [label, cls] = ACTION[action] || [action, 'defer'];
  return <span className={`action action-${cls}`}>{label}</span>;
}

const TIER_CLASS = {
  HOT: 'low', STANDARD: 'low',
  WARM: 'medium', STANDARD_IA: 'medium',
  COLD: 'high', GLACIER: 'high',
  ARCHIVE: 'critical', DEEP_ARCHIVE: 'critical',
};

export function TierTag({ tier }) {
  const key = (tier || '').toUpperCase();
  const label = { STANDARD: 'HOT / Standard', STANDARD_IA: 'WARM / IA', GLACIER: 'COLD / Glacier', DEEP_ARCHIVE: 'ARCHIVE' }[key] || key || '—';
  const cls = TIER_CLASS[key] || 'medium';
  return <span className={`tag tag-${cls}`}>{label}</span>;
}

/* ---------- Layout pieces ---------- */

export function PageHeader({ title, subtitle, actions }) {
  return (
    <header className="page-header">
      <div>
        <h1>{title}</h1>
        {subtitle && <p className="muted">{subtitle}</p>}
      </div>
      {actions && <div className="page-actions">{actions}</div>}
    </header>
  );
}

export function Panel({ title, subtitle, aside, children, flush = false, className = '' }) {
  return (
    <section className={`panel ${className}`}>
      {(title || aside) && (
        <div className="panel-head">
          <div>
            {title && <h2>{title}</h2>}
            {subtitle && <p className="muted small">{subtitle}</p>}
          </div>
          {aside && <div className="panel-aside">{aside}</div>}
        </div>
      )}
      <div className={flush ? 'panel-body flush' : 'panel-body'}>{children}</div>
    </section>
  );
}

// A row of figures divided by rules, rather than a set of separate cards.
export function Figures({ items }) {
  return (
    <dl className="figures">
      {items.map((it) => (
        <div key={it.label} className={it.tone ? `figure tone-${it.tone}` : 'figure'}>
          <dt>{it.label}</dt>
          <dd>{it.value}</dd>
          {it.note && <span className="figure-note">{it.note}</span>}
        </div>
      ))}
    </dl>
  );
}

/* ---------- States ---------- */

export function Loading({ label = 'Loading' }) {
  return (
    <div className="state" role="status">
      <Loader2 className="spin" size={18} aria-hidden="true" />
      <span>{label}</span>
    </div>
  );
}

export function ErrorBox({ error, onRetry }) {
  return (
    <div className="state state-error" role="alert">
      <AlertTriangle size={18} aria-hidden="true" />
      <div>
        <strong>Something went wrong</strong>
        <p>{error?.message || 'The request failed.'}</p>
        {onRetry && (
          <button className="btn" onClick={() => onRetry()}>
            Try again
          </button>
        )}
      </div>
    </div>
  );
}

export function Empty({ title, children, action }) {
  return (
    <div className="state state-empty">
      <Inbox size={22} aria-hidden="true" />
      <strong>{title}</strong>
      {children && <p>{children}</p>}
      {action && <div className="state-actions">{action}</div>}
    </div>
  );
}

export function Notice({ tone = 'info', children, action }) {
  return (
    <div className={`notice notice-${tone}`} role="status">
      <Info size={16} aria-hidden="true" />
      <span>{children}</span>
      {action}
    </div>
  );
}

/* ---------- Toasts ---------- */

const ToastContext = createContext({ push: () => {} });
export const useToast = () => useContext(ToastContext);

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([]);
  const nextId = useRef(1);

  const push = useCallback((kind, message) => {
    const id = nextId.current++;
    setToasts((t) => [...t, { id, kind, message }]);
    setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), kind === 'error' ? 8000 : 4500);
  }, []);

  const value = {
    success: (m) => push('success', m),
    error: (m) => push('error', m),
  };

  return (
    <ToastContext.Provider value={value}>
      {children}
      <div className="toasts" aria-live="polite">
        {toasts.map((t) => (
          <div key={t.id} className={`toast toast-${t.kind}`}>
            {t.kind === 'error' ? <AlertTriangle size={16} aria-hidden="true" /> : <CheckCircle2 size={16} aria-hidden="true" />}
            <span>{t.message}</span>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

/* ---------- Drawer ---------- */

export function Drawer({ open, title, onClose, children, footer }) {
  const closeRef = useRef(null);

  useEffect(() => {
    if (!open) return undefined;
    const onKey = (e) => e.key === 'Escape' && onClose();
    document.addEventListener('keydown', onKey);
    closeRef.current?.focus();
    return () => document.removeEventListener('keydown', onKey);
  }, [open, onClose]);

  if (!open) return null;
  return (
    <div className="drawer-root">
      <div className="drawer-scrim" onClick={onClose} />
      <aside className="drawer" role="dialog" aria-modal="true" aria-label={title}>
        <div className="drawer-head">
          <h2>{title}</h2>
          <button ref={closeRef} className="icon-btn" onClick={onClose} aria-label="Close panel">
            <X size={18} />
          </button>
        </div>
        <div className="drawer-body">{children}</div>
        {footer && <div className="drawer-foot">{footer}</div>}
      </aside>
    </div>
  );
}

export function DefinitionList({ items }) {
  return (
    <dl className="deflist">
      {items.map(([k, v]) => (
        <div key={k}>
          <dt>{k}</dt>
          <dd>{v ?? '—'}</dd>
        </div>
      ))}
    </dl>
  );
}

/* ---------- Capacity visuals ---------- */

// Predicted workload as a bar, with the capacity limit marked on the same scale.
export function CapacityGauge({ predictedMB, capacityMB }) {
  if (predictedMB == null || !capacityMB) return null;
  const max = Math.max(predictedMB, capacityMB) * 1.2;
  const fill = (Math.min(predictedMB, capacityMB) / max) * 100;
  const mark = (capacityMB / max) * 100;
  const overWidth = predictedMB > capacityMB ? ((predictedMB - capacityMB) / max) * 100 : 0;
  return (
    <div className="gauge">
      <div className="gauge-track" role="img" aria-label={`Predicted ${fmtGB(predictedMB / 1024)} against a limit of ${fmtGB(capacityMB / 1024)}`}>
        <div className="gauge-fill" style={{ width: `${fill}%` }} />
        {overWidth > 0 && <div className="gauge-over" style={{ left: `${mark}%`, width: `${overWidth}%` }} />}
        <div className="gauge-mark" style={{ left: `${mark}%` }} />
      </div>
      <div className="gauge-legend">
        <span>Predicted {fmtGB(predictedMB / 1024)}</span>
        <span>Limit {fmtGB(capacityMB / 1024)}</span>
      </div>
    </div>
  );
}

// Confidence interval of a forecast, drawn against the capacity limit.
export function ForecastRange({ low, high, predicted, capacityMB }) {
  const values = [low, high, predicted, capacityMB].filter((v) => v != null);
  const min = Math.min(...values) * 0.9;
  const max = Math.max(...values) * 1.1;
  const pos = (v) => ((v - min) / (max - min)) * 100;
  return (
    <div className="range">
      <div className="range-track" role="img" aria-label={`Forecast between ${fmtGB(low / 1024)} and ${fmtGB(high / 1024)}`}>
        <div className="range-band" style={{ left: `${pos(low)}%`, width: `${pos(high) - pos(low)}%` }} />
        <div className="range-point" style={{ left: `${pos(predicted)}%` }} />
        {capacityMB != null && <div className="range-limit" style={{ left: `${pos(capacityMB)}%` }} />}
      </div>
      <ul className="range-legend">
        <li><i className="key key-band" />Likely range {fmtGB(low / 1024)} to {fmtGB(high / 1024)}</li>
        <li><i className="key key-point" />Forecast {fmtGB(predicted / 1024)}</li>
        {capacityMB != null && <li><i className="key key-limit" />Capacity limit {fmtGB(capacityMB / 1024)}</li>}
      </ul>
    </div>
  );
}
