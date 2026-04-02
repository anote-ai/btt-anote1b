import axios from 'axios';

/**
 * API origin (no trailing slash).
 * - If VITE_API_URL is set → use it (must match the port where FastAPI listens).
 * - In dev, if unset → '' so requests stay on the Vite origin and /api is proxied (see vite.config.js).
 * - In production builds, if unset → http://localhost:8000 (override for deployed API).
 */
export function getApiBaseUrl() {
  const raw = import.meta.env.VITE_API_URL;
  const trimmed = typeof raw === 'string' ? raw.trim() : '';
  if (trimmed) return trimmed.replace(/\/$/, '');
  if (import.meta.env.DEV) return '';
  return 'http://localhost:8000'.replace(/\/$/, '');
}

const API_BASE_URL = getApiBaseUrl();

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: import.meta.env.VITE_API_WITH_CREDENTIALS === 'true',
});

api.interceptors.request.use((config) => {
  if (typeof localStorage === 'undefined') return config;
  const token =
    localStorage.getItem('accessToken') || localStorage.getItem('sessionToken');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Dataset APIs
export const getDatasets = async (taskType = null) => {
  const params = taskType ? { task_type: taskType } : {};
  const response = await api.get('/api/datasets', { params });
  return response.data;
};

export const getDataset = async (datasetId) => {
  const response = await api.get(`/api/datasets/${datasetId}`);
  return response.data;
};

export const getDatasetQuestions = async (datasetId) => {
  const response = await api.get(`/api/datasets/${datasetId}/questions`);
  return response.data;
};

export const createDataset = async (datasetData) => {
  const response = await api.post('/api/datasets', datasetData);
  return response.data;
};

// Submission APIs
export const submitPredictions = async (submissionData) => {
  const response = await api.post('/api/submissions', submissionData);
  return response.data;
};

export const getSubmission = async (submissionId) => {
  const response = await api.get(`/api/submissions/${submissionId}`);
  return response.data;
};

export const getSubmissions = async (filters = {}) => {
  const response = await api.get('/api/submissions', { params: filters });
  return response.data;
};

// Leaderboard APIs
export const getAllLeaderboards = async (taskType = null) => {
  const params = taskType ? { task_type: taskType } : {};
  const response = await api.get('/api/leaderboard', { params });
  return response.data;
};

export const getLeaderboard = async (datasetId, includeInternal = true) => {
  const response = await api.get(`/api/leaderboard/${datasetId}`, {
    params: { include_internal: includeInternal }
  });
  return response.data;
};

// Admin/Data Management APIs
export const seedSampleData = async () => {
  const response = await api.post('/api/admin/seed-data');
  return response.data;
};

export const importFromHuggingFace = async (datasetName, config = 'default', split = 'test', numSamples = 100) => {
  const response = await api.post('/api/admin/import-huggingface', null, {
    params: { dataset_name: datasetName, config, split, num_samples: numSamples }
  });
  return response.data;
};

export const getAdminCacheStats = async () => {
  const response = await api.get('/api/admin/cache-stats');
  return response.data;
};

/** @param {string | null | undefined} datasetId omit or null to clear all leaderboard cache */
export const clearAdminCache = async (datasetId) => {
  const params = datasetId ? { dataset_id: datasetId } : {};
  const response = await api.post('/api/admin/clear-cache', null, { params });
  return response.data;
};

// Health check
export const healthCheck = async () => {
  const response = await api.get('/health');
  return response.data;
};

// Metrics info APIs
export const getMetricInfo = async (metricName) => {
  const response = await api.get(`/api/metrics/${metricName}`);
  return response.data;
};

export const getTaskMetrics = async (taskType) => {
  const response = await api.get(`/api/metrics/task/${taskType}`);
  return response.data;
};

export default api;

