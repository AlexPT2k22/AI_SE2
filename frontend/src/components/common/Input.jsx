import React from 'react';
import PropTypes from 'prop-types';
import './Input.css';

const Input = ({ label, error, className = '', ...props }) => {
    return (
        <div className={`input-wrapper ${className}`}>
            {label && <label className="input-label">{label}</label>}
            <input className={`input ${error ? 'input-error' : ''}`} {...props} />
            {error && <span className="input-error-message">{error}</span>}
        </div>
    );
};

Input.propTypes = {
    label: PropTypes.string,
    error: PropTypes.string,
    className: PropTypes.string,
};

export default Input;
