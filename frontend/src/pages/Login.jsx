// Login page - AI_SE2 session-based authentication
import React from 'react';
import { api } from '../api.js';
import { useNavigate } from 'react-router-dom';
import Card from '../components/common/Card';
import Button from '../components/common/Button';
import Input from '../components/common/Input';

export default function Login() {
    const navigate = useNavigate();
    const [name, setName] = React.useState('');
    const [plate, setPlate] = React.useState('');
    const [isRegister, setIsRegister] = React.useState(false);
    const [msg, setMsg] = React.useState('');
    const [err, setErr] = React.useState('');
    const [loading, setLoading] = React.useState(false);
    const [user, setUser] = React.useState(null);

    // Check if user is already logged in
    React.useEffect(() => {
        const checkAuth = async () => {
            try {
                const data = await api('/api/auth/me');
                setUser(data);
            } catch (e) {
                // Not logged in
            }
        };
        checkAuth();
    }, []);

    const submit = async (e) => {
        e.preventDefault();
        setMsg('');
        setErr('');
        setLoading(true);
        try {
            const endpoint = isRegister ? '/api/auth/register' : '/api/auth/login';
            const body = { name, plate };

            const data = await api(endpoint, {
                method: 'POST',
                body: JSON.stringify(body),
            });
            setMsg(`Bem-vindo, ${data.name}!`);
            setUser(data);
            setTimeout(() => navigate('/reservar'), 1000);
        } catch (e) {
            setErr(e.message);
        } finally {
            setLoading(false);
        }
    };

    const logout = async () => {
        try {
            await api('/api/auth/logout', { method: 'POST' });
            setUser(null);
            setMsg('Logout efetuado com sucesso.');
        } catch (e) {
            setErr(e.message);
        }
    };

    if (user) {
        return (
            <Card className="p-4">
                <h2 style={{ fontSize: 'var(--font-size-xl)', fontWeight: 'bold', marginBottom: 'var(--spacing-4)' }}>
                    Sessão Ativa
                </h2>
                <p style={{ color: 'var(--color-text-secondary)', fontSize: 'var(--font-size-sm)' }}>
                    Está autenticado como:
                </p>
                <div style={{ marginTop: 'var(--spacing-2)' }}>
                    <p><strong>Nome:</strong> {user.name}</p>
                    <p><strong>Matrícula:</strong> {user.plate}</p>
                    <Button
                        variant="ghost"
                        onClick={logout}
                        style={{ marginTop: 'var(--spacing-4)', color: 'var(--color-danger)', border: '1px solid var(--color-danger)' }}
                    >
                        Terminar Sessão
                    </Button>
                </div>
            </Card>
        );
    }

    return (
        <Card className="p-4" style={{ maxWidth: '400px', margin: '0 auto' }}>
            <h2 style={{ fontSize: 'var(--font-size-xl)', fontWeight: 'bold', marginBottom: 'var(--spacing-2)' }}>
                {isRegister ? 'Registar' : 'Entrar'}
            </h2>
            <p style={{ color: 'var(--color-text-secondary)', fontSize: 'var(--font-size-sm)', marginBottom: 'var(--spacing-4)' }}>
                {isRegister
                    ? 'Crie uma nova conta com o seu nome e matrícula.'
                    : 'Entre com o seu nome e matrícula.'}
            </p>

            <form onSubmit={submit} className="flex flex-col gap-4">
                <Input
                    label="Nome completo"
                    placeholder="João Silva"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    required
                />

                <Input
                    label="Matrícula"
                    placeholder="AA-00-BB"
                    value={plate}
                    onChange={(e) => setPlate(e.target.value)}
                    required
                />

                <Button disabled={loading} style={{ width: '100%' }}>
                    {loading ? 'A processar…' : isRegister ? 'Registar' : 'Entrar'}
                </Button>

                <div className="text-center">
                    <button
                        type="button"
                        style={{
                            background: 'none',
                            border: 'none',
                            color: 'var(--color-primary)',
                            cursor: 'pointer',
                            textDecoration: 'underline',
                            fontSize: 'var(--font-size-sm)'
                        }}
                        onClick={() => {
                            setIsRegister(!isRegister);
                            setMsg('');
                            setErr('');
                        }}
                    >
                        {isRegister
                            ? 'Já tem conta? Entrar'
                            : 'Não tem conta? Registar'}
                    </button>
                </div>
            </form>

            {msg && <p style={{ color: 'var(--color-success)', marginTop: 'var(--spacing-4)' }}>{msg}</p>}
            {err && <p style={{ color: 'var(--color-danger)', marginTop: 'var(--spacing-4)' }}>{err}</p>}
        </Card>
    );
}
