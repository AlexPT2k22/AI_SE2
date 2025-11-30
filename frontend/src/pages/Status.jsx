// Status page - shows user's active reservations and unpaid sessions
import React from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../api.js';
import Occupancy from './Occupancy.jsx';
import Card from '../components/common/Card';
import Button from '../components/common/Button';

export default function Status() {
    const navigate = useNavigate();
    const [user, setUser] = React.useState(null);
    const [reservations, setReservations] = React.useState([]);
    const [unpaidSessions, setUnpaidSessions] = React.useState([]);
    const [err, setErr] = React.useState('');
    const [loading, setLoading] = React.useState(true);

    React.useEffect(() => {
        loadUserAndReservations();
        const interval = setInterval(loadUserAndReservations, 5000);
        return () => clearInterval(interval);
    }, []);

    const loadUserAndReservations = async () => {
        try {
            const userData = await api('/api/auth/me');
            setUser(userData);

            // Load reservations
            const reservationsData = await api('/api/reservations');
            const userReservations = reservationsData.filter(
                r => r.plate && userData.plate &&
                    r.plate.replace(/[^A-Z0-9]/gi, '').toUpperCase() ===
                    userData.plate.replace(/[^A-Z0-9]/gi, '').toUpperCase()
            );
            setReservations(userReservations);

            // Load unpaid sessions (sessions with exit but status still open)
            try {
                const allSessions = await api('/api/sessions?status=open');
                console.log('Sessões abertas:', allSessions);
                
                const userUnpaidSessions = allSessions.filter(session => {
                    const sessionPlateNorm = session.plate?.replace(/[^A-Z0-9]/gi, '').toUpperCase();
                    const userPlateNorm = userData.plate?.replace(/[^A-Z0-9]/gi, '').toUpperCase();
                    const hasExit = session.exit_time !== null && session.exit_time !== undefined;
                    const hasDue = session.amount_due > 0;
                    
                    console.log(`Sessão ${session.id}: plate=${sessionPlateNorm}, exit=${hasExit}, due=${hasDue}`);
                    
                    return sessionPlateNorm === userPlateNorm && hasExit && hasDue;
                });
                
                console.log('Sessões não pagas do usuário:', userUnpaidSessions);
                setUnpaidSessions(userUnpaidSessions);
            } catch (sessionErr) {
                console.error('Erro ao carregar sessões:', sessionErr);
                setUnpaidSessions([]);
            }

            setErr('');
        } catch (e) {
            setUser(null);
            setReservations([]);
            setUnpaidSessions([]);
            if (!e.message.includes('401') && !e.message.includes('autenticado')) {
                setErr(e.message);
            }
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="flex flex-col gap-4">
            {/* Unpaid Sessions Section */}
            {user && unpaidSessions.length > 0 && (
                <Card style={{ borderLeft: '4px solid var(--color-warning)' }}>
                    <h2 style={{ fontSize: 'var(--font-size-xl)', fontWeight: 'bold', marginBottom: 'var(--spacing-4)', color: 'var(--color-warning)' }}>
                        ⚠️ Sessões Por Pagar
                    </h2>

                    <p style={{ color: 'var(--color-text-secondary)', fontSize: 'var(--font-size-sm)', marginBottom: 'var(--spacing-4)' }}>
                        Você tem sessões de estacionamento que precisam de pagamento.
                    </p>

                    <div style={{ overflowX: 'auto' }}>
                        <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
                            <thead>
                                <tr style={{ borderBottom: '1px solid var(--color-surface-hover)' }}>
                                    <th style={{ padding: 'var(--spacing-2)' }}>ID</th>
                                    <th style={{ padding: 'var(--spacing-2)' }}>Entrada</th>
                                    <th style={{ padding: 'var(--spacing-2)' }}>Saída</th>
                                    <th style={{ padding: 'var(--spacing-2)' }}>Valor</th>
                                    <th style={{ padding: 'var(--spacing-2)' }}>Ação</th>
                                </tr>
                            </thead>
                            <tbody>
                                {unpaidSessions.map((session) => (
                                    <tr key={session.id} style={{ borderBottom: '1px solid var(--color-surface-hover)' }}>
                                        <td style={{ padding: 'var(--spacing-2)' }}>#{session.id}</td>
                                        <td style={{ padding: 'var(--spacing-2)', fontSize: 'var(--font-size-sm)' }}>
                                            {new Date(session.entry_time).toLocaleString('pt-PT')}
                                        </td>
                                        <td style={{ padding: 'var(--spacing-2)', fontSize: 'var(--font-size-sm)' }}>
                                            {new Date(session.exit_time).toLocaleString('pt-PT')}
                                        </td>
                                        <td style={{ padding: 'var(--spacing-2)', fontWeight: 'bold', color: 'var(--color-warning)' }}>
                                            €{session.amount_due.toFixed(2)}
                                        </td>
                                        <td style={{ padding: 'var(--spacing-2)' }}>
                                            <Button
                                                onClick={() => navigate(`/payment/${session.id}`)}
                                                size="sm"
                                                style={{ backgroundColor: 'var(--color-warning)', color: 'black' }}
                                            >
                                                💳 Pagar Agora
                                            </Button>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </Card>
            )}

            {/* Reservations Section */}
            <Card>
                <h2 style={{ fontSize: 'var(--font-size-xl)', fontWeight: 'bold', marginBottom: 'var(--spacing-4)' }}>
                    Minhas Reservas
                </h2>

                {loading && <p style={{ color: 'var(--color-text-secondary)', fontSize: 'var(--font-size-sm)' }}>A carregar...</p>}

                {!loading && !user && (
                    <p style={{ color: 'var(--color-warning)', fontSize: 'var(--font-size-sm)', marginBottom: 0 }}>
                        Faça login para ver as suas reservas ativas.
                    </p>
                )}

                {!loading && user && reservations.length === 0 && (
                    <p style={{ color: 'var(--color-text-secondary)', fontSize: 'var(--font-size-sm)', marginBottom: 0 }}>
                        Não tem reservas ativas. Utilizador: <strong>{user.name}</strong> ({user.plate})
                    </p>
                )}

                {!loading && user && reservations.length > 0 && (
                    <div>
                        <p style={{ color: 'var(--color-text-secondary)', fontSize: 'var(--font-size-sm)' }}>
                            Utilizador: <strong>{user.name}</strong> ({user.plate})
                        </p>
                        <div style={{ overflowX: 'auto', marginTop: 'var(--spacing-2)' }}>
                            <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
                                <thead>
                                    <tr style={{ borderBottom: '1px solid var(--color-surface-hover)' }}>
                                        <th style={{ padding: 'var(--spacing-2)' }}>Vaga</th>
                                        <th style={{ padding: 'var(--spacing-2)' }}>Expira em</th>
                                        <th style={{ padding: 'var(--spacing-2)' }}>Estado</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {reservations.map((res) => (
                                        <tr key={res.spot} style={{ borderBottom: '1px solid var(--color-surface-hover)' }}>
                                            <td className="font-bold" style={{ padding: 'var(--spacing-2)' }}>{res.spot}</td>
                                            <td style={{ padding: 'var(--spacing-2)' }}>{new Date(res.expires_at * 1000).toLocaleString()}</td>
                                            <td style={{ padding: 'var(--spacing-2)' }}>
                                                <span style={{
                                                    backgroundColor: 'var(--color-primary)',
                                                    padding: '0.25rem 0.5rem',
                                                    borderRadius: 'var(--border-radius-sm)',
                                                    fontSize: '0.75rem',
                                                    fontWeight: 'bold'
                                                }}>
                                                    Ativa
                                                </span>
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    </div>
                )}

                {err && <p style={{ color: 'var(--color-danger)', marginTop: 'var(--spacing-4)' }}>{err}</p>}
            </Card>

            <Occupancy />
        </div>
    );
}
