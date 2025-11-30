import React, { Suspense, lazy } from 'react';
import { Routes, Route } from 'react-router-dom';
import Layout from './components/layout/Layout';
import ProtectedRoute from './components/ProtectedRoute';

// Lazy load pages
const Home = lazy(() => import('./pages/Home'));
const LiveMonitor = lazy(() => import('./pages/LiveMonitor'));
const Reserve = lazy(() => import('./pages/Reserve'));
const Status = lazy(() => import('./pages/Status'));
const Login = lazy(() => import('./pages/Login'));

const LoadingFallback = () => (
    <div className="flex justify-center items-center" style={{ minHeight: '50vh' }}>
        <div className="text-center">
            <p>Carregando...</p>
        </div>
    </div>
);

const App = () => {
    return (
        <Layout>
            <Suspense fallback={<LoadingFallback />}>
                <Routes>
                    <Route path="/" element={<Home />} />
                    <Route path="/live" element={<ProtectedRoute><LiveMonitor /></ProtectedRoute>} />
                    <Route path="/reservar" element={<ProtectedRoute><Reserve /></ProtectedRoute>} />
                    <Route path="/estado" element={<Status />} />
                    <Route path="/login" element={<Login />} />
                </Routes>
            </Suspense>
        </Layout>
    );
};

export default App;
