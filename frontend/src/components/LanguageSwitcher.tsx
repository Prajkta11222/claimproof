import React from 'react';
import { useTranslation } from 'react-i18next';
import { Languages } from 'lucide-react';
import { api } from '../lib/api';

const languages = [
  { code: 'en', label: 'English' },
  { code: 'hi', label: 'हिंदी' },
  { code: 'mr', label: 'मराठी' },
] as const;

export function LanguageSwitcher() {
  const { i18n } = useTranslation();

  const handleLanguageChange = async (lng: string) => {
    await i18n.changeLanguage(lng);
    try {
      await api.updateProfile({ preferred_language: lng as 'en' | 'mr' | 'hi' });
    } catch {
      // Profile sync is non-blocking
    }
  };

  return (
    <div className="inline-flex items-center gap-1 bg-white/80 backdrop-blur p-1 rounded-xl border border-gray-200 shadow-xs">
      <Languages className="w-3.5 h-3.5 text-gray-400 ml-1.5" />
      <div className="flex gap-0.5">
        {languages.map(({ code, label }) => {
          const isActive = (i18n.resolvedLanguage || i18n.language) === code;
          return (
            <button
              key={code}
              type="button"
              onClick={() => handleLanguageChange(code)}
              className={`min-h-[36px] px-2.5 py-1 text-xs font-medium rounded-lg transition-colors ${
                isActive
                  ? 'bg-emerald-600 text-white shadow-xs'
                  : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
              }`}
            >
              {label}
            </button>
          );
        })}
      </div>
    </div>
  );
}
