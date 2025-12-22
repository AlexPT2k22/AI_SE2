// Reservation page - TugaPark v2.0
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { api, apiPost } from '../api';
import Card from '../components/common/Card';
import Button from '../components/common/Button';

export default function Reserve() {
 const navigate = useNavigate();
 const { user, isAuthenticated } = useAuth();

 const [spots, setSpots] = useState({});
 const [reservations, setReservations] = useState([]);
 const [vehicles, setVehicles] = useState([]);
 const [selectedSpot, setSelectedSpot] = useState('');
 const [selectedVehicle, setSelectedVehicle] = useState('');
 const [selectedDate, setSelectedDate] = useState('today'); // 'today' or 'tomorrow'
 const [msg, setMsg] = useState('');
 const [err, setErr] = useState('');
 const [loading, setLoading] = useState(false);

 // Get formatted dates
 const getDateOptions = () => {
 const today = new Date();
 const tomorrow = new Date(today);
 tomorrow.setDate(tomorrow.getDate() + 1);

 const formatDate = (date) => date.toISOString().split('T')[0];
 const formatDisplay = (date) => date.toLocaleDateString('en-US', {
 weekday: 'short',
 day: 'numeric',
 month: 'short'
 });

 return {
 today: {
 value: formatDate(today),
 display: `Today - ${formatDisplay(today)}`
 },
 tomorrow: {
 value: formatDate(tomorrow),
 display: `Tomorrow - ${formatDisplay(tomorrow)}`
 }
 };
 };

 const dateOptions = getDateOptions();

 useEffect(() => {
 if (!isAuthenticated()) {
 return;
 }
 loadData();
 const interval = setInterval(loadData, 5000);
 return () => clearInterval(interval);
 }, [user, isAuthenticated]);

 const loadData = async () => {
 try {
 const [spotsData, reservationsData, vehiclesData] = await Promise.all([
 api('/parking'),
 api('/api/reservations'),
 api('/api/user/vehicles')
 ]);
 setSpots(spotsData);
 setReservations(reservationsData.reservations || reservationsData || []);
 setVehicles(vehiclesData.vehicles || []);

 // Auto-select first vehicle if none selected
 if (!selectedVehicle && vehiclesData.vehicles?.length > 0) {
 const primaryVehicle = vehiclesData.vehicles.find(v => v.is_primary);
 setSelectedVehicle(primaryVehicle?.plate || vehiclesData.vehicles[0].plate);
 }
 } catch (e) {
 console.error('Failed to load data:', e);
 }
 };

 const createReservation = async (e) => {
 e.preventDefault();

 if (!selectedVehicle) {
 setErr('Please select a vehicle.');
 return;
 }
 if (!selectedSpot) {
 setErr('Please select a spot.');
 return;
 }

 setMsg('');
 setErr('');
 setLoading(true);

 try {
 // Get the selected date value
 const reservationDate = selectedDate === 'today'
 ? dateOptions.today.value
 : dateOptions.tomorrow.value;

 const data = await apiPost('/api/reservations', {
 spot: selectedSpot,
 plate: selectedVehicle,
 reservation_date: reservationDate
 });

 const reservation = data.reservation || data;
 const dateDisplay = selectedDate === 'today' ? 'today' : 'tomorrow';
 setMsg(`Reservation confirmed! Spot ${reservation.spot} for ${dateDisplay} (${reservation.reservation_date})`);
 setSelectedSpot('');
 loadData();
 } catch (e) {
 setErr(e.message || 'Failed to create reservation');
 } finally {
 setLoading(false);
 }
 };

 const cancelReservation = async (spot) => {
 if (!confirm(`Cancel reservation for spot ${spot}?`)) return;
 try {
 await api(`/api/reservations/${spot}`, { method: 'DELETE' });
 setMsg(`Reservation for spot ${spot} cancelled.`);
 loadData();
 } catch (e) {
 setErr(e.message);
 }
 };

 if (!isAuthenticated()) {
 return (
 <Card className="p-4 text-center">
 <h2 style={{ fontSize: 'var(--font-size-xl)', fontWeight: 'bold', marginBottom: 'var(--spacing-4)' }}>
 Authentication Required
 </h2>
 <p style={{ color: 'var(--color-text-secondary)', marginBottom: 'var(--spacing-6)' }}>
 You need to sign in to make reservations.
 </p>
 <Button onClick={() => navigate('/login')}>
 Sign In
 </Button>
 </Card>
 );
 }

 if (vehicles.length === 0) {
 return (
 <Card className="p-4 text-center">
 <h2 style={{ fontSize: 'var(--font-size-xl)', fontWeight: 'bold', marginBottom: 'var(--spacing-4)' }}>
 No Vehicles Registered
 </h2>
 <p style={{ color: 'var(--color-text-secondary)', marginBottom: 'var(--spacing-6)' }}>
 You need to register a vehicle before making reservations.
 </p>
 <Button onClick={() => navigate('/perfil')}>
 Go to Profile
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
 Reserve a Spot
 </h2>
 <p style={{ color: 'var(--color-text-secondary)', fontSize: 'var(--font-size-sm)', marginBottom: 'var(--spacing-4)' }}>
 User: <strong>{user?.name}</strong>
 </p>

 {/* Info box */}
 <div style={{
 background: 'rgba(200, 230, 32, 0.1)',
 border: '1px solid var(--color-primary)',
 borderRadius: 'var(--border-radius-lg)',
 padding: 'var(--spacing-3)',
 marginBottom: 'var(--spacing-4)',
 fontSize: 'var(--font-size-sm)'
 }}>
 <strong>Info:</strong> You can only reserve for today or tomorrow.
 If you don't use your reservation, a 20 EUR fine will be applied.
 </div>

 {availableSpots.length === 0 ? (
 <p style={{ color: 'var(--color-warning)', marginTop: 'var(--spacing-4)' }}>
 No spots available for reservation at this time.
 </p>
 ) : (
 <form onSubmit={createReservation} className="flex flex-col gap-4 mt-4">
 <div className="flex gap-4" style={{ flexWrap: 'wrap' }}>
 {/* Vehicle Selection */}
 <div style={{ flex: 1, minWidth: '200px' }}>
 <label className="input-label" style={{ marginBottom: 'var(--spacing-2)', display: 'block' }}>
 Vehicle
 </label>
 <select
 className="input"
 style={{ width: '100%' }}
 value={selectedVehicle}
 onChange={(e) => setSelectedVehicle(e.target.value)}
 required
 >
 {vehicles.map((v) => (
 <option key={v.id} value={v.plate}>
 {v.plate} {v.is_primary ? '(Primary)' : ''} {v.brand ? `- ${v.brand} ${v.model || ''}` : ''}
 </option>
 ))}
 </select>
 </div>

 {/* Spot Selection */}
 <div style={{ flex: 1, minWidth: '200px' }}>
 <label className="input-label" style={{ marginBottom: 'var(--spacing-2)', display: 'block' }}>
 Spot
 </label>
 <select
 className="input"
 style={{ width: '100%' }}
 value={selectedSpot}
 onChange={(e) => setSelectedSpot(e.target.value)}
 required
 >
 <option value="">Select a spot...</option>
 {availableSpots.map((name) => (
 <option key={name} value={name}>
 {name}
 </option>
 ))}
 </select>
 </div>

 {/* Date Selection */}
 <div style={{ flex: 1, minWidth: '200px' }}>
 <label className="input-label" style={{ marginBottom: 'var(--spacing-2)', display: 'block' }}>
 Reservation Date
 </label>
 <select
 className="input"
 style={{ width: '100%' }}
 value={selectedDate}
 onChange={(e) => setSelectedDate(e.target.value)}
 required
 >
 <option value="today">{dateOptions.today.display}</option>
 <option value="tomorrow">{dateOptions.tomorrow.display}</option>
 </select>
 </div>
 </div>

 {/* Submit Button */}
 <div style={{ marginTop: 'var(--spacing-2)' }}>
 <Button
 type="submit"
 disabled={loading || !selectedSpot || !selectedVehicle}
 style={{ width: '100%', maxWidth: '300px' }}
 >
 {loading ? 'Reserving...' : 'Confirm Reservation'}
 </Button>
 </div>
 </form>
 )}

 {msg && <p style={{ color: 'var(--color-success)', marginTop: 'var(--spacing-4)', fontWeight: 'var(--font-weight-medium)' }}>{msg}</p>}
 {err && <p style={{ color: 'var(--color-danger)', marginTop: 'var(--spacing-4)' }}>{err}</p>}
 </Card>

 <Card>
 <h2 style={{ fontSize: 'var(--font-size-xl)', fontWeight: 'bold', marginBottom: 'var(--spacing-4)' }}>
 My Reservations
 </h2>
 {reservations.length === 0 ? (
 <p style={{ color: 'var(--color-text-secondary)', fontSize: 'var(--font-size-sm)' }}>
 No active reservations.
 </p>
 ) : (
 <div style={{ overflowX: 'auto' }}>
 <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
 <thead>
 <tr style={{ borderBottom: '1px solid var(--color-surface-hover)' }}>
 <th style={{ padding: 'var(--spacing-2)' }}>Spot</th>
 <th style={{ padding: 'var(--spacing-2)' }}>License Plate</th>
 <th style={{ padding: 'var(--spacing-2)' }}>Date</th>
 <th style={{ padding: 'var(--spacing-2)' }}>Status</th>
 <th style={{ padding: 'var(--spacing-2)' }}>Actions</th>
 </tr>
 </thead>
 <tbody>
 {reservations.map((res) => {
 const isToday = res.reservation_date === dateOptions.today.value;
 const isTomorrow = res.reservation_date === dateOptions.tomorrow.value;
 const dateLabel = isToday ? 'Today' : isTomorrow ? 'Tomorrow' : res.reservation_date;

 return (
 <tr key={res.id || res.spot} style={{ borderBottom: '1px solid var(--color-surface-hover)' }}>
 <td style={{ padding: 'var(--spacing-2)', fontWeight: 'bold' }}>{res.spot}</td>
 <td style={{ padding: 'var(--spacing-2)' }}>{res.plate || 'N/A'}</td>
 <td style={{ padding: 'var(--spacing-2)' }}>
 <span style={{
 background: isToday ? 'var(--color-primary)' : 'var(--color-info)',
 color: isToday ? 'black' : 'white',
 padding: '2px 8px',
 borderRadius: '4px',
 fontSize: 'var(--font-size-sm)'
 }}>
 {dateLabel}
 </span>
 </td>
 <td style={{ padding: 'var(--spacing-2)' }}>
 {res.was_used ? (
 <span style={{ color: 'var(--color-success)' }}>Used</span>
 ) : res.fine_applied ? (
 <span style={{ color: 'var(--color-danger)' }}>Fine Applied</span>
 ) : (
 <span style={{ color: 'var(--color-warning)' }}>Pending</span>
 )}
 </td>
 <td style={{ padding: 'var(--spacing-2)' }}>
 {!res.was_used && !res.fine_applied && (
 <Button
 variant="ghost"
 size="sm"
 onClick={() => cancelReservation(res.spot)}
 style={{ color: 'var(--color-danger)' }}
 >
 Cancel
 </Button>
 )}
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
