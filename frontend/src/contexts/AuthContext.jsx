// Contexto de Autenticação - TugaPark v2.0
// Gere o estado de autenticação JWT globalmente

import React, { createContext, useContext, useState, useEffect } from 'react';
import { api, setAuthToken, getAuthToken, clearAuthToken } from '../api';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
 const [user, setUser] = useState(null);
 const [loading, setLoading] = useState(true);

 // Verificar se há token guardado ao iniciar
 useEffect(() => {
 const checkAuth = async () => {
 const token = getAuthToken();
 if (token) {
 try {
 const data = await api('/api/auth/me');
 setUser(data);
 } catch (e) {
 // Token inválido ou expirado
 clearAuthToken();
 }
 }
 setLoading(false);
 };
 checkAuth();
 }, []);

 // Função de registo
 const register = async (email, password, fullName) => {
 const data = await api('/api/auth/register', {
 method: 'POST',
 body: JSON.stringify({ email, password, full_name: fullName }),
 });
 setAuthToken(data.token);
 setUser(data.user);
 return data.user;
 };

 // Função de login (email ou matrícula + password)
 const login = async (identifier, password) => {
 const data = await api('/api/auth/login', {
 method: 'POST',
 body: JSON.stringify({ identifier, password }),
 });
 setAuthToken(data.token);
 setUser(data.user);
 return data.user;
 };

 // Função de logout
 const logout = () => {
 clearAuthToken();
 setUser(null);
 };

 // Atualizar dados do utilizador
 const refreshUser = async () => {
 try {
 const data = await api('/api/auth/me');
 setUser(data);
 return data;
 } catch (e) {
 logout();
 return null;
 }
 };

 // Verificar se é admin
 const isAdmin = () => user?.role === 'admin';

 // Verificar se está autenticado
 const isAuthenticated = () => !!user;

 const value = {
 user,
 loading,
 register,
 login,
 logout,
 refreshUser,
 isAdmin,
 isAuthenticated,
 };

 return (
 <AuthContext.Provider value={value}>
 {children}
 </AuthContext.Provider>
 );
}

export function useAuth() {
 const context = useContext(AuthContext);
 if (!context) {
 throw new Error('useAuth must be used within an AuthProvider');
 }
 return context;
}

export default AuthContext;
