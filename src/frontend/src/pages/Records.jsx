import { useMemo, useState } from 'react';
import { ArrowDown, ArrowUp, CloudUpload, Plus, Search, ShieldAlert } from 'lucide-react';
import { api, runBackups } from '../api/client.js';
import { useApi } from '../hooks/useApi.js';
import {
  CRITICALITY_RANK, CriticalityTag, DefinitionList, Drawer, Empty, ErrorBox, Loading, PageHeader, Panel, StatusTag, TierTag, useToast,
} from '../components/ui.jsx';
import { fmtDateTime, fmtMB, fmtNum, localInputToIso, nowLocalInput, plural } from '../lib/format.js';
import { DEPARTMENTS, RECORD_TYPES, SAMPLE_RECORDS } from '../lib/sample.js';

const COLUMNS = [
  { key: 'record_id', label: 'Record', get: (r) => r.record_id },
  { key: 'criticality', label: 'Criticality', get: (r) => CRITICALITY_RANK[r.criticality] || 0 },
  { key: 'data_size_mb', label: 'Size', get: (r) => r.data_size_mb, num: true },
  { key: 'access_frequency', label: 'Accessed (24h)', get: (r) => r.access_frequency, num: true },
  { key: 'storage_tier', label: 'Tier', get: (r) => r.storage_tier || '' },
  { key: 'priority', label: 'Priority', get: (r) => r.priority ?? -1, num: true },
  { key: 'backup_status', label: 'Status', get: (r) => r.backup_status },
  { key: 'last_backup', label: 'Last backup', get: (r) => (r.last_backup ? new Date(r.last_backup).getTime() : 0) },
];

export default function Records() {
  const toast = useToast();
  const records = useApi(api.listRecords, []);
  const schedule = useApi(api.getSchedule, []);
  const [query, setQuery] = useState('');
  const [criticality, setCriticality] = useState('');
  const [status, setStatus] = useState('');
  const [sort, setSort] = useState({ key: 'priority', dir: 'desc' });
  const [selected, setSelected] = useState(null);
  const [creating, setCreating] = useState(false);
  const [seeding, setSeeding] = useState(false);

  // Priority scores are only computed when a schedule is generated, so borrow them from it.
  const priorities = useMemo(() => {
    const map = new Map();
    (schedule.data?.schedule || []).forEach((i) => map.set(i.record_id, i.priority_score));
    return map;
  }, [schedule.data]);

  const rows = useMemo(() => {
    const q = query.trim().toLowerCase();
    const col = COLUMNS.find((c) => c.key === sort.key) || COLUMNS[0];
    return (records.data || [])
      .map((r) => ({ ...r, priority: priorities.get(r.record_id) }))
      .filter((r) => !criticality || r.criticality === criticality)
      .filter((r) => !status || r.backup_status === status)
      .filter((r) => !q || [r.record_id, r.record_type, r.department].some((v) => v.toLowerCase().includes(q)))
      .sort((a, b) => {
        const x = col.get(a);
        const y = col.get(b);
        const cmp = typeof x === 'string' ? x.localeCompare(y) : x - y;
        return sort.dir === 'asc' ? cmp : -cmp;
      });
  }, [records.data, priorities, query, criticality, status, sort]);

  const toggleSort = (key) =>
    setSort((s) => (s.key === key ? { key, dir: s.dir === 'asc' ? 'desc' : 'asc' } : { key, dir: key === 'record_id' ? 'asc' : 'desc' }));

  const refresh = () => {
    records.reload(true);
    schedule.reload(true);
  };

  const loadSamples = async () => {
    setSeeding(true);
    let added = 0;
    for (const rec of SAMPLE_RECORDS) {
      try {
        await api.createRecord({ ...rec, timestamp: new Date().toISOString() });
        added += 1;
      } catch (e) {
        if (e.status !== 400) {
          toast.error(e.message);
          break;
        }
      }
    }
    await api.generateSchedule().catch(() => {});
    setSeeding(false);
    if (added) toast.success(`Added ${plural(added, 'sample record')}.`);
    refresh();
  };

  if (records.error && !records.data) return <ErrorBox error={records.error} onRetry={records.reload} />;
  if (!records.data) return <Loading label="Loading records" />;

  const all = records.data;

  return (
    <>
      <PageHeader
        title="Records"
        subtitle={`${plural(all.length, 'record')} registered`}
        actions={
          <button className="btn primary" onClick={() => setCreating(true)}>
            <Plus size={16} aria-hidden="true" />
            Register record
          </button>
        }
      />

      {all.length === 0 ? (
        <Panel>
          <Empty
            title="No records registered yet"
            action={
              <>
                <button className="btn primary" onClick={() => setCreating(true)}>Register a record</button>
                <button className="btn" onClick={loadSamples} disabled={seeding}>
                  {seeding ? 'Adding samples' : 'Load sample records'}
                </button>
              </>
            }
          >
            The backend keeps records in memory, so it starts empty after every restart.
          </Empty>
        </Panel>
      ) : (
        <Panel flush>
          <div className="toolbar">
            <label className="search">
              <Search size={16} aria-hidden="true" />
              <input
                type="search"
                placeholder="Search by ID, type or department"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                aria-label="Search records"
              />
            </label>
            <select value={criticality} onChange={(e) => setCriticality(e.target.value)} aria-label="Filter by criticality">
              <option value="">All criticality</option>
              <option value="CRITICAL">Critical</option>
              <option value="HIGH">High</option>
              <option value="MEDIUM">Medium</option>
              <option value="LOW">Low</option>
            </select>
            <select value={status} onChange={(e) => setStatus(e.target.value)} aria-label="Filter by status">
              <option value="">All statuses</option>
              <option value="PENDING">Pending</option>
              <option value="SCHEDULED">Scheduled</option>
              <option value="IN_PROGRESS">In progress</option>
              <option value="COMPLETED">Completed</option>
              <option value="FAILED">Failed</option>
            </select>
            <span className="toolbar-count muted small">{plural(rows.length, 'record')} shown</span>
          </div>
          <div className="table-wrap">
            <table className="table clickable">
              <thead>
                <tr>
                  {COLUMNS.map((c) => (
                    <th key={c.key} className={c.num ? 'num' : ''} aria-sort={sort.key === c.key ? (sort.dir === 'asc' ? 'ascending' : 'descending') : 'none'}>
                      <button className="th-btn" onClick={() => toggleSort(c.key)}>
                        {c.label}
                        {sort.key === c.key && (sort.dir === 'asc' ? <ArrowUp size={13} aria-hidden="true" /> : <ArrowDown size={13} aria-hidden="true" />)}
                      </button>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {rows.map((r) => (
                  <tr key={r.record_id} tabIndex={0} onClick={() => setSelected(r.record_id)} onKeyDown={(e) => e.key === 'Enter' && setSelected(r.record_id)}>
                    <td>
                      <div className="cell-strong">{r.record_id}</div>
                      <div className="cell-sub">{r.record_type}, {r.department}</div>
                    </td>
                    <td><CriticalityTag level={r.criticality} /></td>
                    <td className="num">{fmtMB(r.data_size_mb)}</td>
                    <td className="num">{fmtNum(r.access_frequency)}</td>
                    <td><TierTag tier={r.storage_tier} /></td>
                    <td className="num">{r.priority != null ? fmtNum(r.priority, 2) : '—'}</td>
                    <td><StatusTag status={r.backup_status} /></td>
                    <td>{fmtDateTime(r.last_backup)}</td>
                  </tr>
                ))}
                {rows.length === 0 && (
                  <tr>
                    <td colSpan={COLUMNS.length}>
                      <Empty title="No records match these filters" />
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </Panel>
      )}

      <RecordDrawer recordId={selected} onClose={() => setSelected(null)} onChanged={refresh} />
      <RegisterDrawer
        open={creating}
        onClose={() => setCreating(false)}
        onCreated={() => {
          setCreating(false);
          api.generateSchedule().catch(() => {}).finally(refresh);
        }}
      />
    </>
  );
}

function RecordDrawer({ recordId, onClose, onChanged }) {
  const toast = useToast();
  const record = useApi(() => (recordId ? api.getRecord(recordId) : Promise.resolve(null)), [recordId]);
  const jobs = useApi(() => (recordId ? api.listBackups() : Promise.resolve([])), [recordId]);
  const accessLogs = useApi(() => (recordId ? api.recordAccessHistory(recordId) : Promise.resolve([])), [recordId]);
  const [busy, setBusy] = useState(false);
  const r = record.data?.record_id === recordId ? record.data : null;
  const recordJobs = (jobs.data || []).filter((j) => j.record_id === recordId).sort((a, b) => new Date(b.scheduled_at) - new Date(a.scheduled_at));
  const events = (accessLogs.data || []).slice().reverse();

  const backUp = async () => {
    setBusy('backup');
    try {
      await runBackups(recordId);
      toast.success(`Backed up ${recordId}.`);
      record.reload(true);
      jobs.reload(true);
      onChanged();
    } catch (e) {
      toast.error(e.message);
    } finally {
      setBusy(false);
    }
  };

  const retrieve = async () => {
    setBusy('retrieve');
    try {
      const res = await api.retrieveRecord({
        record_id: recordId,
        is_emergency: true,
        department: r?.department || 'Emergency',
        reason: 'Clinical lookup from records console',
      });
      toast.success(`Retrieved ${recordId} in ${res.retrieval_latency_ms} ms (${res.sla_met ? 'SLA met' : 'SLA missed'}).`);
      record.reload(true);
      accessLogs.reload(true);
      onChanged();
    } catch (e) {
      toast.error(e.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <Drawer
      open={!!recordId}
      title={recordId || ''}
      onClose={onClose}
      footer={
        r && (
          <>
            <button className="btn" onClick={retrieve} disabled={!!busy}>
              <ShieldAlert size={16} aria-hidden="true" />
              {busy === 'retrieve' ? 'Retrieving' : 'Emergency retrieve'}
            </button>
            <button className="btn primary" onClick={backUp} disabled={!!busy}>
              <CloudUpload size={16} aria-hidden="true" />
              {busy === 'backup' ? 'Backing up' : r.backup_status === 'COMPLETED' ? 'Back up again' : 'Back up now'}
            </button>
          </>
        )
      }
    >
      {record.error && <ErrorBox error={record.error} onRetry={record.reload} />}
      {!r && !record.error && <Loading />}
      {r && (
        <>
          <div className="drawer-tags">
            <CriticalityTag level={r.criticality} />
            <StatusTag status={r.backup_status} />
            <TierTag tier={r.storage_tier} />
            {r.emergency_flag && <span className="tag tag-critical">Emergency</span>}
          </div>
          <DefinitionList
            items={[
              ['Patient ID', r.patient_id || '—'],
              ['Record type', r.record_type],
              ['Department', r.department],
              ['Size', fmtMB(r.data_size_mb)],
              ['Accessed in last 24h', fmtNum(r.access_frequency)],
              ['Storage tier', r.storage_tier],
              ['S3 location', r.s3_location || '—'],
              ['Generated', fmtDateTime(r.timestamp)],
              ['Registered', fmtDateTime(r.created_at)],
              ['Last accessed', fmtDateTime(r.last_accessed_at)],
              ['Last backup', fmtDateTime(r.last_backup)],
            ]}
          />
          <h3>Access history</h3>
          {recordId && accessLogs.data && events.length === 0 && <p className="muted small">No access events logged for this record yet.</p>}
          {events.length > 0 && (
            <ul className="history">
              {events.slice(0, 8).map((ev, idx) => (
                <li key={ev.event_id || idx}>
                  <div>
                    <div className="cell-strong">{ev.access_type || 'ACCESS'}</div>
                    <div className="cell-sub">{fmtDateTime(ev.timestamp)} · {ev.department}</div>
                  </div>
                  <span className="muted small">{ev.emergency_flag ? 'Emergency' : 'Standard'}</span>
                </li>
              ))}
            </ul>
          )}
          <h3>Backup history</h3>
          {recordId && jobs.data && recordJobs.length === 0 && <p className="muted small">This record has not been backed up yet.</p>}
          {recordJobs.length > 0 && (
            <ul className="history">
              {recordJobs.map((j) => (
                <li key={j.job_id}>
                  <div>
                    <div className="cell-strong">{j.job_id}</div>
                    <div className="cell-sub">{fmtDateTime(j.scheduled_at)}</div>
                  </div>
                  <StatusTag status={j.status} />
                </li>
              ))}
            </ul>
          )}
        </>
      )}
    </Drawer>
  );
}

const emptyForm = () => ({
  record_id: '',
  record_type: '',
  department: '',
  data_size_mb: '',
  access_frequency: '0',
  timestamp: nowLocalInput(),
});

function RegisterDrawer({ open, onClose, onCreated }) {
  const toast = useToast();
  const [form, setForm] = useState(emptyForm);
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);
  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));

  const close = () => {
    setForm(emptyForm());
    setError('');
    onClose();
  };

  const submit = async (e) => {
    e.preventDefault();
    setError('');
    const size = Number(form.data_size_mb);
    const freq = Number(form.access_frequency);
    if (!form.record_id.trim() || !form.record_type.trim() || !form.department.trim()) return setError('Fill in the record ID, type and department.');
    if (!(size > 0)) return setError('Size must be greater than 0 MB.');
    if (!Number.isInteger(freq) || freq < 0) return setError('Access frequency must be a whole number, 0 or more.');

    setSaving(true);
    try {
      const created = await api.createRecord({
        record_id: form.record_id.trim(),
        record_type: form.record_type.trim(),
        department: form.department.trim(),
        data_size_mb: size,
        access_frequency: freq,
        timestamp: localInputToIso(form.timestamp),
      });
      toast.success(`Registered ${created.record_id}. Criticality: ${created.criticality.toLowerCase()}.`);
      setForm(emptyForm());
      onCreated();
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <Drawer open={open} title="Register record" onClose={close}>
      <form className="form" onSubmit={submit} noValidate>
        <label>
          Record ID
          <input value={form.record_id} onChange={set('record_id')} placeholder="EHR_10026" autoComplete="off" />
        </label>
        <label>
          Record type
          <input value={form.record_type} onChange={set('record_type')} list="record-types" placeholder="Emergency EHR" />
          <datalist id="record-types">{RECORD_TYPES.map((t) => <option key={t} value={t} />)}</datalist>
        </label>
        <label>
          Department
          <input value={form.department} onChange={set('department')} list="departments" placeholder="Emergency" />
          <datalist id="departments">{DEPARTMENTS.map((d) => <option key={d} value={d} />)}</datalist>
        </label>
        <div className="form-row">
          <label>
            Size (MB)
            <input type="number" min="0" step="any" value={form.data_size_mb} onChange={set('data_size_mb')} placeholder="25.4" />
          </label>
          <label>
            Accessed in last 24h
            <input type="number" min="0" step="1" value={form.access_frequency} onChange={set('access_frequency')} />
          </label>
        </div>
        <label>
          Generated at
          <input type="datetime-local" value={form.timestamp} onChange={set('timestamp')} />
        </label>
        <p className="muted small">The server assigns criticality from the record type and department.</p>
        {error && <div className="form-error" role="alert">{error}</div>}
        <div className="form-actions">
          <button type="button" className="btn" onClick={close}>Cancel</button>
          <button type="submit" className="btn primary" disabled={saving}>{saving ? 'Registering' : 'Register record'}</button>
        </div>
      </form>
    </Drawer>
  );
}
