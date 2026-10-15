// Thin client for the FastAPI backend (src/backend). Every route lives under /api/v1.
const BASE = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1').replace(/\/+$/, '');

export const API_BASE = BASE;
// The interactive Swagger docs are served from the backend root, outside /api/v1.
export const DOCS_URL = BASE.replace(/\/api\/v1$/, '') + '/docs';

export class ApiError extends Error {
  constructor(message, status = 0) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

// FastAPI returns `detail` as a string for HTTPException and as a list for validation errors.
function detailToMessage(detail) {
  if (!detail) return null;
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((d) => {
        const field = Array.isArray(d.loc) ? d.loc.filter((p) => p !== 'body').join('.') : '';
        return field ? `${field}: ${d.msg}` : d.msg;
      })
      .join('; ');
  }
  return JSON.stringify(detail);
}

async function request(path, { method = 'GET', body, params } = {}) {
  const qs = params
    ? new URLSearchParams(Object.entries(params).filter(([, v]) => v != null && v !== '')).toString()
    : '';
  const url = `${BASE}${path}${qs ? `?${qs}` : ''}`;

  let res;
  try {
    res = await fetch(url, {
      method,
      headers: body !== undefined ? { 'Content-Type': 'application/json' } : undefined,
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
  } catch {
    throw new ApiError(
      `Can't reach the backend at ${BASE}. Check that the API is running and that VITE_API_BASE_URL is correct.`,
    );
  }

  const text = await res.text();
  let data = null;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    /* non-JSON body */
  }
  if (!res.ok) throw new ApiError(detailToMessage(data?.detail) || `Request failed (${res.status})`, res.status);
  return data;
}

export const api = {
  // Health and monitoring
  health: () => request('/health'),
  monitoring: () => request('/monitoring/status'),
  systemTelemetry: () => request('/monitoring/system-telemetry'),
  cloudwatchAlarms: () => request('/monitoring/cloudwatch/alarms'),
  publishCloudWatch: () => request('/monitoring/cloudwatch/publish', { method: 'POST' }),

  // Dashboard
  summary: () => request('/dashboard/summary'),
  workload: () => request('/dashboard/workload'),

  // Records
  listRecords: (params) => request('/records', { params }),
  getRecord: (id) => request(`/records/${encodeURIComponent(id)}`),
  createRecord: (record) => request('/records', { method: 'POST', body: record }),
  ingestAccessEvents: (events) => request('/records/access-events', { method: 'POST', body: events }),
  patientAccessHistory: (patientId) =>
    request(`/records/patient/${encodeURIComponent(patientId)}/access-history`),
  recordAccessHistory: (recordId) =>
    request(`/records/${encodeURIComponent(recordId)}/access-history`),
  retrieveByRecord: (recordId, body) =>
    request(`/records/${encodeURIComponent(recordId)}/retrieve`, { method: 'POST', body: body || {} }),

  // Predictions & Forecasting
  latestPrediction: () => request('/predictions/latest'),
  predict: (input) => request('/predictions', { method: 'POST', body: input }),
  latestAccessPrediction: () => request('/predictions/access-demand/latest'),
  predictAccess: (input) => request('/predictions/access-demand', { method: 'POST', body: input }),
  jointForecast: () => request('/predictions/joint-forecast'),
  latestWorkloadForecast: () => request('/workload/forecast-latest'),

  // Scheduler
  getSchedule: () => request('/schedule'),
  generateSchedule: () => request('/schedule', { method: 'POST' }),

  // Backups
  listBackups: (status) => request('/backups', { params: { status } }),
  getBackup: (id) => request(`/backups/${encodeURIComponent(id)}`),
  triggerBackup: (recordId) =>
    request('/backups', { method: 'POST', body: recordId ? { record_id: recordId } : undefined }),
  retryBackup: (id) => request(`/backups/${encodeURIComponent(id)}/retry`, { method: 'POST' }),

  // S3 Multi-Tier Storage & Costs
  storageCostEstimate: (region = 'us-east-1') => request('/storage/cost-estimate', { params: { region } }),
  transitionTier: (recordId, targetTier, reason) =>
    request('/storage/tier-transitions', {
      method: 'POST',
      body: { record_id: recordId, target_tier: targetTier, reason },
    }),

  // Emergency Retrieval & Edge Cache
  retrieveRecord: ({ record_id, is_emergency = true, department = 'Emergency', reason = 'Clinical lookup' }) =>
    request('/retrieval/request', {
      method: 'POST',
      body: { record_id, is_emergency, department, reason },
    }),
  prefetchRecords: (recordIds, reason) =>
    request('/retrieval/prefetch', {
      method: 'POST',
      body: { record_ids: recordIds, reason },
    }),
  retrievalMetrics: () => request('/retrieval/metrics'),
  listRetrievalJobs: (is_emergency) => request('/retrieval/jobs', { params: { is_emergency } }),

  // AWS Step Functions Orchestration
  triggerPipeline: (inputData) =>
    request('/orchestration/trigger-pipeline', {
      method: 'POST',
      body: inputData || {},
    }),
  listPipelineExecutions: () => request('/orchestration/executions'),
  getExecution: (id) => request(`/orchestration/executions/${encodeURIComponent(id)}`),
};

// Helper: runs backup and regenerates schedule
export async function runBackups(recordId) {
  const jobs = await api.triggerBackup(recordId);
  await api.generateSchedule().catch(() => {});
  return jobs;
}
