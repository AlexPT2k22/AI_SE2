// Sessions History - View all parking sessions
import React from 'react';
import { api } from '../api.js';
import Card from '../components/common/Card';
import { useAuth } from '../contexts/AuthContext';

export default function Sessions() {
    const { isAdmin } = useAuth();
    const [sessions, setSessions] = React.useState([]);
    const [loading, setLoading] = React.useState(true);
    const [error, setError] = React.useState('');
    const [filters, setFilters] = React.useState({
        status: ''
    });

    React.useEffect(() => {
        loadSessions();
    }, [filters]);

    const loadSessions = async () => {
        setLoading(true);
        try {
            const params = new URLSearchParams();
            if (filters.status) params.append('status', filters.status);

            // Admin vê todas as sessões, cliente vê apenas as suas
            const endpoint = isAdmin() ? '/api/sessions' : '/api/user/sessions';
            const data = await api(`${endpoint}?${params.toString()}`);

            // Normalizar resposta (admin retorna array, user retorna {sessions: []})
            const sessionsList = Array.isArray(data) ? data : (data.sessions || []);
            setSessions(sessionsList);
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
        return colors[status] || 'var(--color-danger)';
    };

    return (
        <div style={{ padding: 'var(--spacing-4)', maxWidth: '1200px', margin: '0 auto' }}>
            <div className="flex flex-col" style={{ gap: 'var(--spacing-6)' }}>
                <Card style={{ padding: 'var(--spacing-6)' }}>
                    <h1 style={{ fontSize: 'var(--font-size-2xl)', fontWeight: 'bold', marginBottom: 'var(--spacing-2)' }}>
                        Session History
                    </h1>
                    <p style={{ color: 'var(--color-text-secondary)', fontSize: 'var(--font-size-sm)' }}>
                        View all your parking sessions
                    </p>
                </Card>

                {/* Filters */}
                <Card style={{ padding: 'var(--spacing-6)' }}>
                    <h3 style={{ fontSize: 'var(--font-size-lg)', fontWeight: '600', marginBottom: 'var(--spacing-4)' }}>
                        Filters
                    </h3>
                    <div style={{
                        display: 'grid',
                        gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
                        gap: 'var(--spacing-4)'
                    }}>
                        <div>
                            <label style={{
                                display: 'block',
                                marginBottom: 'var(--spacing-2)',
                                fontSize: 'var(--font-size-sm)',
                                color: 'var(--color-text-secondary)'
                            }}>
                                Status
                            </label>
                            <select
                                className="input"
                                style={{ width: '100%' }}
                                value={filters.status}
                                onChange={(e) => handleFilterChange('status', e.target.value)}
                            >
                                <option value="">All</option>
                                <option value="open">Open</option>
                                <option value="paid">Paid</option>
                                <option value="cancelled">Cancelled</option>
                            </select>
                        </div>
                    </div>
                </Card>

                {/* Sessions Table */}
                <Card style={{ padding: 'var(--spacing-6)' }}>
                    <h3 style={{ fontSize: 'var(--font-size-lg)', fontWeight: '600', marginBottom: 'var(--spacing-4)' }}>
                        Sessions ({sessions.length})
                    </h3>

                    {loading && (
                        <p style={{ color: 'var(--color-text-secondary)', textAlign: 'center', padding: 'var(--spacing-4)' }}>
                            Loading...
                        </p>
                    )}

                    {error && (
                        <p style={{ color: 'var(--color-danger)', textAlign: 'center', padding: 'var(--spacing-4)' }}>
                            {error}
                        </p>
                    )}

                    {!loading && !error && sessions.length === 0 && (
                        <p style={{ color: 'var(--color-text-secondary)', textAlign: 'center', padding: 'var(--spacing-4)' }}>
                            No sessions found.
                        </p>
                    )}

                    {!loading && !error && sessions.length > 0 && (
                        <div style={{ overflowX: 'auto' }}>
                            <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
                                <thead>
                                    <tr style={{ borderBottom: '2px solid var(--color-surface-hover)' }}>
                                        <th style={{ padding: 'var(--spacing-3)', fontWeight: '600' }}>License Plate</th>
                                        <th style={{ padding: 'var(--spacing-3)', fontWeight: '600' }}>Spot</th>
                                        <th style={{ padding: 'var(--spacing-3)', fontWeight: '600' }}>Entry</th>
                                        <th style={{ padding: 'var(--spacing-3)', fontWeight: '600' }}>Exit</th>
                                        <th style={{ padding: 'var(--spacing-3)', fontWeight: '600' }}>Amount</th>
                                        <th style={{ padding: 'var(--spacing-3)', fontWeight: '600' }}>Paid</th>
                                        <th style={{ padding: 'var(--spacing-3)', fontWeight: '600' }}>Status</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {sessions.map((session) => (
                                        <tr key={session.id} style={{ borderBottom: '1px solid var(--color-surface-hover)' }}>
                                            <td style={{ padding: 'var(--spacing-3)', fontWeight: 'bold' }}>{session.plate}</td>
                                            <td style={{ padding: 'var(--spacing-3)' }}>
                                                <span style={{
                                                    backgroundColor: 'var(--color-surface)',
                                                    padding: '0.25rem 0.5rem',
                                                    borderRadius: 'var(--border-radius-sm)',
                                                    fontWeight: '600'
                                                }}>
                                                    {session.spot || '-'}
                                                </span>
                                            </td>
                                            <td style={{ padding: 'var(--spacing-3)', fontSize: 'var(--font-size-sm)' }}>
                                                {session.entry_time ? new Date(session.entry_time).toLocaleString() : '-'}
                                            </td>
                                            <td style={{ padding: 'var(--spacing-3)', fontSize: 'var(--font-size-sm)' }}>
                                                {session.exit_time ? new Date(session.exit_time).toLocaleString() : '-'}
                                            </td>
                                            <td style={{ padding: 'var(--spacing-3)', fontWeight: 'bold' }}>
                                                €{session.amount_due?.toFixed(2) || '0.00'}
                                            </td>
                                            <td style={{ padding: 'var(--spacing-3)' }}>
                                                €{session.amount_paid?.toFixed(2) || '0.00'}
                                            </td>
                                            <td style={{ padding: 'var(--spacing-3)' }}>
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
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    )}
                </Card>
            </div>
        </div>
    );
}
