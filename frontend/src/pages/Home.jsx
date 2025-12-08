// Home page - Redesigned Parking App Style
import React from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api.js';
import Card from '../components/common/Card';
import Button from '../components/common/Button';
import ZoneFilter from '../components/common/ZoneFilter';
import SpotCard from '../components/common/SpotCard';
import './Home.css';

const ZONES = [
    { id: 'all', label: 'Todas' },
    { id: 'A', label: 'Zona A' },
    { id: 'B', label: 'Zona B' },
    { id: 'C', label: 'Zona C' },
];

export default function Home() {
    const [spots, setSpots] = React.useState({});
    const [activeZone, setActiveZone] = React.useState('all');
    const [loading, setLoading] = React.useState(true);
    const [selectedSpot, setSelectedSpot] = React.useState(null);

    React.useEffect(() => {
        loadSpots();
        const interval = setInterval(loadSpots, 3000);
        return () => clearInterval(interval);
    }, []);

    const loadSpots = async () => {
        try {
            const data = await api('/parking');
            setSpots(data);
            setLoading(false);
        } catch (e) {
            console.error('Failed to load spots:', e);
            setLoading(false);
        }
    };

    // Filter spots by zone
    const getFilteredSpots = () => {
        const spotNames = Object.keys(spots);
        if (activeZone === 'all') return spotNames;
        // Simple zone assignment based on spot number
        return spotNames.filter(name => {
            const num = parseInt(name.replace(/\D/g, '')) || 0;
            if (activeZone === 'A') return num <= 3;
            if (activeZone === 'B') return num > 3 && num <= 6;
            if (activeZone === 'C') return num > 6;
            return true;
        });
    };

    const filteredSpots = getFilteredSpots();
    const freeCount = filteredSpots.filter(name => !spots[name]?.occupied).length;

    const handleSpotClick = (spotName) => {
        setSelectedSpot(spotName);
    };

    const closeModal = () => {
        setSelectedSpot(null);
    };

    return (
        <div className="home-page">
            {/* Stats Banner */}
            <Card className="stats-banner">
                <div className="stats-content">
                    <div className="stat-item">
                        <span className="stat-value">{freeCount}</span>
                        <span className="stat-label">lugares livres</span>
                    </div>
                    <div className="stat-divider"></div>
                    <div className="stat-item">
                        <span className="stat-value">{filteredSpots.length}</span>
                        <span className="stat-label">total</span>
                    </div>
                </div>
            </Card>

            {/* Parking Section */}
            <section className="parking-section">
                <div className="section-header">
                    <h3>Estacionamento</h3>
                    <Link to="/live" className="see-all-link">Ver Tudo</Link>
                </div>

                {loading ? (
                    <div className="loading-state">
                        <p>A carregar...</p>
                    </div>
                ) : (
                    <div className="spots-grid">
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
                                    onClick={() => handleSpotClick(name)}
                                />
                            );
                        })}
                    </div>
                )}
            </section>

            {/* Quick Actions */}
            <div className="quick-actions">
                <Link to="/reservar" className="action-btn-wrapper">
                    <Button variant="primary" size="lg" className="continue-btn">
                        Reservar Vaga
                        <svg viewBox="0 0 24 24" fill="currentColor" width="20" height="20">
                            <path d="M12 4l-1.41 1.41L16.17 11H4v2h12.17l-5.58 5.59L12 20l8-8z" />
                        </svg>
                    </Button>
                </Link>
            </div>

            {/* Spot Detail Modal */}
            {selectedSpot && (
                <div className="modal-overlay" onClick={closeModal}>
                    <div className="modal-content" onClick={(e) => e.stopPropagation()}>
                        <button className="modal-close" onClick={closeModal}>
                            <svg viewBox="0 0 24 24" fill="currentColor" width="24" height="24">
                                <path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z" />
                            </svg>
                        </button>
                        <h3 className="modal-title">Confirmar Reserva</h3>
                        <p className="modal-subtitle">TugaPark</p>
                        
                        <div className="modal-details">
                            <div className="detail-box">
                                <span className="detail-label">Zona</span>
                                <span className="detail-value">Zona A</span>
                            </div>
                            <div className="detail-box">
                                <span className="detail-label">Lugar</span>
                                <span className="detail-value">{selectedSpot}</span>
                            </div>
                        </div>

                        <div className="modal-price">
                            <span className="price-value">€2.50</span>
                            <span className="price-label">por hora</span>
                        </div>

                        <Link to="/reservar" onClick={closeModal}>
                            <Button variant="primary" size="lg" className="confirm-btn">
                                Confirmar
                                <svg viewBox="0 0 24 24" fill="currentColor" width="20" height="20">
                                    <path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z" />
                                </svg>
                            </Button>
                        </Link>
                    </div>
                </div>
            )}
        </div>
    );
}
