import React from 'react';
import PropTypes from 'prop-types';
import './ZoneFilter.css';

const ZoneFilter = ({ zones, activeZone, onZoneChange }) => {
    return (
        <div className="zone-filter">
            {zones.map((zone) => (
                <button
                    key={zone.id}
                    className={`zone-pill ${activeZone === zone.id ? 'active' : ''}`}
                    onClick={() => onZoneChange(zone.id)}
                >
                    {zone.label}
                </button>
            ))}
        </div>
    );
};

ZoneFilter.propTypes = {
    zones: PropTypes.arrayOf(
        PropTypes.shape({
            id: PropTypes.string.isRequired,
            label: PropTypes.string.isRequired,
        })
    ).isRequired,
    activeZone: PropTypes.string.isRequired,
    onZoneChange: PropTypes.func.isRequired,
};

export default ZoneFilter;
