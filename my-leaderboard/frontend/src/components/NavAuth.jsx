import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';

/**
 * Nav: always show Log in → /login, or Sign out when a Google token is stored.
 */
export default function NavAuth() {
  const [hasGoogleToken, setHasGoogleToken] = useState(
    () => typeof localStorage !== 'undefined' && !!localStorage.getItem('googleIdToken')
  );

  useEffect(() => {
    const sync = () => setHasGoogleToken(!!localStorage.getItem('googleIdToken'));
    window.addEventListener('leaderboard-auth-changed', sync);
    return () => window.removeEventListener('leaderboard-auth-changed', sync);
  }, []);

  if (hasGoogleToken) {
    return (
      <button
        type="button"
        onClick={() => {
          localStorage.removeItem('googleIdToken');
          window.dispatchEvent(new Event('leaderboard-auth-changed'));
        }}
        className="inline-flex items-center px-3 py-2 rounded-md text-sm font-medium text-gray-300 hover:text-white border border-gray-600 hover:border-gray-500"
      >
        Sign out
      </button>
    );
  }

  return (
    <Link
      to="/login"
      className="inline-flex items-center px-3 py-2 rounded-md text-sm font-medium text-blue-300 hover:text-white border border-blue-800/60 hover:border-blue-500/50 bg-blue-950/30"
    >
      Log in
    </Link>
  );
}
