import React from 'react';
import Navbar from './Navbar';
import './Layout.css';

const Layout = ({ children }) => {
    return (
        <div className="layout">
            <Navbar />
            <main className="main-content container">
                {children}
            </main>
            <footer className="footer">
                <div className="container text-center">
                    <p className="text-muted">© 2024 TugaPark. All rights reserved.</p>
                </div>
            </footer>
        </div>
    );
};

export default Layout;
