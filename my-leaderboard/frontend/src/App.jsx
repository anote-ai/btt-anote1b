import React, { useCallback, useEffect, useState } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate, Link } from 'react-router-dom';
import Home from './pages/Home';
import CreateDataset from './pages/CreateDataset';
import Submit from './pages/Submit';
import DomainBenchmarks from './pages/DomainBenchmarks';
import SubmissionHistory from './pages/SubmissionHistory';
import DatasetLeaderboard from './pages/DatasetLeaderboard';
import LegacyDatasetRedirect from './pages/LegacyDatasetRedirect';
import AdminLeaderboard from './pages/AdminLeaderboard';
import Docs from './pages/Docs';
import Login from './pages/Login';
import NavAuth from './components/NavAuth';
import { getApiBaseUrl, getAnoteSignInUrl, getMe } from './services/api';

const API_BASE_URL = getApiBaseUrl();
const ANOTE_SIGNIN_URL = getAnoteSignInUrl();

function App() {
  const [me, setMe] = useState(null);

  const loadMe = useCallback(() => {
    getMe()
      .then(setMe)
      .catch(() => setMe({ authenticated: false, auth_mode: 'unknown' }));
  }, []);

  useEffect(() => {
    loadMe();
  }, [loadMe]);

  useEffect(() => {
    const onAuth = () => loadMe();
    window.addEventListener('leaderboard-auth-changed', onAuth);
    return () => window.removeEventListener('leaderboard-auth-changed', onAuth);
  }, [loadMe]);

  return (
    <Router>
      <div className="min-h-screen bg-gray-900">
        {/* Navigation */}
        <nav className="bg-gray-950 border-b border-gray-800">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex justify-between items-center h-16">
              <div className="flex items-center space-x-3">
                <Link to="/" className="flex items-center space-x-3">
                  <img 
                    src="/logo.png" 
                    alt="Anote Logo" 
                    className="h-8 w-8 object-contain"
                  />
                  <span className="text-white text-xl font-semibold">Anote Leaderboard</span>
                </Link>
              </div>
              
              <div className="flex space-x-3 md:space-x-4">
                <Link
                  to="/"
                  className="text-gray-300 hover:text-white px-3 py-2 rounded-md text-sm font-medium transition-colors"
                >
                  All Benchmarks
                </Link>
                <Link
                  to="/domains"
                  className="text-gray-300 hover:text-white px-3 py-2 rounded-md text-sm font-medium transition-colors"
                >
                  Domain-Specific
                </Link>
                <Link
                  to="/history"
                  className="hidden sm:inline-block text-gray-300 hover:text-white px-3 py-2 rounded-md text-sm font-medium transition-colors"
                >
                  Submission History
                </Link>
                <Link
                  to="/create-dataset"
                  className="text-gray-300 hover:text-white px-3 py-2 rounded-md text-sm font-medium transition-colors"
                >
                  Create Dataset
                </Link>
                <Link
                  to="/leaderboard/admin"
                  className="hidden md:inline-block text-gray-500 hover:text-gray-300 px-2 py-2 rounded-md text-xs font-medium transition-colors"
                >
                  Admin
                </Link>
                <NavAuth />
                <Link
                  to="/submit"
                  className="btn-black px-4 py-2 rounded-md text-sm font-medium"
                >
                  Submit Model
                </Link>
                {ANOTE_SIGNIN_URL && (
                  <a
                    href={ANOTE_SIGNIN_URL}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="hidden sm:inline-flex items-center px-3 py-2 rounded-md text-sm font-medium text-gray-400 hover:text-white border border-gray-700"
                  >
                    Open app
                  </a>
                )}
                {(me?.authenticated || me?.auth_mode === 'jwt') && (
                  <span
                    className="hidden lg:inline-block max-w-[12rem] truncate text-xs text-gray-500"
                    title={
                      me.authenticated
                        ? me.email || me.sub || ''
                        : 'Use Log in to sign in with Google'
                    }
                  >
                    {me.authenticated
                      ? me.email || me.sub || 'Signed in'
                      : me.auth_mode === 'jwt'
                        ? 'Not signed in'
                        : ''}
                  </span>
                )}
              </div>
            </div>
          </div>
        </nav>

        {/* Main Content */}
        <Routes>
          <Route path="/login" element={<Login me={me} />} />
          <Route path="/" element={<Home />} />
          <Route path="/domains" element={<DomainBenchmarks />} />
          <Route path="/create-dataset" element={<CreateDataset />} />
          <Route path="/submit" element={<Submit />} />
          <Route path="/history" element={<SubmissionHistory />} />
          {/* Legacy paths (old CRA leaderboard / main app deep links) */}
          <Route path="/leaderboard" element={<Navigate to="/" replace />} />
          <Route path="/submittoleaderboard" element={<Navigate to="/submit" replace />} />
          <Route path="/evaluations" element={<Navigate to="/" replace />} />
          <Route path="/benchmarks" element={<Navigate to="/domains" replace />} />
          <Route path="/leaderboard/admin" element={<AdminLeaderboard />} />
          <Route path="/dataset/:name" element={<LegacyDatasetRedirect />} />
          <Route path="/leaderboard/:datasetId" element={<DatasetLeaderboard />} />
          <Route path="/docs" element={<Docs />} />
        </Routes>

        {/* Footer */}
        <footer className="bg-gray-950 border-t border-gray-800 mt-20">
          <div className="max-w-7xl mx-auto px-4 py-6 text-center text-gray-400 text-sm">
            <p className="mb-2">
              Built by <a href="https://anote.ai" className="text-blue-400 hover:text-blue-300 font-medium">Anote</a>
              {' · '}
              <Link to="/login" className="text-blue-400 hover:text-blue-300">
                Log in
              </Link>
              {ANOTE_SIGNIN_URL && (
                <>
                  {' · '}
                  <a
                    href={ANOTE_SIGNIN_URL}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-blue-400 hover:text-blue-300"
                  >
                    Open app
                  </a>
                </>
              )}
            </p>
            <p>
              <Link 
                to="/docs"
                className="text-blue-400 hover:text-blue-300"
              >
                Documentation
              </Link>
              {' | '}
              <a 
                href={`${API_BASE_URL}/docs`}
                target="_blank" 
                rel="noopener noreferrer"
                className="text-blue-400 hover:text-blue-300"
              >
                API Docs (Interactive)
              </a>
              {' | '}
              <a 
                href="https://github.com/nv78/Autonomous-Intelligence" 
                target="_blank" 
                rel="noopener noreferrer"
                className="text-blue-400 hover:text-blue-300"
              >
                GitHub
              </a>
            </p>
          </div>
        </footer>
      </div>
    </Router>
  );
}

export default App;

