// ProtectedRoute - TugaPark v2.0
// Componente para proteger rotas que requerem autenticação ou admin

import React from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';

export default function ProtectedRoute({ children, adminOnly = false }) {
 const { user, loading, isAdmin, isAuthenticated } = useAuth();

 if (loading) {
 return (
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
 <p>A verificar autenticação...</p>
 </div>
 <style>{`
 @keyframes spin {
 0% { transform: rotate(0deg); }
 100% { transform: rotate(360deg); }
 }
 `}</style>
 </div>
 );
 }

 // Não autenticado -> redirecionar para login
 if (!isAuthenticated()) {
 return <Navigate to="/login" replace />;
 }

 // Rota só para admin, mas não é admin -> mostrar mensagem de acesso negado
 if (adminOnly && !isAdmin()) {
 return (
 <div className="flex justify-center items-center" style={{ minHeight: '50vh' }}>
 <div className="text-center" style={{
 padding: 'var(--spacing-6)',
 backgroundColor: 'var(--color-bg-secondary)',
 borderRadius: 'var(--border-radius-lg)',
 maxWidth: '400px'
 }}>
 <div style={{ fontSize: '48px', marginBottom: 'var(--spacing-4)' }}></div>
 <h2 style={{ fontSize: 'var(--font-size-xl)', fontWeight: 'bold', marginBottom: 'var(--spacing-2)' }}>
 Acesso Restrito
 </h2>
 <p style={{ color: 'var(--color-text-secondary)', marginBottom: 'var(--spacing-4)' }}>
 Esta página é exclusiva para administradores.
 </p>
 <a
 href="/"
 style={{
 color: 'var(--color-primary)',
 textDecoration: 'underline'
 }}
 >
 Voltar à página inicial
 </a>
 </div>
 </div>
 );
 }

 return children;
}
