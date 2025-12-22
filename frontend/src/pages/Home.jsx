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
 { id: 'all', label: 'All' },
 { id: 'A', label: 'Zone A' },
 { id: 'B', label: 'Zone B' },
 { id: 'C', label: 'Zone C' },
];

export default function Home() {
 const [spots, setSpots] = React.useState({});
 const [activeZone, setActiveZone] = React.useState('all');
 const [loading, setLoading] = React.useState(true);

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
 const freeCount = filteredSpots.filter(name => !spots[name]?.occupied && !spots[name]?.reserved).length;

 return (
 <div className="home-page">
 {/* Stats Banner */}
 <Card className="stats-banner">
 <div className="stats-content">
 <div className="stat-item">
 <span className="stat-value">{freeCount}</span>
 <span className="stat-label">free spots</span>
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
 <h3>Parking</h3>
 <Link to="/live" className="see-all-link">View All</Link>
 </div>

 {loading ? (
 <div className="loading-state">
 <p>Loading...</p>
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
 Reserve Spot
 <svg viewBox="0 0 24 24" fill="currentColor" width="20" height="20">
 <path d="M12 4l-1.41 1.41L16.17 11H4v2h12.17l-5.58 5.59L12 20l8-8z" />
 </svg>
 </Button>
 </Link>
 </div>
 </div>
 );
}
