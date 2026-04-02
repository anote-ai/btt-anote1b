import React, { useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { getDatasets } from '../services/api';

function normalizeKey(s) {
  return decodeSafe(s)
    .trim()
    .toLowerCase()
    .replace(/[\s_]+/g, '-')
    .replace(/-+/g, '-');
}

function decodeSafe(raw) {
  try {
    return decodeURIComponent(raw);
  } catch {
    return raw;
  }
}

function datasetMatchesParam(paramRaw, datasetName) {
  const param = decodeSafe(paramRaw).trim();
  const name = (datasetName || '').trim();
  if (!param || !name) return false;
  if (param === name) return true;
  const a = param.toLowerCase();
  const b = name.toLowerCase();
  if (a === b) return true;
  if (normalizeKey(paramRaw) === normalizeKey(name)) return true;
  return false;
}

/**
 * Old leaderboard used /dataset/:name (human-readable). New app uses UUID in /leaderboard/:datasetId.
 */
const LegacyDatasetRedirect = () => {
  const { name } = useParams();
  const navigate = useNavigate();
  const [message, setMessage] = useState('Resolving dataset…');
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let cancelled = false;

    const run = async () => {
      try {
        const datasets = await getDatasets();
        if (cancelled) return;
        const match = Array.isArray(datasets)
          ? datasets.find((d) => datasetMatchesParam(name, d.name))
          : null;
        if (match?.id) {
          navigate(`/leaderboard/${match.id}`, { replace: true });
          return;
        }
        setFailed(true);
        setMessage('Dataset not found. It may have moved — browse benchmarks from the home page.');
      } catch {
        if (!cancelled) {
          setFailed(true);
          setMessage('Could not load datasets. Check the API and try again.');
        }
      }
    };

    if (name) run();
    return () => {
      cancelled = true;
    };
  }, [name, navigate]);

  return (
    <div className="min-h-screen bg-gray-900 flex flex-col items-center justify-center gap-4 px-4">
      <p className="text-gray-300 text-center max-w-md">{message}</p>
      {failed ? (
        <Link to="/" className="text-blue-400 hover:text-blue-300">
          All benchmarks
        </Link>
      ) : null}
    </div>
  );
};

export default LegacyDatasetRedirect;
