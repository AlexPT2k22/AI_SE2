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

    // Get page title based on current route
    const getPageTitle = () => {
        switch (location.pathname) {
            case '/': return 'TugaPark';
            case '/live': return 'Monitor ao Vivo';
            case '/reservar': return 'Reservar';
            case '/estado': return 'Minhas Sessões';
            case '/admin': return 'Administração';
            case '/login': return 'Login';
            default: return 'TugaPark';
        }
    };

    return (
        <header className="navbar">
            <div className="navbar-container">
                {/* Mobile Header */}
                <div className="navbar-mobile">
                    <button className="navbar-btn" onClick={() => window.history.back()}>
                        <svg viewBox="0 0 24 24" fill="currentColor" width="24" height="24">
                            <path d="M20 11H7.83l5.59-5.59L12 4l-8 8 8 8 1.41-1.41L7.83 13H20v-2z" />
                        </svg>
                    </button>
                    <h1 className="navbar-title">{getPageTitle()}</h1>
                    <button className="navbar-btn" onClick={toggleMenu}>
                        <svg viewBox="0 0 24 24" fill="currentColor" width="24" height="24">
                            <circle cx="12" cy="12" r="2" />
                            <circle cx="12" cy="5" r="2" />
                            <circle cx="12" cy="19" r="2" />
                        </svg>
                    </button>
                </div>

                {/* Desktop Navigation */}
                <nav className={`navbar-links ${isMenuOpen ? 'mobile-open' : ''}`}>
                    <Link to="/" className="navbar-brand" onClick={closeMenu}>
                        <span className="brand-icon">🅿️</span>
                        TugaPark
                    </Link>
                    <div className="nav-links-group">
                        <Link to="/" className={isActive('/')} onClick={closeMenu}>Home</Link>
                        <Link to="/live" className={isActive('/live')} onClick={closeMenu}>Monitor</Link>
                        <Link to="/reservar" className={isActive('/reservar')} onClick={closeMenu}>Reservar</Link>
                        <Link to="/estado" className={isActive('/estado')} onClick={closeMenu}>Sessões</Link>
                        <Link to="/admin" className={isActive('/admin')} onClick={closeMenu}>Admin</Link>
                        <Link to="/login" className={isActive('/login')} onClick={closeMenu}>Login</Link>
                    </div>
                </nav>
            </div>
        </header>
    );
};

export default Navbar;
