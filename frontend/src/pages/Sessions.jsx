// Sessions History - View all parking sessions
import React from 'react';
import { api } from '../api.js';
import { useNavigate } from 'react-router-dom';
import Card from '../components/common/Card';
import Button from '../components/common/Button';

export default function Sessions() {
    const navigate = useNavigate();
    const [sessions, setSessions] = React.useState([]);
    const [loading, setLoading] = React.useState(true);
    const [error, setError] = React.useState('');
    const [filters, setFilters] = React.useState({
        status: '',
        plate: ''
    });

    React.useEffect(() => {
        loadSessions();
    }, [filters]);

    const loadSessions = async () => {
        setLoading(true);
        try {
            const params = new URLSearchParams();
            if (filters.status) params.append('status', filters.status);
            if (filters.plate) params.append('plate', filters.plate);
            
            const data = await api(`/api/sessions?${params.toString()}`);
            setSessions(data);
            setError('');
        } catch (e) {
            setError(e.message);
        } finally {
            setLoading(false);
        }
    };

    const handleFilterChange = (key, value) => {
        setFilters({ ...filters, [key]: value });
    };

    const getStatusColor = (status) => {
        const colors = {
            open: 'var(--color-info)',
            paid: 'var(--color-success)',
            cancelled: 'var(--color-danger)'
        };
        return colors[status] || 'var(--color-secondary)';
    };

    return (
        <div className="flex flex-col gap-4">
            <Card style={{ padding: 'var(--spacing-4)' }}>
                <h1 style={{ fontSize: 'var(--font-size-2xl)', fontWeight: 'bold', marginBottom: 'var(--spacing-2)' }}>
                    Histórico de Sessões
                </h1>
                <p style={{ color: 'var(--color-text-secondary)', fontSize: 'var(--font-size-sm)' }}>
                    Visualize todas as sessões de estacionamento
                </p>
            </Card>

            {/* Filters */}
            <Card>
                <h3 style={{ fontSize: 'var(--font-size-lg)', fontWeight: '600', marginBottom: 'var(--spacing-4)' }}>
                    Filtros
                </h3>
                <div style={{ 
                    display: 'grid', 
                    gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', 
                    gap: 'var(--spacing-3)' 
                }}>
                    <div>
                        <label style={{ 
                            display: 'block', 
                            marginBottom: 'var(--spacing-2)', 
                            fontSize: 'var(--font-size-sm)', 
                            color: 'var(--color-text-secondary)' 
                        }}>
                            Estado
                        </label>
                        <select
                            className="input"
                            style={{ width: '100%' }}
                            value={filters.status}
                            onChange={(e) => handleFilterChange('status', e.target.value)}
                        >
                            <option value="">Todos</option>
                            <option value="open">Aberto</option>
                            <option value="paid">Pago</option>
                            <option value="cancelled">Cancelado</option>
                        </select>
                    </div>
                    <div>
                        <label style={{ 
                            display: 'block', 
                            marginBottom: 'var(--spacing-2)', 
                            fontSize: 'var(--font-size-sm)', 
                            color: 'var(--color-text-secondary)' 
                        }}>
                            Matrícula
                        </label>
                        <input
                            className="input"
                            style={{ width: '100%' }}
                            type="text"
                            placeholder="AA-00-BB"
                            value={filters.plate}
                            onChange={(e) => handleFilterChange('plate', e.target.value)}
                        />
                    </div>
                    <div style={{ display: 'flex', alignItems: 'flex-end' }}>
                        <Button 
                            onClick={loadSessions}
                            style={{ width: '100%' }}
                        >
                            🔍 Pesquisar
                        </Button>
                    </div>
                </div>
            </Card>

            {/* Sessions Table */}
            <Card>
                <h3 style={{ fontSize: 'var(--font-size-lg)', fontWeight: '600', marginBottom: 'var(--spacing-4)' }}>
                    Sessões ({sessions.length})
                </h3>

                {loading && (
                    <p style={{ color: 'var(--color-text-secondary)', textAlign: 'center', padding: 'var(--spacing-4)' }}>
                        A carregar...
                    </p>
                )}

                {error && (
                    <p style={{ color: 'var(--color-danger)', textAlign: 'center', padding: 'var(--spacing-4)' }}>
                        {error}
                    </p>
                )}

                {!loading && !error && sessions.length === 0 && (
                    <p style={{ color: 'var(--color-text-secondary)', textAlign: 'center', padding: 'var(--spacing-4)' }}>
                        Nenhuma sessão encontrada.
                    </p>
                )}

                {!loading && !error && sessions.length > 0 && (
                    <div style={{ overflowX: 'auto' }}>
                        <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
                            <thead>
                                <tr style={{ borderBottom: '2px solid var(--color-surface-hover)' }}>
                                    <th style={{ padding: 'var(--spacing-2)', fontWeight: '600' }}>ID</th>
                                    <th style={{ padding: 'var(--spacing-2)', fontWeight: '600' }}>Matrícula</th>
                                    <th style={{ padding: 'var(--spacing-2)', fontWeight: '600' }}>Câmera</th>
                                    <th style={{ padding: 'var(--spacing-2)', fontWeight: '600' }}>Entrada</th>
                                    <th style={{ padding: 'var(--spacing-2)', fontWeight: '600' }}>Saída</th>
                                    <th style={{ padding: 'var(--spacing-2)', fontWeight: '600' }}>Valor</th>
                                    <th style={{ padding: 'var(--spacing-2)', fontWeight: '600' }}>Pago</th>
                                    <th style={{ padding: 'var(--spacing-2)', fontWeight: '600' }}>Estado</th>
                                    <th style={{ padding: 'var(--spacing-2)', fontWeight: '600' }}>Ações</th>
                                </tr>
                            </thead>
                            <tbody>
                                {sessions.map((session) => (
                                    <tr key={session.id} style={{ borderBottom: '1px solid var(--color-surface-hover)' }}>
                                        <td style={{ padding: 'var(--spacing-2)' }}>{session.id}</td>
                                        <td style={{ padding: 'var(--spacing-2)', fontWeight: 'bold' }}>{session.plate}</td>
                                        <td style={{ padding: 'var(--spacing-2)', fontSize: 'var(--font-size-sm)', color: 'var(--color-text-secondary)' }}>
                                            {session.camera_id}
                                        </td>
                                        <td style={{ padding: 'var(--spacing-2)', fontSize: 'var(--font-size-sm)' }}>
                                            {session.entry_time ? new Date(session.entry_time).toLocaleString('pt-PT') : '-'}
                                        </td>
                                        <td style={{ padding: 'var(--spacing-2)', fontSize: 'var(--font-size-sm)' }}>
                                            {session.exit_time ? new Date(session.exit_time).toLocaleString('pt-PT') : '-'}
                                        </td>
                                        <td style={{ padding: 'var(--spacing-2)', fontWeight: 'bold' }}>
                                            €{session.amount_due.toFixed(2)}
                                        </td>
                                        <td style={{ padding: 'var(--spacing-2)' }}>
                                            €{session.amount_paid.toFixed(2)}
                                        </td>
                                        <td style={{ padding: 'var(--spacing-2)' }}>
                                            <span style={{
                                                backgroundColor: getStatusColor(session.status),
                                                padding: '0.25rem 0.5rem',
                                                borderRadius: 'var(--border-radius-sm)',
                                                fontSize: 'var(--font-size-xs)',
                                                fontWeight: 'bold',
                                                textTransform: 'uppercase'
                                            }}>
                                                {session.status}
                                            </span>
                                        </td>
                                        <td style={{ padding: 'var(--spacing-2)' }}>
                                            {session.status === 'open' && session.amount_due > 0 && (
                                                <Button
                                                    variant="ghost"
                                                    size="sm"
                                                    onClick={() => navigate(`/payment/${session.id}`)}
                                                >
                                                    💳 Pagar
                                                </Button>
                                            )}
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
