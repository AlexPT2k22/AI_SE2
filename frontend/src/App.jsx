// App.jsx - TugaPark v2.0
// Aplicação principal com rotas e autenticação

import React, { Suspense, lazy } from 'react';
import { Routes, Route } from 'react-router-dom';
import { AuthProvider } from './contexts/AuthContext';
import Layout from './components/layout/Layout';
import ProtectedRoute from './components/ProtectedRoute';

// Lazy load pages
const Home = lazy(() => import('./pages/Home'));
const LiveMonitor = lazy(() => import('./pages/LiveMonitor'));
const Reserve = lazy(() => import('./pages/Reserve'));
const Status = lazy(() => import('./pages/Status'));
const Login = lazy(() => import('./pages/Login'));
const Profile = lazy(() => import('./pages/Profile'));
const Admin = lazy(() => import('./pages/Admin'));
const Sessions = lazy(() => import('./pages/Sessions'));
const Payment = lazy(() => import('./pages/Payment'));

const LoadingFallback = () => (
 <div className="flex justify-center items-center" style={{ minHeight: '50vh' }}>
 <div className="text-center">
 <div style={{
 width: '40px',
 height: '40px',
 border: '3px solid var(--color-border)',
 borderTop: '3px solid var(--color-primary)',
 borderRadius: '50%',
 animation: 'spin 1s linear infinite',
 margin: '0 auto 16px'
 }}></div>
 <p>Carregando...</p>
 </div>
 <style>{`
 @keyframes spin {
 0% { transform: rotate(0deg); }
 100% { transform: rotate(360deg); }
 }
 `}</style>
 </div>
);

const App = () => {
 return (
 <AuthProvider>
 <Layout>
 <Suspense fallback={<LoadingFallback />}>
 <Routes>
 {/* Públicas */}
 <Route path="/" element={<Home />} />
 <Route path="/login" element={<Login />} />
 <Route path="/estado" element={<Status />} />

 {/* Protegidas - requer autenticação */}
 <Route path="/perfil" element={<ProtectedRoute><Profile /></ProtectedRoute>} />
 <Route path="/reservar" element={<ProtectedRoute><Reserve /></ProtectedRoute>} />
 <Route path="/sessions" element={<ProtectedRoute><Sessions /></ProtectedRoute>} />
 <Route path="/payment/:sessionId" element={<ProtectedRoute><Payment /></ProtectedRoute>} />

 {/* Protegidas - apenas admin */}
 <Route path="/live" element={<ProtectedRoute adminOnly><LiveMonitor /></ProtectedRoute>} />
 <Route path="/admin" element={<ProtectedRoute adminOnly><Admin /></ProtectedRoute>} />
 </Routes>
 </Suspense>
 </Layout>
 </AuthProvider>
 );
};

export default App;
