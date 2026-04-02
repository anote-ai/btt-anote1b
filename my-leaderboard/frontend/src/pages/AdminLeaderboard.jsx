import React, { useCallback, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import HFImporter from '../components/HFImporter';
import {
  clearAdminCache,
  getAdminCacheStats,
  seedSampleData,
} from '../services/api';

function formatApiError(err) {
  const detail = err.response?.data?.detail;
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((item) => (typeof item === 'object' ? item.msg || JSON.stringify(item) : String(item)))
      .join('; ');
  }
  if (detail && typeof detail === 'object' && detail.message) return detail.message;
  return err.message || 'Request failed';
}

const AdminLeaderboard = () => {
  const navigate = useNavigate();
  const [cacheStats, setCacheStats] = useState(null);
  const [cacheLoading, setCacheLoading] = useState(true);
  const [cacheError, setCacheError] = useState(null);

  const [datasetIdForClear, setDatasetIdForClear] = useState('');
  const [actionError, setActionError] = useState(null);
  const [actionSuccess, setActionSuccess] = useState(null);
  const [seedLoading, setSeedLoading] = useState(false);
  const [clearLoading, setClearLoading] = useState(false);

  const loadCacheStats = useCallback(async () => {
    setCacheLoading(true);
    setCacheError(null);
    try {
      const data = await getAdminCacheStats();
      setCacheStats(data);
    } catch (err) {
      setCacheError(formatApiError(err));
      setCacheStats(null);
    } finally {
      setCacheLoading(false);
    }
  }, []);

  useEffect(() => {
    loadCacheStats();
  }, [loadCacheStats]);

  const runSeed = async () => {
    const ok = window.confirm(
      'Load sample datasets and baseline submissions? Existing datasets with the same name are skipped.'
    );
    if (!ok) return;
    setSeedLoading(true);
    setActionError(null);
    setActionSuccess(null);
    try {
      const res = await seedSampleData();
      const d = res.data || {};
      setActionSuccess(
        `${res.message} (${d.datasets_added ?? 0} datasets added, ${d.submissions_added ?? 0} submissions added).`
      );
      await loadCacheStats();
    } catch (err) {
      setActionError(formatApiError(err));
    } finally {
      setSeedLoading(false);
    }
  };

  const runClearCache = async (scope) => {
    const label =
      scope === 'all'
        ? 'Clear all leaderboard cache entries?'
        : `Clear cache for dataset ID "${datasetIdForClear.trim()}"?`;
    if (!window.confirm(label)) return;
    setClearLoading(true);
    setActionError(null);
    setActionSuccess(null);
    try {
      const id = scope === 'dataset' ? datasetIdForClear.trim() : undefined;
      if (scope === 'dataset' && !id) {
        setActionError('Enter a dataset ID to clear cache for that dataset only.');
        setClearLoading(false);
        return;
      }
      const res = await clearAdminCache(scope === 'all' ? null : id);
      setActionSuccess(res.message || 'Cache cleared.');
      if (scope === 'dataset') setDatasetIdForClear('');
      await loadCacheStats();
    } catch (err) {
      setActionError(formatApiError(err));
    } finally {
      setClearLoading(false);
    }
  };

  const onImportSuccess = () => {
    setActionError(null);
    loadCacheStats();
  };

  return (
    <div className="min-h-screen bg-gray-900 py-8 px-3 pb-24">
      <div className="max-w-4xl mx-auto">
        <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
          <button
            type="button"
            onClick={() => navigate('/')}
            className="text-blue-400 hover:text-blue-300"
          >
            ← Back to Leaderboards
          </button>
          <p className="text-xs text-gray-500">
            Internal tools — same routes as legacy <code className="text-gray-400">/leaderboard/admin</code>
          </p>
        </div>

        <h1 className="text-3xl font-bold text-white mb-2">Leaderboard admin</h1>
        <p className="text-gray-400 mb-8 text-sm">
          Seed benchmarks, import from Hugging Face, and manage API cache. Uses{' '}
          <code className="text-gray-300">/api/admin/*</code> on your configured API.
        </p>

        {actionError && (
          <div className="mb-6 p-4 bg-red-900/40 border border-red-700 rounded-lg text-red-100 text-sm">
            {actionError}
          </div>
        )}
        {actionSuccess && (
          <div className="mb-6 p-4 bg-green-900/30 border border-green-700 rounded-lg text-green-100 text-sm">
            {actionSuccess}
          </div>
        )}

        <section className="mb-10 rounded-lg border border-gray-800 bg-gray-950 p-6">
          <h2 className="text-lg font-semibold text-white mb-1">Leaderboard cache</h2>
          <p className="text-gray-400 text-sm mb-4">
            Monitoring and invalidation for cached leaderboard responses.
          </p>
          {cacheLoading ? (
            <p className="text-gray-400 text-sm">Loading stats…</p>
          ) : cacheError ? (
            <p className="text-red-300 text-sm">{cacheError}</p>
          ) : cacheStats ? (
            <ul className="text-sm text-gray-300 space-y-1 mb-4 font-mono">
              {Object.entries(cacheStats).map(([k, v]) => (
                <li key={k}>
                  <span className="text-gray-500">{k}:</span> {String(v)}
                </li>
              ))}
            </ul>
          ) : null}
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              onClick={() => loadCacheStats()}
              disabled={cacheLoading}
              className="px-4 py-2 rounded-md bg-gray-800 text-gray-200 text-sm hover:bg-gray-700 border border-gray-700 disabled:opacity-50"
            >
              Refresh stats
            </button>
            <button
              type="button"
              onClick={() => runClearCache('all')}
              disabled={clearLoading}
              className="px-4 py-2 rounded-md bg-amber-900/50 text-amber-100 text-sm hover:bg-amber-900/70 border border-amber-800 disabled:opacity-50"
            >
              {clearLoading ? 'Working…' : 'Clear all cache'}
            </button>
          </div>
          <div className="mt-4 pt-4 border-t border-gray-800">
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Clear cache for one dataset (ID)
            </label>
            <div className="flex flex-wrap gap-2">
              <input
                type="text"
                value={datasetIdForClear}
                onChange={(e) => setDatasetIdForClear(e.target.value)}
                placeholder="Dataset UUID"
                className="flex-1 min-w-[200px] px-3 py-2 bg-gray-900 border border-gray-700 rounded text-white text-sm focus:outline-none focus:border-blue-500"
              />
              <button
                type="button"
                onClick={() => runClearCache('dataset')}
                disabled={clearLoading || !datasetIdForClear.trim()}
                className="px-4 py-2 rounded-md bg-amber-900/50 text-amber-100 text-sm hover:bg-amber-900/70 border border-amber-800 disabled:opacity-50"
              >
                Clear for this dataset
              </button>
            </div>
          </div>
        </section>

        <section className="mb-10 rounded-lg border border-gray-800 bg-gray-950 p-6">
          <h2 className="text-lg font-semibold text-white mb-1">Sample data</h2>
          <p className="text-gray-400 text-sm mb-4">
            Runs <code className="text-gray-300">POST /api/admin/seed-data</code>: adds built-in sample datasets
            and baseline submissions where names are not already present.
          </p>
          <button
            type="button"
            onClick={runSeed}
            disabled={seedLoading}
            className="px-4 py-2 rounded-md bg-blue-600 text-white text-sm font-medium hover:bg-blue-500 disabled:opacity-50"
          >
            {seedLoading ? 'Seeding…' : 'Load sample data'}
          </button>
        </section>

        <section className="mb-10 rounded-lg border border-gray-800 bg-gray-950 p-6">
          <h2 className="text-lg font-semibold text-white mb-1">Import from Hugging Face</h2>
          <p className="text-gray-400 text-sm mb-4">
            Same as Create Dataset → HF import: <code className="text-gray-300">POST /api/admin/import-huggingface</code>.
          </p>
          <HFImporter onSuccess={onImportSuccess} />
        </section>
      </div>
    </div>
  );
};

export default AdminLeaderboard;
