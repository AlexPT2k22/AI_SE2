// Occupancy component - Redesigned with visual car grid
import React from 'react';
import { api } from '../api.js';
import Card from '../components/common/Card';
import ZoneFilter from '../components/common/ZoneFilter';
import SpotCard from '../components/common/SpotCard';
import './Occupancy.css';

const ZONES = [
    { id: 'all', label: 'All' },
    { id: 'A', label: 'Zone A' },
    { id: 'B', label: 'Zone B' },
    { id: 'C', label: 'Zone C' },
];

export default function Occupancy() {
    const [spots, setSpots] = React.useState({});
    const [error, setError] = React.useState('');
    const [loading, setLoading] = React.useState(true);
    const [activeZone, setActiveZone] = React.useState('all');

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

    // Filter spots by zone
    const getFilteredSpots = () => {
        const spotNames = Object.keys(spots);
        if (activeZone === 'all') return spotNames;
        return spotNames.filter(name => {
            const num = parseInt(name.replace(/\D/g, '')) || 0;
            if (activeZone === 'A') return num <= 3;
            if (activeZone === 'B') return num > 3 && num <= 6;
            if (activeZone === 'C') return num > 6;
            return true;
        });
    };

    const filteredSpots = getFilteredSpots();
    const occupied = filteredSpots.filter(name => spots[name]?.occupied).length;
    const free = filteredSpots.length - occupied;

    if (loading) {
        return (
            <Card>
                <h2 className="occupancy-title">Parking Occupancy</h2>
                <p className="loading-text">Loading...</p>
            </Card>
        );
    }

    if (error) {
        return (
            <Card>
                <h2 className="occupancy-title">Parking Occupancy</h2>
                <p className="error-text">{error}</p>
            </Card>
        );
    }

    return (
        <div className="occupancy-page">
            <Card>
                <div className="occupancy-header">
                    <h2 className="occupancy-title">Parking Occupancy</h2>
                    <div className="occupancy-stats">
                        <span className="stat stat-free">
                            <span className="stat-dot free"></span>
                            Free: <strong>{free}</strong>
                        </span>
                        <span className="stat stat-occupied">
                            <span className="stat-dot occupied"></span>
                            Occupied: <strong>{occupied}</strong>
                        </span>
                    </div>
                </div>

                <div className="parking-lot">
                    {/* Road markings effect */}
                    <div className="parking-grid">
                        {filteredSpots.map((name) => {
                            const spot = spots[name];
                            const status = spot.occupied ? 'occupied' :
                                spot.reserved ? 'reserved' : 'available';
                            return (
                                <SpotCard
                                    key={name}
                                    spotId={name}
                                    status={status}
                                    reserved={spot.reserved}
                                />
                            );
                        })}
                    </div>
                </div>
            </Card>
        </div>
    );
}
