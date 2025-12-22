import React from 'react';
import Navbar from './Navbar';
import BottomNav from './BottomNav';
import './Layout.css';

const Layout = ({ children }) => {
 return (
 <div className="layout">
 <Navbar />
 <main className="main-content">
 <div className="container">
 {children}
 </div>
 </main>
 <BottomNav />
 </div>
 );
};

export default Layout;
