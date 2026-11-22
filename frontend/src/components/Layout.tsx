import React from 'react';
import { Outlet, Link, useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { LanguageSwitcher } from './LanguageSwitcher';
import { useAuth } from '../features/auth/authContext';
import { LogOut, Home, PlusCircle } from 'lucide-react';

export function Layout() {
  const { t } = useTranslation();
  const { signOut } = useAuth();
  const navigate = useNavigate();

  const handleLogout = async () => {
    await signOut();
    navigate('/login');
  };

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col font-sans text-gray-900 antialiased">
      {/* Header */}
      <header className="sticky top-0 z-40 bg-white/95 backdrop-blur border-b border-gray-200/80 px-4 py-2.5 sm:px-6">
        <div className="max-w-2xl mx-auto flex items-center justify-between gap-2">
          <Link to="/" className="flex items-center gap-2.5 group">
            <div className="w-8 h-8 rounded-lg bg-emerald-600 flex items-center justify-center text-white font-bold text-sm shadow-xs group-hover:bg-emerald-700 transition-colors">
              CP
            </div>
            <div>
              <span className="font-bold text-base text-gray-900 tracking-tight leading-tight block">
                ClaimProof
              </span>
              <span className="text-[10px] text-gray-500 hidden sm:block">
                72h Evidence Companion
              </span>
            </div>
          </Link>

          <div className="flex items-center gap-2">
            <LanguageSwitcher />
            <button
              onClick={handleLogout}
              title={t('auth.logout', 'Log out')}
              aria-label={t('auth.logout', 'Log out')}
              className="min-h-[40px] min-w-[40px] p-2 text-gray-500 hover:text-gray-800 hover:bg-gray-100 rounded-xl transition-colors inline-flex items-center justify-center"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        </div>
      </header>

      {/* Main content */}
      <main className="flex-1 max-w-2xl w-full mx-auto p-4 sm:p-6 pb-20">
        <Outlet />
      </main>

      {/* Mobile Bottom Navigation Bar */}
      <nav className="fixed bottom-0 inset-x-0 bg-white border-t border-gray-200 z-30 px-4 py-1.5 flex justify-around items-center max-w-2xl mx-auto sm:hidden">
        <Link
          to="/"
          className="flex flex-col items-center py-1 px-3 text-xs font-medium text-gray-600 hover:text-emerald-600"
        >
          <Home className="w-5 h-5 mb-0.5" />
          <span>{t('home.title')}</span>
        </Link>
        <Link
          to="/incidents/new"
          className="flex flex-col items-center py-1 px-3 text-xs font-medium text-emerald-700 hover:text-emerald-800"
        >
          <PlusCircle className="w-5 h-5 mb-0.5 text-emerald-600" />
          <span>{t('home.reportNewLoss')}</span>
        </Link>
      </nav>

      {/* Footer */}
      <footer className="border-t border-gray-200 bg-white/50 text-center py-4 px-4 text-xs text-gray-500">
        <div className="max-w-2xl mx-auto space-y-1">
          <p>{t('common.disclaimer')}</p>
          <p className="text-[11px] text-gray-400">ClaimProof MVP — 2026</p>
        </div>
      </footer>
    </div>
  );
}
