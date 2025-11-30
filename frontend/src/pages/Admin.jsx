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
                <p style={{ color: 'var(--color-text-secondary)' }}>A carregar estatísticas...</p>
            </Card>
        );
    }

    if (error) {
        return (
            <Card style={{ padding: 'var(--spacing-6)', textAlign: 'center' }}>
                <p style={{ color: 'var(--color-danger)' }}>Erro: {error}</p>
            </Card>
        );
    }

    const occupancyRate = stats.total_spots > 0 
        ? ((stats.occupied_spots / stats.total_spots) * 100).toFixed(1) 
        : 0;

    return (
        <div className="flex flex-col gap-4">
            {/* Header */}
            <Card style={{ padding: 'var(--spacing-4)' }}>
                <h1 style={{ fontSize: 'var(--font-size-2xl)', fontWeight: 'bold', marginBottom: 'var(--spacing-2)' }}>
                    Painel de Administração
                </h1>
                <p style={{ color: 'var(--color-text-secondary)', fontSize: 'var(--font-size-sm)' }}>
                    Visão geral do sistema de estacionamento
                </p>
            </Card>

            {/* Statistics Grid */}
            <div style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))',
                gap: 'var(--spacing-4)'
            }}>
                <StatsCard
                    title="Sessões Totais"
                    value={stats.total_sessions}
                    icon="📊"
                    subtitle="Todas as sessões registadas"
                />
                <StatsCard
                    title="Sessões Ativas"
                    value={stats.active_sessions}
                    icon="🚗"
                    color="var(--color-info)"
                    subtitle="Veículos no parque agora"
                />
                <StatsCard
                    title="Receita Total"
                    value={`€${stats.total_revenue.toFixed(2)}`}
                    icon="💰"
                    color="var(--color-success)"
                    subtitle="Receita acumulada"
                />
                <StatsCard
                    title="Sessões Hoje"
                    value={stats.today_sessions}
                    icon="📅"
                    color="var(--color-warning)"
                    subtitle="Entradas hoje"
                />
            </div>

            {/* Parking Occupancy */}
            <div style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))',
                gap: 'var(--spacing-4)'
            }}>
                <StatsCard
                    title="Taxa de Ocupação"
                    value={`${occupancyRate}%`}
                    icon="📍"
                    subtitle={`${stats.occupied_spots} de ${stats.total_spots} vagas ocupadas`}
                />
                <StatsCard
                    title="Duração Média"
                    value={`${Math.round(stats.avg_duration_minutes)} min`}
                    icon="⏱️"
                    color="var(--color-info)"
                    subtitle="Tempo médio de permanência"
                />
            </div>

            {/* Recent Sessions */}
            <Card>
                <h2 style={{ fontSize: 'var(--font-size-xl)', fontWeight: 'bold', marginBottom: 'var(--spacing-4)' }}>
                    Sessões Recentes
                </h2>
                {stats.recent_sessions.length === 0 ? (
                    <p style={{ color: 'var(--color-text-secondary)', fontSize: 'var(--font-size-sm)' }}>
                        Nenhuma sessão registada ainda.
                    </p>
                ) : (
                    <div style={{ overflowX: 'auto' }}>
                        <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
                            <thead>
                                <tr style={{ borderBottom: '1px solid var(--color-surface-hover)' }}>
                                    <th style={{ padding: 'var(--spacing-2)' }}>ID</th>
                                    <th style={{ padding: 'var(--spacing-2)' }}>Matrícula</th>
                                    <th style={{ padding: 'var(--spacing-2)' }}>Entrada</th>
                                    <th style={{ padding: 'var(--spacing-2)' }}>Saída</th>
                                    <th style={{ padding: 'var(--spacing-2)' }}>Valor</th>
                                    <th style={{ padding: 'var(--spacing-2)' }}>Estado</th>
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
                                            <td style={{ padding: 'var(--spacing-2)' }}>{session.id}</td>
                                            <td style={{ padding: 'var(--spacing-2)', fontWeight: 'bold' }}>{session.plate}</td>
                                            <td style={{ padding: 'var(--spacing-2)', fontSize: 'var(--font-size-sm)' }}>
                                                {session.entry_time ? new Date(session.entry_time).toLocaleString('pt-PT') : '-'}
                                            </td>
                                            <td style={{ padding: 'var(--spacing-2)', fontSize: 'var(--font-size-sm)' }}>
                                                {session.exit_time ? new Date(session.exit_time).toLocaleString('pt-PT') : '-'}
                                            </td>
                                            <td style={{ padding: 'var(--spacing-2)' }}>
                                                €{session.amount_due.toFixed(2)}
                                            </td>
                                            <td style={{ padding: 'var(--spacing-2)' }}>
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
    );
}
