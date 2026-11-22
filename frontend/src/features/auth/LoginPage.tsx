import React, { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useAuth } from './authContext';
import { LanguageSwitcher } from '../../components/LanguageSwitcher';
import { ShieldAlert, ShieldCheck } from 'lucide-react';

export function LoginPage() {
  const { t } = useTranslation();
  const { signIn, signUp } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const [isSignUp, setIsSignUp] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [consentAgreed, setConsentAgreed] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  const [successMessage, setSuccessMessage] = useState('');
  const [loading, setLoading] = useState(false);

  const from = (location.state as { from?: { pathname: string } })?.from?.pathname || '/';

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage('');
    setSuccessMessage('');

    if (isSignUp && !consentAgreed) {
      setErrorMessage(t('auth.consentRequired'));
      return;
    }

    setLoading(true);
    try {
      if (isSignUp) {
        const { error } = await signUp(email, password);
        if (error) {
          setErrorMessage(error.message || t('auth.signupFailed'));
        } else {
          setSuccessMessage(t('auth.signupSuccess'));
        }
      } else {
        const { error } = await signIn(email, password);
        if (error) {
          setErrorMessage(error.message || t('auth.loginFailed'));
        } else {
          navigate(from, { replace: true });
        }
      }
    } catch {
      setErrorMessage(t('common.error'));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col justify-center py-8 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full mx-auto space-y-6">
        {/* Top Header */}
        <div className="flex flex-col items-center">
          <div className="w-12 h-12 bg-emerald-600 rounded-xl flex items-center justify-center text-white font-bold text-2xl shadow-md mb-2">
            CP
          </div>
          <h1 className="text-2xl font-bold text-gray-900 tracking-tight">ClaimProof</h1>
          <p className="text-xs text-gray-500 mt-1">72 Hours to Prove Your Loss</p>
          <div className="mt-4">
            <LanguageSwitcher />
          </div>
        </div>

        {/* Card */}
        <div className="bg-white py-6 px-6 sm:px-8 shadow-sm rounded-2xl border border-gray-100">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">
            {isSignUp ? t('auth.signup') : t('auth.login')}
          </h2>

          {errorMessage && (
            <div className="mb-4 p-3 bg-red-50 border border-red-200 text-red-700 rounded-xl text-sm flex items-start gap-2">
              <ShieldAlert className="w-5 h-5 shrink-0 text-red-500" />
              <span>{errorMessage}</span>
            </div>
          )}

          {successMessage && (
            <div className="mb-4 p-3 bg-emerald-50 border border-emerald-200 text-emerald-700 rounded-xl text-sm flex items-start gap-2">
              <ShieldCheck className="w-5 h-5 shrink-0 text-emerald-500" />
              <span>{successMessage}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                {t('auth.email')}
              </label>
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full px-3 py-2.5 rounded-xl border border-gray-300 shadow-sm focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 text-sm"
                placeholder="farmer@example.com"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                {t('auth.password')}
              </label>
              <input
                type="password"
                required
                minLength={6}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full px-3 py-2.5 rounded-xl border border-gray-300 shadow-sm focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 text-sm"
                placeholder="••••••••"
              />
            </div>

            {isSignUp && (
              <div className="bg-emerald-50/60 p-3 rounded-xl border border-emerald-100 space-y-2">
                <p className="text-xs text-gray-700 leading-relaxed">
                  {t('auth.consentText')}
                </p>
                <label className="flex items-start gap-2 pt-1 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={consentAgreed}
                    onChange={(e) => setConsentAgreed(e.target.checked)}
                    className="mt-0.5 h-4 w-4 rounded border-gray-300 text-emerald-600 focus:ring-emerald-500"
                  />
                  <span className="text-xs font-semibold text-emerald-900">
                    {t('auth.consentCheckbox')}
                  </span>
                </label>
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full min-h-[44px] py-2.5 px-4 border border-transparent rounded-xl shadow-sm text-sm font-medium text-white bg-emerald-600 hover:bg-emerald-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-emerald-500 transition-colors disabled:opacity-50"
            >
              {loading
                ? t('common.loading')
                : isSignUp
                ? t('auth.signupButton')
                : t('auth.loginButton')}
            </button>
          </form>

          <div className="mt-5 text-center">
            <button
              type="button"
              onClick={() => {
                setIsSignUp(!isSignUp);
                setErrorMessage('');
                setSuccessMessage('');
              }}
              className="text-xs text-emerald-700 hover:text-emerald-800 font-medium min-h-[44px] inline-flex items-center"
            >
              {isSignUp ? t('auth.switchToLogin') : t('auth.switchToSignup')}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
