import React from 'react';
import { useLocation, useNavigate } from 'react-router-dom';

export default function HeaderBar() {
  const location = useLocation();
  const navigate = useNavigate();
  const isHome = location.pathname === '/' || location.pathname === '';

  return (
    <div className="sticky top-0 z-50 bg-gray-800">
      <div className="max-w-7xl mx-auto px-4 h-12 flex items-center justify-between">
        <a href="https://anote.ai" className="flex items-center gap-2" target="_blank" rel="noreferrer">
          <img src="/logo.png" alt="Anote" className="h-7 w-7" />
          <span className="font-semibold text-white">Anote</span>
        </a>
        {!isHome && (
          <button
            aria-label="Close"
            title="Back to Home"
            onClick={() => navigate('/')}
            className="h-8 w-8 flex items-center justify-center rounded-full border border-gray-300 text-gray-600 hover:bg-gray-100"
          >
            ×
          </button>
        )}
      </div>
    </div>
  );
}

