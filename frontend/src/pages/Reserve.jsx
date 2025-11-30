// Reservation page - AI_SE2 integrated
import React from 'react';
import { api } from '../api.js';
import { useNavigate } from 'react-router-dom';
import Card from '../components/common/Card';
import Button from '../components/common/Button';

export default function Reserve() {
    const navigate = useNavigate();
    const [user, setUser] = React.useState(null);
    const [spots, setSpots] = React.useState({});
    const [reservations, setReservations] = React.useState([]);
    const [selectedSpot, setSelectedSpot] = React.useState('');
    const [hours, setHours] = React.useState(1);
    const [msg, setMsg] = React.useState('');
    const [err, setErr] = React.useState('');
    const [loading, setLoading] = React.useState(false);

    React.useEffect(() => {
        loadUser();
        loadSpots();
        loadReservations();
        const interval = setInterval(() => {
            loadSpots();
            loadReservations();
        }, 5000);
        return () => clearInterval(interval);
    }, []);

    const loadUser = async () => {
        try {
            const data = await api('/api/auth/me');
            setUser(data);
        } catch (e) {
            setUser(null);
        }
    };

    const loadSpots = async () => {
        try {
            const data = await api('/parking');
            setSpots(data);
        } catch (e) {
            console.error('Failed to load spots:', e);
        }
    };

    const loadReservations = async () => {
        try {
            const data = await api('/api/reservations');
            setReservations(data);
        } catch (e) {
            console.error('Failed to load reservations:', e);
        }
    };

    const createReservation = async (e) => {
        e.preventDefault();
        if (!user) {
            setErr('Precisa de estar autenticado para reservar.');
            return;
        }
        setMsg('');
        setErr('');
        setLoading(true);
        try {
            const data = await api('/api/reservations', {
                method: 'POST',
                body: JSON.stringify({ spot: selectedSpot, hours: Number(hours) }),
            });
            setMsg(`Reserva confirmada: ${data.spot} até ${new Date(data.expires_at * 1000).toLocaleString()}`);
            setSelectedSpot('');
            loadSpots();
            loadReservations();
        } catch (e) {
            setErr(e.message);
        } finally {
            setLoading(false);
        }
    };

    const cancelReservation = async (spot) => {
        if (!confirm(`Cancelar reserva de ${spot}?`)) return;
        try {
            await api(`/api/reservations/${spot}`, { method: 'DELETE' });
            setMsg(`Reserva de ${spot} cancelada.`);
            loadSpots();
            loadReservations();
        } catch (e) {
            setErr(e.message);
        }
    };

    if (!user) {
        return (
            <Card className="p-4 text-center">
                <h2 style={{ fontSize: 'var(--font-size-xl)', fontWeight: 'bold', marginBottom: 'var(--spacing-4)' }}>
                    Autenticação Necessária
                </h2>
                <p style={{ color: 'var(--color-text-secondary)', marginBottom: 'var(--spacing-6)' }}>
                    Precisa de estar autenticado para reservar vagas.
                </p>
                <Button onClick={() => navigate('/login')}>
                    Ir para Login
                </Button>
            </Card>
        );
    }

    const availableSpots = Object.keys(spots).filter(
        name => !spots[name].occupied && !spots[name].reserved
    );

    return (
        <div className="flex flex-col gap-4">
            <Card>
                <h2 style={{ fontSize: 'var(--font-size-xl)', fontWeight: 'bold', marginBottom: 'var(--spacing-4)' }}>
                    Reservar Vaga
                </h2>
                <p style={{ color: 'var(--color-text-secondary)', fontSize: 'var(--font-size-sm)', marginBottom: 'var(--spacing-4)' }}>
                    Utilizador: <strong>{user.name}</strong> | Matrícula: <strong>{user.plate}</strong>
                </p>

                {availableSpots.length === 0 ? (
                    <p style={{ color: 'var(--color-warning)', marginTop: 'var(--spacing-4)' }}>
                        Não há vagas disponíveis para reservar neste momento.
                    </p>
                ) : (
                    <form onSubmit={createReservation} className="flex flex-col gap-4 mt-4">
                        <div className="flex gap-4" style={{ flexWrap: 'wrap' }}>
                            <div style={{ flex: 1, minWidth: '200px' }}>
                                <label className="input-label" style={{ marginBottom: 'var(--spacing-2)', display: 'block' }}>Vaga</label>
                                <select
                                    className="input"
                                    style={{ width: '100%' }}
                                    value={selectedSpot}
                                    onChange={(e) => setSelectedSpot(e.target.value)}
                                    required
                                >
                                    <option value="">Selecione uma vaga...</option>
                                    {availableSpots.map((name) => (
                                        <option key={name} value={name}>
                                            {name}
                                        </option>
                                    ))}
                                </select>
                            </div>

                            <div style={{ width: '150px' }}>
                                <label className="input-label" style={{ marginBottom: 'var(--spacing-2)', display: 'block' }}>Duração</label>
                                <select
                                    className="input"
                                    style={{ width: '100%' }}
                                    value={hours}
                                    onChange={(e) => setHours(e.target.value)}
                                >
                                    {[1, 2, 3, 4, 6, 12, 24].map((h) => (
                                        <option key={h} value={h}>{h}h</option>
                                    ))}
                                </select>
                            </div>

                            <div style={{ display: 'flex', alignItems: 'flex-end' }}>
                                <Button disabled={loading || !selectedSpot} style={{ width: '100%' }}>
                                    {loading ? 'A reservar…' : 'Reservar'}
                                </Button>
                            </div>
                        </div>
                    </form>
                )}

                {msg && <p style={{ color: 'var(--color-success)', marginTop: 'var(--spacing-4)' }}>{msg}</p>}
                {err && <p style={{ color: 'var(--color-danger)', marginTop: 'var(--spacing-4)' }}>{err}</p>}
            </Card>

            <Card>
                <h2 style={{ fontSize: 'var(--font-size-xl)', fontWeight: 'bold', marginBottom: 'var(--spacing-4)' }}>
                    Reservas Ativas
                </h2>
                {reservations.length === 0 ? (
                    <p style={{ color: 'var(--color-text-secondary)', fontSize: 'var(--font-size-sm)' }}>
                        Não há reservas ativas.
                    </p>
                ) : (
                    <div style={{ overflowX: 'auto' }}>
                        <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
                            <thead>
                                <tr style={{ borderBottom: '1px solid var(--color-surface-hover)' }}>
                                    <th style={{ padding: 'var(--spacing-2)' }}>Vaga</th>
                                    <th style={{ padding: 'var(--spacing-2)' }}>Matrícula</th>
                                    <th style={{ padding: 'var(--spacing-2)' }}>Expira em</th>
                                    <th style={{ padding: 'var(--spacing-2)' }}>Ações</th>
                                </tr>
                            </thead>
                            <tbody>
                                {reservations.map((res) => (
                                    <tr key={res.spot} style={{ borderBottom: '1px solid var(--color-surface-hover)' }}>
                                        <td style={{ padding: 'var(--spacing-2)' }}>{res.spot}</td>
                                        <td style={{ padding: 'var(--spacing-2)' }}>{res.plate || 'N/A'}</td>
                                        <td style={{ padding: 'var(--spacing-2)' }}>{new Date(res.expires_at * 1000).toLocaleString()}</td>
                                        <td style={{ padding: 'var(--spacing-2)' }}>
                                            <Button
                                                variant="ghost"
                                                size="sm"
                                                onClick={() => cancelReservation(res.spot)}
                                                style={{ color: 'var(--color-danger)' }}
                                            >
                                                Cancelar
                                            </Button>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}
            </Card>
        </div>
    );
}
