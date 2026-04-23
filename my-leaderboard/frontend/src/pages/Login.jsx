import React, { useEffect } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import GoogleSignInButton from '../components/GoogleSignInButton';
import { getGoogleWebClientId } from '../services/api';

const HAS_GOOGLE = !!getGoogleWebClientId();

export default function Login({ me }) {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const returnTo = searchParams.get('returnTo') || '/';

  useEffect(() => {
    if (me?.authenticated) {
      navigate(returnTo.startsWith('/') ? returnTo : '/', { replace: true });
    }
  }, [me, navigate, returnTo]);

  return (
    <div className="min-h-[70vh] flex flex-col items-center justify-center px-4 py-16">
      <div className="w-full max-w-md rounded-xl border border-gray-800 bg-gray-950 p-8 shadow-xl">
        <h1 className="text-2xl font-bold text-white text-center mb-2">Log in</h1>
        <p className="text-gray-400 text-sm text-center mb-8">
          Sign in with Google to use this leaderboard. Your session stays on this site only.
        </p>

        {HAS_GOOGLE ? (
          <>
            <GoogleSignInButton size="large" className="mb-6" />
            {me?.authenticated && (
              <p className="text-center text-green-400 text-sm mb-4">Signed in — redirecting…</p>
            )}
          </>
        ) : (
          <p className="text-gray-400 text-sm text-center">
            Configure Google Sign-In in <code className="text-gray-300">frontend/.env</code> (
            <code className="text-gray-300">VITE_GOOGLE_CLIENT_ID</code> or{' '}
            <code className="text-gray-300">VITE_GOOGLE_OAUTH_CLIENT_ID</code>).
          </p>
        )}

        <div className="text-center">
          <Link to="/" className="text-blue-400 hover:text-blue-300 text-sm">
            ← Back to benchmarks
          </Link>
        </div>
      </div>
    </div>
  );
}
