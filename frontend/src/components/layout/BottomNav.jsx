import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import './BottomNav.css';

const BottomNav = () => {
 const location = useLocation();

 const isActive = (path) => location.pathname === path;

 return (
 <nav className="bottom-nav">
 <Link to="/" className={`nav-item ${isActive('/') ? 'active' : ''}`}>
 <svg viewBox="0 0 24 24" fill="currentColor" className="nav-icon">
 <path d="M10 20v-6h4v6h5v-8h3L12 3 2 12h3v8z" />
 </svg>
 <span>Home</span>
 </Link>

 <Link to="/live" className={`nav-item ${isActive('/live') ? 'active' : ''}`}>
 <svg viewBox="0 0 24 24" fill="currentColor" className="nav-icon">
 <path d="M20.5 3l-.16.03L15 5.1 9 3 3.36 4.9c-.21.07-.36.25-.36.48V20.5c0 .28.22.5.5.5l.16-.03L9 18.9l6 2.1 5.64-1.9c.21-.07.36-.25.36-.48V3.5c0-.28-.22-.5-.5-.5zM15 19l-6-2.11V5l6 2.11V19z" />
 </svg>
 <span>Mapa</span>
 </Link>

 <Link to="/reservar" className={`nav-item ${isActive('/reservar') ? 'active' : ''}`}>
 <svg viewBox="0 0 24 24" fill="currentColor" className="nav-icon">
 <path d="M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z" />
 </svg>
 <span>Reservar</span>
 </Link>

 <Link to="/login" className={`nav-item ${isActive('/login') ? 'active' : ''}`}>
 <svg viewBox="0 0 24 24" fill="currentColor" className="nav-icon">
 <path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z" />
 </svg>
 <span>Perfil</span>
 </Link>
 </nav>
 );
};

export default BottomNav;
