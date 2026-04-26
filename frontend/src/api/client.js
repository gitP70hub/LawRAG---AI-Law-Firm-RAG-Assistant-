import axios from 'axios';

const api = axios.create({
  // Use a relative base URL so Vite's proxy forwards /api → http://localhost:8000
  // This avoids CORS completely during development.
  baseURL: '/api/v1',
  headers: { 'Content-Type': 'application/json' },
  timeout: 180_000, // LLM calls can be slow (up to 3 min)
});

// ── Request interceptor: add timestamp for debugging ───────────────────────────
api.interceptors.request.use((cfg) => {
  cfg.metadata = { startTime: Date.now() };
  return cfg;
});

// ── Response interceptor: surface errors cleanly ───────────────────────────────
api.interceptors.response.use(
  (res) => res,
  (err) => {
    const detail = err.response?.data?.detail;
    if (detail) err.message = Array.isArray(detail) ? detail.map(d => d.msg).join(', ') : detail;
    return Promise.reject(err);
  }
);

// ── Cases ──────────────────────────────────────────────────────────────────────
export const getCases     = (params = {})     => api.get('/cases/',             { params });
export const getCase      = (id)              => api.get(`/cases/${id}`);
export const createCase   = (body)            => api.post('/cases/', body);
export const updateCase   = (id, body)        => api.patch(`/cases/${id}`, body);
export const deleteCase   = (id)              => api.delete(`/cases/${id}`);
export const updateStatus = (id, status)      => api.put(`/cases/${id}/status`, { status });

// ── Timeline ───────────────────────────────────────────────────────────────────
export const getTimeline   = (id, force = false) =>
  api.get(`/cases/${id}/timeline`, { params: { force_regenerate: force } });
export const clearTimeline = (id)             => api.delete(`/cases/${id}/timeline`);

// ── Documents ─────────────────────────────────────────────────────────────────
export const getDocuments   = (caseId) => api.get('/documents/', { params: { case_id: caseId } });
export const deleteDocument = (docId)  => api.delete(`/documents/${docId}`);
export const uploadDocument = (caseId, file, onProgress) => {
  const fd = new FormData();
  fd.append('case_id', caseId);
  fd.append('file', file);
  return api.post('/upload/', fd, {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress: (e) =>
      onProgress && onProgress(Math.round((e.loaded * 100) / (e.total || 1))),
  });
};

// ── Chat ──────────────────────────────────────────────────────────────────────
export const sendChat   = (body)           => api.post('/chat/', body);
export const getHistory = (caseId, params = {}) => api.get(`/chat/${caseId}`, { params });
export const clearChat  = (caseId)         => api.delete(`/chat/${caseId}`);

// ── Precedent ─────────────────────────────────────────────────────────────────
export const findPrecedents = (body) => api.post('/precedent/', body);

// ── Clause Analyzer ──────────────────────────────────────────────────────────
export const analyzeClauses = (body) => api.post('/clause-analyze/', body);
export const analyzeRawText = (body) => api.post('/clause-analyze/raw-text', body);

export default api;
