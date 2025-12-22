// Admin Dashboard - Statistics and Management
import React from 'react';
import { api } from '../api.js';
import Card from '../components/common/Card';
import StatsCard from '../components/common/StatsCard';

export default function Admin() {
 const [stats, setStats] = React.useState(null);
 const [notifications, setNotifications] = React.useState([]);
 const [loading, setLoading] = React.useState(true);
 const [error, setError] = React.useState('');
 const wsRef = React.useRef(null);

 // WebSocket para notificações em tempo real (só envia quando há nova violação)
 React.useEffect(() => {
 const wsUrl = `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/ws`;
 const ws = new WebSocket(wsUrl);
 wsRef.current = ws;

 ws.onmessage = (event) => {
 try {
 const message = JSON.parse(event.data);
 // Verificar se é uma notificação (tem type: "notification")
 if (message.type === 'notification' && message.data?.notification_type === 'violation_alert') {
 const newNotif = {
 id: `ws-${Date.now()}`, // ID temporário para WebSocket
 title: message.data.title,
 body: message.data.body,
 notification_type: message.data.notification_type,
 created_at: message.data.timestamp,
 data: message.data
 };
 setNotifications(prev => [newNotif, ...prev]);
 }
 } catch (e) {
 // Ignorar mensagens que não são JSON (ex: estado de vagas)
 }
 };

 ws.onerror = (err) => console.error('[Admin] WebSocket error:', err);
 ws.onclose = () => console.log('[Admin] WebSocket disconnected');

 return () => {
 if (ws.readyState === WebSocket.OPEN) ws.close();
 };
 }, []);

 // Carregar dados iniciais
 React.useEffect(() => {
 loadStats();
 loadNotifications(); // Carregar notificações existentes no início

 // Apenas stats atualizam periodicamente (notificações vêm via WebSocket)
 const statsInterval = setInterval(loadStats, 30000);
 return () => clearInterval(statsInterval);
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

 const loadNotifications = async () => {
 try {
 const data = await api('/api/user/notifications?unread_only=true');
 setNotifications(data.notifications || []);
 } catch (e) {
 console.error('Failed to load notifications:', e);
 }
 };

 const markAsRead = async (id) => {
 // Remover da lista imediatamente (UI responsiva)
 setNotifications(notifications.filter(n => n.id !== id));

 // Marcar como lida no servidor (se for ID válido do servidor)
 if (typeof id === 'number' && id > 0) {
 try {
 await api(`/api/user/notifications/${id}/read`, { method: 'POST' });
 } catch (e) {
 console.error('Failed to mark notification as read:', e);
 }
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

 {/* Alerts Section - Always visible */}
 <Card style={{
 padding: 'var(--spacing-6)',
 borderLeft: notifications.length > 0 ? '4px solid var(--color-danger)' : '4px solid var(--color-success)',
 backgroundColor: notifications.length > 0 ? 'rgba(239, 68, 68, 0.05)' : undefined
 }}>
 <h2 style={{ fontSize: 'var(--font-size-xl)', fontWeight: 'bold', marginBottom: 'var(--spacing-4)', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
 {notifications.length > 0 ? '' : ''} Alerts ({notifications.length})
 </h2>
 {notifications.length === 0 ? (
 <p style={{ color: 'var(--color-text-secondary)', fontSize: 'var(--font-size-sm)' }}>
 No active alerts. All systems normal.
 </p>
 ) : (
 <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--spacing-3)' }}>
 {notifications.map((notif) => {
 const isViolation = notif.notification_type === 'violation_alert' || notif.notification_type === 'reservation_violation';
 const bgColor = isViolation ? 'rgba(239, 68, 68, 0.1)' : 'var(--color-surface)';
 const borderColor = isViolation ? 'var(--color-danger)' : 'var(--color-border)';

 return (
 <div key={notif.id} style={{
 backgroundColor: bgColor,
 border: `1px solid ${borderColor}`,
 borderRadius: 'var(--border-radius-md)',
 padding: 'var(--spacing-4)',
 display: 'flex',
 justifyContent: 'space-between',
 alignItems: 'flex-start'
 }}>
 <div>
 <div style={{ fontWeight: 'bold', marginBottom: '0.25rem' }}>
 {notif.title}
 </div>
 <div style={{ fontSize: 'var(--font-size-sm)', color: 'var(--color-text-secondary)' }}>
 {notif.body}
 </div>
 <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)', marginTop: '0.5rem' }}>
 {new Date(notif.created_at).toLocaleString()}
 </div>
 </div>
 <button
 onClick={() => markAsRead(notif.id)}
 style={{
 backgroundColor: 'var(--color-surface-hover)',
 border: 'none',
 borderRadius: 'var(--border-radius-sm)',
 padding: '0.5rem 1rem',
 cursor: 'pointer',
 fontSize: 'var(--font-size-sm)',
 color: 'var(--color-text-primary)'
 }}
 >
 Dismiss
 </button>
 </div>
 );
 })}
 </div>
 )}
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
 icon=""
 subtitle="All registered sessions"
 />
 <StatsCard
 title="Active Sessions"
 value={stats.active_sessions}
 icon=""
 color="var(--color-info)"
 subtitle="Vehicles in parking now"
 />
 <StatsCard
 title="Total Revenue"
 value={`€${stats.total_revenue.toFixed(2)}`}
 icon=""
 color="var(--color-success)"
 subtitle="Accumulated revenue"
 />
 <StatsCard
 title="Today's Sessions"
 value={stats.today_sessions}
 icon=""
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
 icon=""
 subtitle={`${stats.occupied_spots} of ${stats.total_spots} spots occupied`}
 />
 <StatsCard
 title="Average Duration"
 value={`${Math.round(stats.avg_duration_minutes)} min`}
 icon="⏱"
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
