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
 const userReservations = reservationsData.reservations || reservationsData;
 setReservations(Array.isArray(userReservations) ? userReservations : []);

 // Load unpaid sessions (sessions with exit but status still open)
 try {
 const allSessions = await api('/api/sessions?status=open');
 console.log('Open sessions:', allSessions);

 const userUnpaidSessions = (allSessions || []).filter(session => {
 const hasExit = session.exit_time !== null && session.exit_time !== undefined;
 const hasDue = session.amount_due > 0;
 return hasExit && hasDue;
 });

 console.log('User unpaid sessions:', userUnpaidSessions);
 setUnpaidSessions(userUnpaidSessions);
 } catch (sessionErr) {
 console.error('Error loading sessions:', sessionErr);
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
 <div style={{ padding: 'var(--spacing-4)', maxWidth: '1200px', margin: '0 auto' }}>
 <div className="flex flex-col" style={{ gap: 'var(--spacing-6)' }}>
 {/* Unpaid Sessions Section */}
 {user && unpaidSessions.length > 0 && (
 <Card style={{ padding: 'var(--spacing-6)', borderLeft: '4px solid var(--color-warning)' }}>
 <h2 style={{ fontSize: 'var(--font-size-xl)', fontWeight: 'bold', marginBottom: 'var(--spacing-4)', color: 'var(--color-warning)' }}>
 Unpaid Sessions
 </h2>

 <p style={{ color: 'var(--color-text-secondary)', fontSize: 'var(--font-size-sm)', marginBottom: 'var(--spacing-4)' }}>
 You have parking sessions that require payment.
 </p>

 <div style={{ overflowX: 'auto' }}>
 <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
 <thead>
 <tr style={{ borderBottom: '1px solid var(--color-surface-hover)' }}>
 <th style={{ padding: 'var(--spacing-2)' }}>ID</th>
 <th style={{ padding: 'var(--spacing-2)' }}>Entry</th>
 <th style={{ padding: 'var(--spacing-2)' }}>Exit</th>
 <th style={{ padding: 'var(--spacing-2)' }}>Amount</th>
 <th style={{ padding: 'var(--spacing-2)' }}>Action</th>
 </tr>
 </thead>
 <tbody>
 {unpaidSessions.map((session) => (
 <tr key={session.id} style={{ borderBottom: '1px solid var(--color-surface-hover)' }}>
 <td style={{ padding: 'var(--spacing-2)' }}>#{session.id}</td>
 <td style={{ padding: 'var(--spacing-2)', fontSize: 'var(--font-size-sm)' }}>
 {new Date(session.entry_time).toLocaleString()}
 </td>
 <td style={{ padding: 'var(--spacing-2)', fontSize: 'var(--font-size-sm)' }}>
 {new Date(session.exit_time).toLocaleString()}
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
 Pay Now
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
 <Card style={{ padding: 'var(--spacing-6)' }}>
 <h2 style={{ fontSize: 'var(--font-size-xl)', fontWeight: 'bold', marginBottom: 'var(--spacing-4)' }}>
 My Reservations
 </h2>

 {loading && <p style={{ color: 'var(--color-text-secondary)', fontSize: 'var(--font-size-sm)' }}>Loading...</p>}

 {!loading && !user && (
 <p style={{ color: 'var(--color-warning)', fontSize: 'var(--font-size-sm)', marginBottom: 0 }}>
 Please sign in to view your active reservations.
 </p>
 )}

 {!loading && user && reservations.length === 0 && (
 <p style={{ color: 'var(--color-text-secondary)', fontSize: 'var(--font-size-sm)', marginBottom: 0 }}>
 You have no active reservations. User: <strong>{user.name}</strong>
 </p>
 )}

 {!loading && user && reservations.length > 0 && (
 <div>
 <p style={{ color: 'var(--color-text-secondary)', fontSize: 'var(--font-size-sm)' }}>
 User: <strong>{user.name}</strong>
 </p>
 <div style={{ overflowX: 'auto', marginTop: 'var(--spacing-2)' }}>
 <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
 <thead>
 <tr style={{ borderBottom: '1px solid var(--color-surface-hover)' }}>
 <th style={{ padding: 'var(--spacing-2)' }}>Spot</th>
 <th style={{ padding: 'var(--spacing-2)' }}>Date</th>
 <th style={{ padding: 'var(--spacing-2)' }}>Status</th>
 </tr>
 </thead>
 <tbody>
 {reservations.map((res) => (
 <tr key={res.id || res.spot} style={{ borderBottom: '1px solid var(--color-surface-hover)' }}>
 <td className="font-bold" style={{ padding: 'var(--spacing-2)' }}>{res.spot}</td>
 <td style={{ padding: 'var(--spacing-2)' }}>{res.reservation_date}</td>
 <td style={{ padding: 'var(--spacing-2)' }}>
 <span style={{
 backgroundColor: 'var(--color-primary)',
 padding: '0.25rem 0.5rem',
 borderRadius: 'var(--border-radius-sm)',
 fontSize: '0.75rem',
 fontWeight: 'bold'
 }}>
 Active
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
 </div>
 );
}
