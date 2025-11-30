import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import './Navbar.css';

const Navbar = () => {
    const location = useLocation();
    const [isMenuOpen, setIsMenuOpen] = React.useState(false);

    const isActive = (path) => {
        return location.pathname === path ? 'nav-link active' : 'nav-link';
    };

    const toggleMenu = () => {
        setIsMenuOpen(!isMenuOpen);
    };

    const closeMenu = () => {
        setIsMenuOpen(false);
    };

    return (
        <nav className="navbar">
            <div className="container navbar-container">
                <Link to="/" className="navbar-brand">
                    <span className="brand-icon">T</span>
                    TugaPark
                </Link>

                {/* Hamburger Button */}
                <button 
                    className="navbar-toggle"
                    onClick={toggleMenu}
                    aria-label="Toggle menu"
                >
                    <span className={`hamburger ${isMenuOpen ? 'active' : ''}`}>
                        <span></span>
                        <span></span>
                        <span></span>
                    </span>
                </button>

                {/* Desktop Navigation */}
                <div className={`navbar-links ${isMenuOpen ? 'mobile-open' : ''}`}>
                    <Link to="/" className={isActive('/')} onClick={closeMenu}>Home</Link>
                    <Link to="/live" className={isActive('/live')} onClick={closeMenu}>Monitor</Link>
                    <Link to="/reservar" className={isActive('/reservar')} onClick={closeMenu}>Reservar</Link>
                    <Link to="/login" className={isActive('/login')} onClick={closeMenu}>Login</Link>
                </div>
            </div>
        </nav>
    );
};

export default Navbar;
