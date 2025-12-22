// NotificationBell - Real-time notification system for TugaPark
// Shows violation alerts and other notifications via WebSocket

import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { api } from '../api';
import './NotificationBell.css';

const NotificationBell = () => {
 const { isAdmin, isAuthenticated, user } = useAuth();
 const [notifications, setNotifications] = useState([]);
 const [unreadCount, setUnreadCount] = useState(0);
 const [isOpen, setIsOpen] = useState(false);
 const [wsConnected, setWsConnected] = useState(false);
 const wsRef = useRef(null);
 const dropdownRef = useRef(null);
 const reconnectTimeoutRef = useRef(null);
 const shownToastsRef = useRef(new Set()); // Track shown toasts to prevent duplicates

 // Close dropdown when clicking outside
 useEffect(() => {
 const handleClickOutside = (event) => {
 if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
 setIsOpen(false);
 }
 };
 document.addEventListener('mousedown', handleClickOutside);
 return () => document.removeEventListener('mousedown', handleClickOutside);
 }, []);

 // Fetch notifications from API
 const fetchNotifications = useCallback(async () => {
 if (!isAuthenticated()) return;

 try {
 const data = await api('/api/user/notifications');
 if (data && data.notifications) {
 setNotifications(data.notifications);
 setUnreadCount(data.notifications.filter(n => !n.read).length);
 }
 } catch (err) {
 console.error('Failed to fetch notifications:', err);
 }
 }, [isAuthenticated]);

 // Connect to WebSocket for real-time notifications
 const connectWebSocket = useCallback(() => {
 if (!isAuthenticated() || wsRef.current?.readyState === WebSocket.OPEN) return;

 const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
 const wsUrl = `${protocol}//${window.location.host}/ws`;

 const ws = new WebSocket(wsUrl);
 wsRef.current = ws;

 ws.onopen = () => {
 console.log('[NotificationBell] WebSocket connected');
 setWsConnected(true);
 };

 ws.onmessage = (event) => {
 try {
 const data = JSON.parse(event.data);

 // Check if this is a notification message
 if (data.type === 'notification' && data.data) {
 const notification = data.data;
 console.log('[NotificationBell] Received notification:', notification);

 // Add to notifications list
 setNotifications(prev => [{
 id: Date.now(),
 title: notification.title,
 body: notification.body,
 notification_type: notification.notification_type,
 data: notification,
 created_at: notification.timestamp || new Date().toISOString(),
 read: false
 }, ...prev.slice(0, 49)]); // Keep last 50

 setUnreadCount(prev => prev + 1);

 // Show browser notification if supported and violation
 if (notification.notification_type === 'violation_alert' && Notification.permission === 'granted') {
 new Notification(notification.title, {
 body: notification.body,
 icon: '/favicon.ico',
 tag: `violation-${notification.spot}`
 });
 }

 // Show toast for violation alerts (only if not already shown)
 if (notification.notification_type === 'violation_alert') {
 // Create unique key based on spot and plate only (no timestamp)
 // This ensures we don't show duplicates even if timestamps differ slightly
 const toastKey = `${notification.spot}-${notification.intruder_plate}`;

 // Check both DOM and our Set to prevent duplicates
 if (!shownToastsRef.current.has(toastKey)) {
 shownToastsRef.current.add(toastKey);
 showToast(notification, toastKey);

 // Clean up key after 60 seconds to allow new notification for same spot
 setTimeout(() => {
 shownToastsRef.current.delete(toastKey);
 }, 60000);
 } else {
 console.log('[NotificationBell] Skipping duplicate toast for:', toastKey);
 }
 }
 }
 } catch (e) {
 // Not a notification message, ignore
 }
 };

 ws.onerror = (error) => {
 console.error('[NotificationBell] WebSocket error:', error);
 setWsConnected(false);
 };

 ws.onclose = () => {
 console.log('[NotificationBell] WebSocket disconnected');
 setWsConnected(false);

 // Reconnect after 5 seconds
 reconnectTimeoutRef.current = setTimeout(() => {
 if (isAuthenticated()) {
 connectWebSocket();
 }
 }, 5000);
 };
 }, [isAuthenticated]);

 // Show toast notification
 const showToast = (notification, toastKey = null) => {
 const toast = document.createElement('div');
 toast.className = 'notification-toast violation';
 if (toastKey) {
 toast.setAttribute('data-toast-key', toastKey);
 }
 toast.innerHTML = `
 <div class="toast-icon">!</div>
 <div class="toast-content">
 <div class="toast-title">${notification.title}</div>
 <div class="toast-body">${notification.body}</div>
 </div>
 <button class="toast-close" onclick="this.parentElement.remove()">x</button>
 `;

 let container = document.querySelector('.toast-container');
 if (!container) {
 container = document.createElement('div');
 container.className = 'toast-container';
 document.body.appendChild(container);
 }

 container.appendChild(toast);

 // Auto-remove after 10 seconds
 setTimeout(() => {
 toast.classList.add('fade-out');
 setTimeout(() => toast.remove(), 300);
 }, 10000);
 };

 // Request notification permission
 useEffect(() => {
 if ('Notification' in window && Notification.permission === 'default') {
 Notification.requestPermission();
 }
 }, []);

 // Initialize
 useEffect(() => {
 if (isAuthenticated()) {
 fetchNotifications();
 connectWebSocket();
 }

 return () => {
 if (wsRef.current) {
 wsRef.current.close();
 }
 if (reconnectTimeoutRef.current) {
 clearTimeout(reconnectTimeoutRef.current);
 }
 };
 }, [isAuthenticated, fetchNotifications, connectWebSocket]);

 // Mark notification as read
 const markAsRead = async (notificationId) => {
 try {
 await api(`/api/user/notifications/${notificationId}/read`, { method: 'POST' });
 setNotifications(prev =>
 prev.map(n => n.id === notificationId ? { ...n, read: true } : n)
 );
 setUnreadCount(prev => Math.max(0, prev - 1));
 } catch (err) {
 console.error('Failed to mark notification as read:', err);
 }
 };

 // Mark all as read
 const markAllAsRead = async () => {
 try {
 await api('/api/user/notifications/read-all', { method: 'POST' });
 setNotifications(prev => prev.map(n => ({ ...n, read: true })));
 setUnreadCount(0);
 } catch (err) {
 console.error('Failed to mark all as read:', err);
 }
 };

 // Clear all notifications
 const clearAll = async () => {
 try {
 await api('/api/user/notifications/clear', { method: 'DELETE' });
 setNotifications([]);
 setUnreadCount(0);
 } catch (err) {
 console.error('Failed to clear notifications:', err);
 }
 };

 // Get notification icon based on type
 const getNotificationIcon = (type) => {
 switch (type) {
 case 'violation_alert': return '!';
 case 'reservation_violation': return '!';
 case 'fine': return '$';
 case 'payment': return '$';
 default: return 'i';
 }
 };

 // Format time ago
 const formatTimeAgo = (timestamp) => {
 const now = new Date();
 const date = new Date(timestamp);
 const diffMs = now - date;
 const diffMins = Math.floor(diffMs / 60000);
 const diffHours = Math.floor(diffMins / 60);
 const diffDays = Math.floor(diffHours / 24);

 if (diffMins < 1) return 'now';
 if (diffMins < 60) return `${diffMins}m`;
 if (diffHours < 24) return `${diffHours}h`;
 return `${diffDays}d`;
 };

 // Only show for authenticated users (admins see all, users see their own)
 if (!isAuthenticated()) return null;

 return (
 <div className="notification-bell-wrapper" ref={dropdownRef}>
 <button
 className={`notification-bell-btn ${unreadCount > 0 ? 'has-notifications' : ''}`}
 onClick={() => setIsOpen(!isOpen)}
 title={`${unreadCount} notificações não lidas`}
 >
 <svg viewBox="0 0 24 24" fill="currentColor" width="22" height="22">
 <path d="M12 22c1.1 0 2-.9 2-2h-4c0 1.1.9 2 2 2zm6-6v-5c0-3.07-1.63-5.64-4.5-6.32V4c0-.83-.67-1.5-1.5-1.5s-1.5.67-1.5 1.5v.68C7.64 5.36 6 7.92 6 11v5l-2 2v1h16v-1l-2-2zm-2 1H8v-6c0-2.48 1.51-4.5 4-4.5s4 2.02 4 4.5v6z" />
 </svg>
 {unreadCount > 0 && (
 <span className="notification-badge">
 {unreadCount > 99 ? '99+' : unreadCount}
 </span>
 )}
 {wsConnected && <span className="ws-indicator"></span>}
 </button>

 {isOpen && (
 <div className="notification-dropdown">
 <div className="notification-header">
 <h3>Notifications</h3>
 <div className="notification-actions">
 {unreadCount > 0 && (
 <button onClick={markAllAsRead} className="action-btn">
 Mark all read
 </button>
 )}
 {notifications.length > 0 && (
 <button onClick={clearAll} className="action-btn danger">
 Clear
 </button>
 )}
 </div>
 </div>

 <div className="notification-list">
 {notifications.length === 0 ? (
 <div className="notification-empty">
 <span className="empty-icon">-</span>
 <p>No notifications</p>
 </div>
 ) : (
 notifications.map((notification) => (
 <div
 key={notification.id}
 className={`notification-item ${notification.read ? 'read' : 'unread'} ${notification.notification_type}`}
 onClick={() => !notification.read && markAsRead(notification.id)}
 >
 <span className="notification-icon">
 {getNotificationIcon(notification.notification_type)}
 </span>
 <div className="notification-content">
 <div className="notification-title">{notification.title}</div>
 <div className="notification-body">{notification.body}</div>
 <div className="notification-time">
 {formatTimeAgo(notification.created_at)}
 </div>
 </div>
 {!notification.read && <span className="unread-dot"></span>}
 </div>
 ))
 )}
 </div>
 </div>
 )}
 </div>
 );
};

export default NotificationBell;
