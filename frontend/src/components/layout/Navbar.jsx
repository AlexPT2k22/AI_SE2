// Navbar - TugaPark v2.0
// Navegação com autenticação e controlo de acesso

import React from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import NotificationBell from '../NotificationBell';
import './Navbar.css';

const Navbar = () => {
    const location = useLocation();
    const navigate = useNavigate();
    const { user, isAdmin, isAuthenticated, logout } = useAuth();
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

    const handleLogout = () => {
        logout();
        closeMenu();
        navigate('/');
    };

    // Get page title based on current route
    const getPageTitle = () => {
        switch (location.pathname) {
            case '/': return 'TugaPark';
            case '/live': return 'Monitor ao Vivo';
            case '/reservar': return 'Reservar';
            case '/estado': return 'Minhas Sessões';
            case '/sessoes': return 'Sessões';
            case '/admin': return 'Administração';
            case '/login': return 'Login';
            case '/perfil': return 'Meu Perfil';
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
                        <span className="brand-icon">P</span>
                        TugaPark
                    </Link>
                    <div className="nav-links-group">
                        <Link to="/" className={isActive('/')} onClick={closeMenu}>Home</Link>

                        {/* Links for admin only */}
                        {isAdmin() && (
                            <Link to="/live" className={isActive('/live')} onClick={closeMenu}>Monitor</Link>
                        )}

                        {/* Links for authenticated users */}
                        {isAuthenticated() && (
                            <>
                                <Link to="/reservar" className={isActive('/reservar')} onClick={closeMenu}>Reserve</Link>
                                <Link to="/sessions" className={isActive('/sessions')} onClick={closeMenu}>Sessions</Link>
                            </>
                        )}
                    </div>

                    {/* Auth section */}
                    <div className="nav-auth">
                        {isAuthenticated() ? (
                            <>
                                <NotificationBell />
                                <Link
                                    to="/perfil"
                                    className={`nav-link user-link ${isActive('/perfil').includes('active') ? 'active' : ''}`}
                                    onClick={closeMenu}
                                >
                                    <span className="user-avatar">
                                        {user?.name?.charAt(0)?.toUpperCase() || '?'}
                                    </span>
                                    <span className="user-name">{user?.name?.split(' ')[0]}</span>
                                    {isAdmin() && <span className="admin-badge">Admin</span>}
                                </Link>
                                <button
                                    onClick={handleLogout}
                                    className="nav-link logout-btn"
                                >
                                    Sign Out
                                </button>
                            </>
                        ) : (
                            <>
                                <Link to="/login" className={isActive('/login')} onClick={closeMenu}>
                                    Sign In
                                </Link>
                                <Link to="/login?register=true" className="nav-link register-link" onClick={closeMenu}>
                                    Sign Up
                                </Link>
                            </>
                        )}
                    </div>
                </nav>
            </div>
        </header>
    );
};

export default Navbar;
