import React from 'react';
import PropTypes from 'prop-types';
import './SpotCard.css';

// SVG car icon in top-down view
const CarIcon = ({ color = '#c8e620' }) => (
    <svg
        viewBox="0 0 60 100"
        className="car-icon"
        fill={color}
    >
        {/* Car body */}
        <rect x="8" y="15" width="44" height="70" rx="8" ry="8" />
        {/* Windshield */}
        <rect x="12" y="22" width="36" height="18" rx="4" ry="4" fill="rgba(0,0,0,0.2)" />
        {/* Rear window */}
        <rect x="12" y="60" width="36" height="12" rx="3" ry="3" fill="rgba(0,0,0,0.2)" />
        {/* Left mirrors */}
        <ellipse cx="4" cy="30" rx="4" ry="6" />
        {/* Right mirror */}
        <ellipse cx="56" cy="30" rx="4" ry="6" />
        {/* Front lights */}
        <rect x="14" y="16" width="8" height="4" rx="1" fill="rgba(255,255,255,0.6)" />
        <rect x="38" y="16" width="8" height="4" rx="1" fill="rgba(255,255,255,0.6)" />
        {/* Rear lights */}
        <rect x="14" y="80" width="8" height="4" rx="1" fill="rgba(255,100,100,0.8)" />
        <rect x="38" y="80" width="8" height="4" rx="1" fill="rgba(255,100,100,0.8)" />
    </svg>
);

const SpotCard = ({ spotId, status, reserved, onClick }) => {
    const isAvailable = status === 'available';
    const isOccupied = status === 'occupied';

    return (
        <div
            className={`spot-card ${status} ${reserved ? 'reserved' : ''}`}
            onClick={onClick}
        >
            <div className="spot-info">
                <span className="spot-id">{spotId}</span>
                <span className="spot-status">
                    {isAvailable ? 'Disponível' : isOccupied ? 'Ocupado' : 'Reservado'}
                </span>
            </div>
            <div className="car-container">
                {isOccupied ? (
                    <CarIcon color="#9ca3af" />
                ) : (
                    <CarIcon color="#c8e620" />
                )}
            </div>
            {reserved && <div className="reserved-badge">Reservado</div>}
        </div>
    );
};

SpotCard.propTypes = {
    spotId: PropTypes.string.isRequired,
    status: PropTypes.oneOf(['available', 'occupied', 'reserved']).isRequired,
    reserved: PropTypes.bool,
    onClick: PropTypes.func,
};

SpotCard.defaultProps = {
    reserved: false,
    onClick: () => {},
};

export default SpotCard;
