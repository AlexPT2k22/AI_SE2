import React from 'react';
import PropTypes from 'prop-types';
import './SpotCard.css';

// SVG car icon in top-down view
const CarIcon = ({ color = '#c8e620' }) => (
    <svg xmlns="http://www.w3.org/2000/svg" x="0px" y="0px" width="50" height="50" viewBox="0,0,256,256" style={{ transform: 'rotate(-90deg)' }}>
        <g fill={color} fillRule="nonzero" stroke="none" strokeWidth="1" strokeLinecap="butt" strokeLinejoin="miter" strokeMiterlimit="10" strokeDasharray="" strokeDashoffset="0" fontFamily="none" fontWeight="none" fontSize="none" textAnchor="none" style={{ mixBlendMode: 'normal' }}><g transform="scale(5.12,5.12)"><path d="M30,9v2h-22.875c-1.79297,0 -3.37891,1.20313 -3.85547,2.9375c-0.58984,2.13672 -1.26953,5.76172 -1.26953,11.0625c0,5.30078 0.67969,8.92578 1.26953,11.0625c0.47656,1.73438 2.0625,2.9375 3.85547,2.9375h22.875v2h2v-2h9.15234c2.84375,0 5.29688,-2.00781 5.87891,-4.78516c0.49219,-2.36719 0.96875,-5.58594 0.96875,-9.21484c0,-3.62891 -0.47656,-6.84766 -0.96875,-9.21484c-0.58203,-2.77734 -3.03516,-4.78516 -5.87891,-4.78516h-9.15234v-2zM12,13h18l-5,4h-8zM43,14h0.78906c0.63281,0.55859 1.09766,1.3125 1.28516,2.19531c0.22656,1.08984 0.44531,2.38281 0.61719,3.80469h-2.69141zM9,16l4,4v10l-4,4c0,0 -1,-3.07031 -1,-9.00391c0,-5.93359 1,-8.99609 1,-8.99609zM33,16c0,0 2,3.95313 2,9c0,5.04688 -2,9 -2,9l-4,-4v-10zM43,30h2.69141c-0.17187,1.42188 -0.39453,2.71484 -0.62109,3.80469c-0.18359,0.88281 -0.64844,1.63672 -1.28516,2.19531h-0.78516zM17,33h8l5,4h-18z"></path></g></g>
    </svg>
);

const SpotCard = ({ spotId, status, reserved = false, onClick = () => {} }) => {
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

export default SpotCard;
