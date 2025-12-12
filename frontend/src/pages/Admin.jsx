// Admin Dashboard - Statistics and Management
import React from 'react';
import { api } from '../api.js';
import Card from '../components/common/Card';
import StatsCard from '../components/common/StatsCard';

export default function Admin() {
    const [stats, setStats] = React.useState(null);
    const [loading, setLoading] = React.useState(true);
    const [error, setError] = React.useState('');

    React.useEffect(() => {
        loadStats();
        const interval = setInterval(loadStats, 10000); // Refresh every 10s
        return () => clearInterval(interval);
    }, []);

    const loadStats = async () => {
        try {
            const data = await api('/api/admin/stats');
            setStats(data);
            setError('');
        } catch (e) {
            setError(e.message);
        } finally {
            setLoading(false);
        }
    };

    if (loading) {
        return (
            <Card style={{ padding: 'var(--spacing-6)', textAlign: 'center' }}>
                <p style={{ color: 'var(--color-text-secondary)' }}>Loading statistics...</p>
            </Card>
        );
    }

    if (error) {
        return (
            <Card style={{ padding: 'var(--spacing-6)', textAlign: 'center' }}>
                <p style={{ color: 'var(--color-danger)' }}>Error: {error}</p>
            </Card>
        );
    }

    const occupancyRate = stats.total_spots > 0
        ? ((stats.occupied_spots / stats.total_spots) * 100).toFixed(1)
        : 0;

    return (
        <div style={{ padding: 'var(--spacing-4)', maxWidth: '1400px', margin: '0 auto' }}>
            <div className="flex flex-col" style={{ gap: 'var(--spacing-6)' }}>
                {/* Header */}
                <Card style={{ padding: 'var(--spacing-6)' }}>
                    <h1 style={{ fontSize: 'var(--font-size-2xl)', fontWeight: 'bold', marginBottom: 'var(--spacing-2)' }}>
                        Admin Dashboard
                    </h1>
                    <p style={{ color: 'var(--color-text-secondary)', fontSize: 'var(--font-size-sm)' }}>
                        Parking system overview
                    </p>
                </Card>

                {/* Statistics Grid */}
                <div style={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))',
                    gap: 'var(--spacing-4)'
                }}>
                    <StatsCard
                        title="Total Sessions"
                        value={stats.total_sessions}
                        icon="📊"
                        subtitle="All registered sessions"
                    />
                    <StatsCard
                        title="Active Sessions"
                        value={stats.active_sessions}
                        icon="🚗"
                        color="var(--color-info)"
                        subtitle="Vehicles in parking now"
                    />
                    <StatsCard
                        title="Total Revenue"
                        value={`€${stats.total_revenue.toFixed(2)}`}
                        icon="💰"
                        color="var(--color-success)"
                        subtitle="Accumulated revenue"
                    />
                    <StatsCard
                        title="Today's Sessions"
                        value={stats.today_sessions}
                        icon="📅"
                        color="var(--color-warning)"
                        subtitle="Entries today"
                    />
                </div>

                {/* Parking Occupancy */}
                <div style={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))',
                    gap: 'var(--spacing-4)'
                }}>
                    <StatsCard
                        title="Occupancy Rate"
                        value={`${occupancyRate}%`}
                        icon="📍"
                        subtitle={`${stats.occupied_spots} of ${stats.total_spots} spots occupied`}
                    />
                    <StatsCard
                        title="Average Duration"
                        value={`${Math.round(stats.avg_duration_minutes)} min`}
                        icon="⏱️"
                        color="var(--color-info)"
                        subtitle="Average parking time"
                    />
                </div>

                {/* Recent Sessions */}
                <Card style={{ padding: 'var(--spacing-6)' }}>
                    <h2 style={{ fontSize: 'var(--font-size-xl)', fontWeight: 'bold', marginBottom: 'var(--spacing-4)' }}>
                        Recent Sessions
                    </h2>
                    {stats.recent_sessions.length === 0 ? (
                        <p style={{ color: 'var(--color-text-secondary)', fontSize: 'var(--font-size-sm)' }}>
                            No sessions registered yet.
                        </p>
                    ) : (
                        <div style={{ overflowX: 'auto' }}>
                            <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
                                <thead>
                                    <tr style={{ borderBottom: '2px solid var(--color-surface-hover)' }}>
                                        <th style={{ padding: 'var(--spacing-3)', fontWeight: '600' }}>ID</th>
                                        <th style={{ padding: 'var(--spacing-3)', fontWeight: '600' }}>License Plate</th>
                                        <th style={{ padding: 'var(--spacing-3)', fontWeight: '600' }}>Spot</th>
                                        <th style={{ padding: 'var(--spacing-3)', fontWeight: '600' }}>Entry</th>
                                        <th style={{ padding: 'var(--spacing-3)', fontWeight: '600' }}>Exit</th>
                                        <th style={{ padding: 'var(--spacing-3)', fontWeight: '600' }}>Amount</th>
                                        <th style={{ padding: 'var(--spacing-3)', fontWeight: '600' }}>Status</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {stats.recent_sessions.map((session) => {
                                        const statusColors = {
                                            open: 'var(--color-info)',
                                            paid: 'var(--color-success)',
                                            cancelled: 'var(--color-danger)'
                                        };

                                        return (
                                            <tr key={session.id} style={{ borderBottom: '1px solid var(--color-surface-hover)' }}>
                                                <td style={{ padding: 'var(--spacing-3)' }}>{session.id}</td>
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
                                                    <span style={{
                                                        backgroundColor: statusColors[session.status] || 'var(--color-secondary)',
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
                                        );
                                    })}
                                </tbody>
                            </table>
                        </div>
                    )}
                </Card>
            </div>
        </div>
    );
}
