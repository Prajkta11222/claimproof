import React, { Suspense, lazy } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Layout } from './components/Layout';
import { AuthProvider } from './features/auth/useAuth';
import { AuthGuard } from './features/auth/AuthGuard';

const HomePage = lazy(() =>
  import('./features/incidents/HomePage').then((m) => ({ default: m.HomePage }))
);
const NewIncidentPage = lazy(() =>
  import('./features/incidents/NewIncidentPage').then((m) => ({ default: m.NewIncidentPage }))
);
const IncidentDashboard = lazy(() =>
  import('./features/incidents/IncidentDashboard').then((m) => ({ default: m.IncidentDashboard }))
);
const LoginPage = lazy(() =>
  import('./features/auth/LoginPage').then((m) => ({ default: m.LoginPage }))
);

export function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Suspense
          fallback={
            <div className="min-h-screen flex items-center justify-center bg-slate-50">
              <div className="w-8 h-8 border-3 border-emerald-600 border-t-transparent rounded-full animate-spin"></div>
            </div>
          }
        >
          <Routes>
            <Route path="/login" element={<LoginPage />} />

            <Route
              path="/"
              element={
                <AuthGuard>
                  <Layout />
                </AuthGuard>
              }
            >
              <Route index element={<HomePage />} />
              <Route path="incidents/new" element={<NewIncidentPage />} />
              <Route path="incidents/:id" element={<IncidentDashboard />} />
            </Route>

            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </Suspense>
      </BrowserRouter>
    </AuthProvider>
  );
}
