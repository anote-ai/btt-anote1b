import React from 'react';
import { GoogleLogin } from '@react-oauth/google';
import { getGoogleWebClientId } from '../services/api';

export function googleAuthNotify() {
  window.dispatchEvent(new Event('leaderboard-auth-changed'));
}

/**
 * Google Sign-In → stores ID token in localStorage as googleIdToken.
 */
export default function GoogleSignInButton({
  size = 'medium',
  width,
  className = '',
}) {
  const clientId = getGoogleWebClientId();
  if (!clientId) {
    return (
      <p className="text-amber-400 text-sm">
        Set <code className="text-amber-200">VITE_GOOGLE_CLIENT_ID</code> (or{' '}
        <code className="text-amber-200">VITE_GOOGLE_OAUTH_CLIENT_ID</code>) in{' '}
        <code className="text-amber-200">frontend/.env</code>
      </p>
    );
  }

  return (
    <div
      className={`flex justify-center [&_iframe]:!shadow-none ${className}`}
      style={width ? { width } : undefined}
    >
      <GoogleLogin
        onSuccess={(res) => {
          if (res.credential) {
            localStorage.setItem('googleIdToken', res.credential);
            googleAuthNotify();
          }
        }}
        onError={() => {
          console.warn('Google Sign-In failed');
        }}
        useOneTap={false}
        theme="filled_black"
        size={size}
        text="signin_with"
        shape="rectangular"
      />
    </div>
  );
}
