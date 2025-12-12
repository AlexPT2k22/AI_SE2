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
                        <div>
                            <label style={{
                                display: 'block',
                                marginBottom: 'var(--spacing-2)',
                                fontSize: 'var(--font-size-sm)',
                                color: 'var(--color-text-secondary)'
                            }}>
                                License Plate
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
                                Search
                            </Button>
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
                                        <th style={{ padding: 'var(--spacing-2)', fontWeight: '600' }}>ID</th>
                                        <th style={{ padding: 'var(--spacing-2)', fontWeight: '600' }}>License Plate</th>
                                        <th style={{ padding: 'var(--spacing-2)', fontWeight: '600' }}>Camera</th>
                                        <th style={{ padding: 'var(--spacing-2)', fontWeight: '600' }}>Entry</th>
                                        <th style={{ padding: 'var(--spacing-2)', fontWeight: '600' }}>Exit</th>
                                        <th style={{ padding: 'var(--spacing-2)', fontWeight: '600' }}>Amount</th>
                                        <th style={{ padding: 'var(--spacing-2)', fontWeight: '600' }}>Paid</th>
                                        <th style={{ padding: 'var(--spacing-2)', fontWeight: '600' }}>Status</th>
                                        <th style={{ padding: 'var(--spacing-2)', fontWeight: '600' }}>Actions</th>
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
                                                {session.entry_time ? new Date(session.entry_time).toLocaleString() : '-'}
                                            </td>
                                            <td style={{ padding: 'var(--spacing-2)', fontSize: 'var(--font-size-sm)' }}>
                                                {session.exit_time ? new Date(session.exit_time).toLocaleString() : '-'}
                                            </td>
                                            <td style={{ padding: 'var(--spacing-2)', fontWeight: 'bold' }}>
                                                €{session.amount_due?.toFixed(2) || '0.00'}
                                            </td>
                                            <td style={{ padding: 'var(--spacing-2)' }}>
                                                €{session.amount_paid?.toFixed(2) || '0.00'}
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
                                                        Pay
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
        </div>
    );
}
