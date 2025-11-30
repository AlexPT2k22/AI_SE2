// Occupancy component - shows all parking spots status
import React from 'react';
import { api } from '../api.js';
import Card from '../components/common/Card';
import './Occupancy.css';

export default function Occupancy() {
    const [spots, setSpots] = React.useState({});
    const [error, setError] = React.useState('');
    const [loading, setLoading] = React.useState(true);

    React.useEffect(() => {
        loadSpots();
        const interval = setInterval(loadSpots, 3000);
        return () => clearInterval(interval);
    }, []);

    async function loadSpots() {
        try {
            const data = await api('/parking');
            setSpots(data);
            setError('');
            setLoading(false);
        } catch (e) {
            setError(e.message);
            setLoading(false);
        }
    }

    if (loading) {
        return (
            <Card>
                <h2 style={{ fontSize: 'var(--font-size-xl)', fontWeight: 'bold', marginBottom: 'var(--spacing-2)' }}>
                    Ocupação do Parque
                </h2>
                <p style={{ color: 'var(--color-text-secondary)', fontSize: 'var(--font-size-sm)' }}>A carregar...</p>
            </Card>
        );
    }

    if (error) {
        return (
            <Card>
                <h2 style={{ fontSize: 'var(--font-size-xl)', fontWeight: 'bold', marginBottom: 'var(--spacing-2)' }}>
                    Ocupação do Parque
                </h2>
                <p style={{ color: 'var(--color-danger)', fontSize: 'var(--font-size-sm)' }}>{error}</p>
            </Card>
        );
    }

    const spotNames = Object.keys(spots);
    const occupied = spotNames.filter(name => spots[name].occupied).length;
    const free = spotNames.length - occupied;

    return (
        <Card>
            <div className="flex justify-between items-center" style={{ marginBottom: 'var(--spacing-6)' }}>
                <h2 style={{ fontSize: 'var(--font-size-xl)', fontWeight: 'bold' }}>
                    Ocupação do Parque
                </h2>
                <div className="flex gap-4 text-sm font-medium">
                    <span style={{ color: 'var(--color-text-secondary)' }}>Total: <strong style={{ color: 'var(--color-text-primary)' }}>{spotNames.length}</strong></span>
                    <span style={{ color: 'var(--color-success)' }}>Livres: <strong>{free}</strong></span>
                    <span style={{ color: 'var(--color-danger)' }}>Ocupados: <strong>{occupied}</strong></span>
                </div>
            </div>

            <div className="occupancy-grid">
                {spotNames.map((name) => {
                    const spot = spots[name];
                    const isOccupied = spot.occupied;
                    const isReserved = spot.reserved;
                    const isViolation = spot.violation;

                    let statusClass = 'free';
                    if (isOccupied) statusClass = 'occupied';
                    if (isReserved) statusClass += ' reserved';
                    if (isViolation) statusClass += ' violation';

                    return (
                        <div key={name} className={`spot-card ${statusClass}`}>
                            <div className="spot-id">{name}</div>
                            <div className="spot-status">
                                {isOccupied ? 'Ocupado' : 'Livre'}
                            </div>

                            {isReserved && <div className="spot-badge badge-reserved">Reservado</div>}
                            {isViolation && <div className="spot-badge badge-violation">Violação</div>}
                        </div>
                    );
                })}
            </div>
        </Card>
    );
}
