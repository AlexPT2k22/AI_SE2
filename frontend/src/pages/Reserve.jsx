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
    const [msg, setMsg] = useState('');
    const [err, setErr] = useState('');
    const [loading, setLoading] = useState(false);

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
            setErr('Please select a vehicle first.');
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
            // Get today's date in YYYY-MM-DD format
            const today = new Date().toISOString().split('T')[0];

            const data = await apiPost('/api/reservations', {
                spot: selectedSpot,
                plate: selectedVehicle,
                reservation_date: today
            });

            const reservation = data.reservation || data;
            setMsg(`Reservation confirmed: ${reservation.spot} for ${reservation.reservation_date}`);
            setSelectedSpot('');
            loadData();
        } catch (e) {
            setErr(e.message);
        } finally {
            setLoading(false);
        }
    };

    const cancelReservation = async (spot) => {
        if (!confirm(`Cancel reservation for ${spot}?`)) return;
        try {
            await api(`/api/reservations/${spot}`, { method: 'DELETE' });
            setMsg(`Reservation for ${spot} cancelled.`);
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
                    You need to be logged in to make reservations.
                </p>
                <Button onClick={() => navigate('/login')}>
                    Go to Sign In
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

                {availableSpots.length === 0 ? (
                    <p style={{ color: 'var(--color-warning)', marginTop: 'var(--spacing-4)' }}>
                        No spots available for reservation at this time.
                    </p>
                ) : (
                    <form onSubmit={createReservation} className="flex flex-col gap-4 mt-4">
                        <div className="flex gap-4" style={{ flexWrap: 'wrap' }}>
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

                            <div style={{ display: 'flex', alignItems: 'flex-end' }}>
                                <Button disabled={loading || !selectedSpot || !selectedVehicle} style={{ width: '100%' }}>
                                    {loading ? 'Reserving...' : 'Reserve'}
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
                    Active Reservations
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
                                    <th style={{ padding: 'var(--spacing-2)' }}>Actions</th>
                                </tr>
                            </thead>
                            <tbody>
                                {reservations.map((res) => (
                                    <tr key={res.spot} style={{ borderBottom: '1px solid var(--color-surface-hover)' }}>
                                        <td style={{ padding: 'var(--spacing-2)' }}>{res.spot}</td>
                                        <td style={{ padding: 'var(--spacing-2)' }}>{res.plate || 'N/A'}</td>
                                        <td style={{ padding: 'var(--spacing-2)' }}>{res.reservation_date || 'Today'}</td>
                                        <td style={{ padding: 'var(--spacing-2)' }}>
                                            <Button
                                                variant="ghost"
                                                size="sm"
                                                onClick={() => cancelReservation(res.spot)}
                                                style={{ color: 'var(--color-danger)' }}
                                            >
                                                Cancel
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
