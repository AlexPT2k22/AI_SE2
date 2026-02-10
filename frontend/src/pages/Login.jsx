// Login/Register Page - TugaPark v2.0
// Supports login with email OR license plate + password

import React, { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import Card from '../components/common/Card';
import Button from '../components/common/Button';
import Input from '../components/common/Input';

export default function Login() {
    const navigate = useNavigate();
    const [searchParams] = useSearchParams();
    const { user, login, register, isAuthenticated } = useAuth();

    const [mode, setMode] = useState(searchParams.get('register') ? 'register' : 'login');
    const [loading, setLoading] = useState(false);
    const [message, setMessage] = useState('');
    const [error, setError] = useState('');

    // Campos do formulário
    const [identifier, setIdentifier] = useState(''); // Email ou matrícula (login)
    const [email, setEmail] = useState(''); // Email (registo)
    const [password, setPassword] = useState('');
    const [confirmPassword, setConfirmPassword] = useState('');
    const [fullName, setFullName] = useState('');

    // React to URL changes (e.g., navigating to /login?register=true)
    useEffect(() => {
        const isRegister = searchParams.get('register');
        setMode(isRegister ? 'register' : 'login');
    }, [searchParams]);

    // Redirecionar se já está autenticado
    useEffect(() => {
        if (isAuthenticated()) {
            navigate('/');
        }
    }, [user, navigate, isAuthenticated]);

    const handleSubmit = async (e) => {
        e.preventDefault();
        setMessage('');
        setError('');
        setLoading(true);

        try {
            if (mode === 'register') {
                // Validate passwords
                if (password !== confirmPassword) {
                    throw new Error('Passwords do not match');
                }
                if (password.length < 6) {
                    throw new Error('Password must be at least 6 characters');
                }
                if (!fullName.trim()) {
                    throw new Error('Full name is required');
                }

                await register(email, password, fullName);
                setMessage('Account created successfully! Redirecting...');
            } else {
                // Login
                await login(identifier, password);
                setMessage('Login successful! Redirecting...');
            }

            setTimeout(() => navigate('/'), 1000);
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    const switchMode = () => {
        setMode(mode === 'login' ? 'register' : 'login');
        setError('');
        setMessage('');
    };

    return (
        <div style={{
            display: 'flex',
            justifyContent: 'center',
            alignItems: 'center',
            minHeight: '70vh',
            padding: 'var(--spacing-4)'
        }}>
            <Card style={{ maxWidth: '420px', width: '100%', padding: 'var(--spacing-6)' }}>
                <h2 style={{
                    fontSize: 'var(--font-size-2xl)',
                    fontWeight: 'bold',
                    marginBottom: 'var(--spacing-2)',
                    textAlign: 'center'
                }}>
                    {mode === 'login' ? 'Sign In' : 'Create Account'}
                </h2>

                <p style={{
                    color: 'var(--color-text-secondary)',
                    fontSize: 'var(--font-size-sm)',
                    textAlign: 'center',
                    marginBottom: 'var(--spacing-6)'
                }}>
                    {mode === 'login'
                        ? 'Sign in with your email or license plate'
                        : 'Create your TugaPark account'}
                </p>

                <form onSubmit={handleSubmit} className="flex flex-col gap-4">
                    {mode === 'register' && (
                        <>
                            <Input
                                label="Full Name"
                                placeholder="John Smith"
                                value={fullName}
                                onChange={(e) => setFullName(e.target.value)}
                                required
                            />
                            <Input
                                type="email"
                                label="Email"
                                placeholder="john@example.com"
                                value={email}
                                onChange={(e) => setEmail(e.target.value)}
                                required
                            />
                        </>
                    )}

                    {mode === 'login' && (
                        <Input
                            label="Email or License Plate"
                            placeholder="john@example.com or AA-00-BB"
                            value={identifier}
                            onChange={(e) => setIdentifier(e.target.value)}
                            required
                        />
                    )}

                    <Input
                        type="password"
                        label="Password"
                        placeholder="••••••••"
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        required
                    />

                    {mode === 'register' && (
                        <Input
                            type="password"
                            label="Confirm Password"
                            placeholder="••••••••"
                            value={confirmPassword}
                            onChange={(e) => setConfirmPassword(e.target.value)}
                            required
                        />
                    )}

                    <Button
                        type="submit"
                        disabled={loading}
                        style={{ width: '100%', marginTop: 'var(--spacing-2)' }}
                    >
                        {loading
                            ? 'Processing...'
                            : mode === 'login' ? 'Sign In' : 'Create Account'}
                    </Button>
                </form>

                {/* Messages */}
                {message && (
                    <p style={{
                        color: 'var(--color-success)',
                        marginTop: 'var(--spacing-4)',
                        textAlign: 'center',
                        fontSize: 'var(--font-size-sm)'
                    }}>
                        {message}
                    </p>
                )}
                {error && (
                    <p style={{
                        color: 'var(--color-danger)',
                        marginTop: 'var(--spacing-4)',
                        textAlign: 'center',
                        fontSize: 'var(--font-size-sm)'
                    }}>
                        {error}
                    </p>
                )}

                {/* Switch mode */}
                <div style={{
                    marginTop: 'var(--spacing-6)',
                    textAlign: 'center',
                    borderTop: '1px solid var(--color-border)',
                    paddingTop: 'var(--spacing-4)'
                }}>
                    <button
                        type="button"
                        onClick={switchMode}
                        style={{
                            background: 'none',
                            border: 'none',
                            color: 'var(--color-primary)',
                            cursor: 'pointer',
                            fontSize: 'var(--font-size-sm)'
                        }}
                    >
                        {mode === 'login'
                            ? "Don't have an account? Register"
                            : 'Already have an account? Sign In'}
                    </button>
                </div>

                {/* Info about license plate login */}
                {mode === 'login' && (
                    <p style={{
                        marginTop: 'var(--spacing-4)',
                        fontSize: 'var(--font-size-xs)',
                        color: 'var(--color-text-muted)',
                        textAlign: 'center'
                    }}>
                        You can sign in with your email or a registered vehicle license plate.
                    </p>
                )}
            </Card>
        </div>
    );
}
