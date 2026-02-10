// Profile Page - TugaPark v2.0
// Vehicle and payment method management

import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { api, apiPost, apiDelete } from '../api';
import Card from '../components/common/Card';
import Button from '../components/common/Button';
import Input from '../components/common/Input';

export default function Profile() {
    const navigate = useNavigate();
    const { user, logout, refreshUser, isAuthenticated } = useAuth();

    const [loading, setLoading] = useState(true);
    const [vehicles, setVehicles] = useState([]);
    const [paymentMethods, setPaymentMethods] = useState([]);
    const [message, setMessage] = useState('');
    const [error, setError] = useState('');

    // Vehicle form
    const [showVehicleForm, setShowVehicleForm] = useState(false);
    const [newVehicle, setNewVehicle] = useState({
        plate: '', brand: '', model: '', color: ''
    });

    // Card form
    const [showCardForm, setShowCardForm] = useState(false);
    const [newCard, setNewCard] = useState({
        card_type: 'visa',
        card_number: '',
        card_holder_name: '',
        expiry_month: '',
        expiry_year: '',
        is_default: true,  // Always default since only 1 card allowed
        auto_pay: false    // Automatic payment on exit
    });

    useEffect(() => {
        if (!isAuthenticated()) {
            navigate('/login');
            return;
        }
        loadData();
    }, [user, navigate, isAuthenticated]);

    const loadData = async () => {
        setLoading(true);
        try {
            const [vehiclesRes, methodsRes] = await Promise.all([
                api('/api/user/vehicles'),
                api('/api/user/payment-methods')
            ]);
            setVehicles(vehiclesRes.vehicles || []);
            setPaymentMethods(methodsRes.payment_methods || []);
        } catch (err) {
            setError('Error loading data: ' + err.message);
        } finally {
            setLoading(false);
        }
    };

    // Add vehicle
    const addVehicle = async (e) => {
        e.preventDefault();
        setError('');
        try {
            await apiPost('/api/user/vehicles', newVehicle);
            setMessage('Vehicle added successfully!');
            setShowVehicleForm(false);
            setNewVehicle({ plate: '', brand: '', model: '', color: '' });
            loadData();
            refreshUser();
        } catch (err) {
            setError(err.message);
        }
    };

    // Remove vehicle
    const removeVehicle = async (id) => {
        if (!confirm('Are you sure you want to remove this vehicle?')) return;
        try {
            await apiDelete(`/api/user/vehicles/${id}`);
            setMessage('Vehicle removed.');
            loadData();
            refreshUser();
        } catch (err) {
            setError(err.message);
        }
    };

    // Add card
    const addCard = async (e) => {
        e.preventDefault();
        setError('');
        try {
            await apiPost('/api/user/payment-methods', newCard);
            setMessage('Card added successfully!');
            setShowCardForm(false);
            setNewCard({
                card_type: 'visa',
                card_number: '',
                card_holder_name: '',
                expiry_month: '',
                expiry_year: '',
                is_default: true
            });
            loadData();
        } catch (err) {
            setError(err.message);
        }
    };

    // Remove card
    const removeCard = async (id) => {
        if (!confirm('Are you sure you want to remove this card?')) return;
        try {
            await apiDelete(`/api/user/payment-methods/${id}`);
            setMessage('Card removed.');
            loadData();
        } catch (err) {
            setError(err.message);
        }
    };

    const handleLogout = () => {
        logout();
        navigate('/login');
    };

    if (loading) {
        return (
            <div className="flex justify-center items-center" style={{ minHeight: '50vh' }}>
                <p>A carregar...</p>
            </div>
        );
    }

    return (
        <div style={{ padding: 'var(--spacing-4)', maxWidth: '1200px', margin: '0 auto' }}>
            <div className="flex flex-col" style={{ gap: 'var(--spacing-6)' }}>
                {/* Header */}
                <Card style={{ padding: 'var(--spacing-6)' }}>
                    <div className="flex justify-between items-center">
                        <div>
                            <h1 style={{ fontSize: 'var(--font-size-2xl)', fontWeight: 'bold' }}>
                                {user?.full_name || 'My Profile'}
                            </h1>
                            <p style={{ color: 'var(--color-text-secondary)', marginTop: 'var(--spacing-1)' }}>
                                {user?.email} • <span style={{
                                    backgroundColor: user?.role === 'admin' ? 'var(--color-primary)' : 'var(--color-success)',
                                    padding: '2px 8px',
                                    borderRadius: '4px',
                                    fontSize: 'var(--font-size-xs)'
                                }}>
                                    {user?.role === 'admin' ? 'Admin' : 'Client'}
                                </span>
                            </p>
                        </div>
                        <Button variant="ghost" onClick={handleLogout} style={{ color: 'var(--color-danger)' }}>
                            Sign Out
                        </Button>
                    </div>
                </Card>

                {/* Messages */}
                {message && (
                    <Card style={{ padding: 'var(--spacing-4)', backgroundColor: 'var(--color-success)', color: 'white' }}>
                        {message}
                        <button onClick={() => setMessage('')} style={{ float: 'right', background: 'none', border: 'none', color: 'white', cursor: 'pointer', fontSize: '18px' }}>×</button>
                    </Card>
                )}
                {error && (
                    <Card style={{ padding: 'var(--spacing-4)', backgroundColor: 'var(--color-danger)', color: 'white' }}>
                        {error}
                        <button onClick={() => setError('')} style={{ float: 'right', background: 'none', border: 'none', color: 'white', cursor: 'pointer', fontSize: '18px' }}>×</button>
                    </Card>
                )}

                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(400px, 1fr))', gap: 'var(--spacing-6)' }}>
                    {/* Vehicles */}
                    <Card style={{ padding: 'var(--spacing-6)' }}>
                        <div className="flex justify-between items-center" style={{ marginBottom: 'var(--spacing-4)' }}>
                            <h2 style={{ fontSize: 'var(--font-size-lg)', fontWeight: '600' }}>My Vehicles</h2>
                            <Button variant="secondary" onClick={() => setShowVehicleForm(!showVehicleForm)}>
                                {showVehicleForm ? 'Cancel' : '+ Add'}
                            </Button>
                        </div>

                        {showVehicleForm && (
                            <form onSubmit={addVehicle} className="flex flex-col gap-3" style={{
                                marginBottom: 'var(--spacing-6)',
                                padding: 'var(--spacing-4)',
                                backgroundColor: 'var(--color-bg-secondary)',
                                borderRadius: 'var(--border-radius-md)'
                            }}>
                                <Input
                                    label="License Plate *"
                                    placeholder="AA-00-BB"
                                    value={newVehicle.plate}
                                    onChange={(e) => setNewVehicle({ ...newVehicle, plate: e.target.value })}
                                    required
                                />
                                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--spacing-2)' }}>
                                    <Input
                                        label="Brand"
                                        placeholder="BMW"
                                        value={newVehicle.brand}
                                        onChange={(e) => setNewVehicle({ ...newVehicle, brand: e.target.value })}
                                    />
                                    <Input
                                        label="Model"
                                        placeholder="Series 3"
                                        value={newVehicle.model}
                                        onChange={(e) => setNewVehicle({ ...newVehicle, model: e.target.value })}
                                    />
                                </div>
                                <Input
                                    label="Color"
                                    placeholder="Black"
                                    value={newVehicle.color}
                                    onChange={(e) => setNewVehicle({ ...newVehicle, color: e.target.value })}
                                />
                                <Button type="submit" style={{ marginTop: 'var(--spacing-4)' }}>Add Vehicle</Button>
                            </form>
                        )}

                        {vehicles.length === 0 ? (
                            <p style={{ color: 'var(--color-text-secondary)', fontSize: 'var(--font-size-sm)' }}>
                                No vehicles registered. Add your first car!
                            </p>
                        ) : (
                            <div className="flex flex-col gap-2">
                                {vehicles.map(v => (
                                    <div key={v.id} style={{
                                        display: 'flex',
                                        justifyContent: 'space-between',
                                        alignItems: 'center',
                                        padding: 'var(--spacing-4)',
                                        backgroundColor: 'var(--color-bg-secondary)',
                                        borderRadius: 'var(--border-radius-md)'
                                    }}>
                                        <div>
                                            <div style={{ fontWeight: '600' }}>
                                                {v.plate}
                                            </div>
                                            <div style={{ fontSize: 'var(--font-size-sm)', color: 'var(--color-text-secondary)' }}>
                                                {[v.brand, v.model, v.color].filter(Boolean).join(' • ') || 'No details'}
                                            </div>
                                        </div>
                                        <button
                                            onClick={() => removeVehicle(v.id)}
                                            style={{
                                                background: 'none',
                                                border: 'none',
                                                color: 'var(--color-danger)',
                                                cursor: 'pointer',
                                                fontSize: 'var(--font-size-lg)'
                                            }}
                                        >
                                            X
                                        </button>
                                    </div>
                                ))}
                            </div>
                        )}
                    </Card>

                    {/* Payment Method */}
                    <Card style={{ padding: 'var(--spacing-6)' }}>
                        <div className="flex justify-between items-center" style={{ marginBottom: 'var(--spacing-4)' }}>
                            <h2 style={{ fontSize: 'var(--font-size-lg)', fontWeight: '600' }}>Payment Method</h2>
                            {paymentMethods.length === 0 && (
                                <Button variant="secondary" onClick={() => setShowCardForm(!showCardForm)}>
                                    {showCardForm ? 'Cancel' : '+ Add'}
                                </Button>
                            )}
                        </div>

                        {showCardForm && (
                            <form onSubmit={addCard} className="flex flex-col gap-3" style={{
                                marginBottom: 'var(--spacing-6)',
                                padding: 'var(--spacing-4)',
                                backgroundColor: 'var(--color-bg-secondary)',
                                borderRadius: 'var(--border-radius-md)'
                            }}>
                                <div>
                                    <label style={{ display: 'block', marginBottom: '4px', fontSize: 'var(--font-size-sm)' }}>Card Type</label>
                                    <select
                                        value={newCard.card_type}
                                        onChange={(e) => setNewCard({ ...newCard, card_type: e.target.value })}
                                        style={{
                                            width: '100%',
                                            padding: '8px 12px',
                                            borderRadius: 'var(--border-radius-md)',
                                            border: '1px solid var(--color-border)',
                                            backgroundColor: 'var(--color-bg-primary)',
                                            color: 'var(--color-text-primary)'
                                        }}
                                    >
                                        <option value="visa">Visa</option>
                                        <option value="mastercard">Mastercard</option>
                                        <option value="amex">American Express</option>
                                        <option value="other">Other</option>
                                    </select>
                                </div>
                                <Input
                                    label="Card Number *"
                                    placeholder="4242 4242 4242 4242"
                                    value={newCard.card_number}
                                    onChange={(e) => setNewCard({ ...newCard, card_number: e.target.value })}
                                    required
                                />
                                <Input
                                    label="Name on Card *"
                                    placeholder="JOHN SMITH"
                                    value={newCard.card_holder_name}
                                    onChange={(e) => setNewCard({ ...newCard, card_holder_name: e.target.value })}
                                    required
                                />
                                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--spacing-2)' }}>
                                    <Input
                                        type="number"
                                        label="Exp. Month *"
                                        placeholder="12"
                                        min="1"
                                        max="12"
                                        value={newCard.expiry_month}
                                        onChange={(e) => setNewCard({ ...newCard, expiry_month: parseInt(e.target.value) || '' })}
                                        required
                                    />
                                    <Input
                                        type="number"
                                        label="Exp. Year *"
                                        placeholder="2027"
                                        min="2024"
                                        value={newCard.expiry_year}
                                        onChange={(e) => setNewCard({ ...newCard, expiry_year: parseInt(e.target.value) || '' })}
                                        required
                                    />
                                </div>
                                <div style={{
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: 'var(--spacing-3)',
                                    padding: 'var(--spacing-3)',
                                    backgroundColor: 'var(--color-surface)',
                                    borderRadius: 'var(--border-radius-md)',
                                    marginTop: 'var(--spacing-2)'
                                }}>
                                    <input
                                        type="checkbox"
                                        id="auto_pay"
                                        checked={newCard.auto_pay}
                                        onChange={(e) => setNewCard({ ...newCard, auto_pay: e.target.checked })}
                                        style={{ width: '18px', height: '18px', cursor: 'pointer' }}
                                    />
                                    <label htmlFor="auto_pay" style={{ cursor: 'pointer' }}>
                                        <span style={{ fontWeight: '600' }}>Enable Automatic Payment</span>
                                        <br />
                                        <span style={{ fontSize: 'var(--font-size-sm)', color: 'var(--color-text-secondary)' }}>
                                            Your card will be charged automatically when you exit the parking
                                        </span>
                                    </label>
                                </div>
                                <Button type="submit" style={{ marginTop: 'var(--spacing-4)' }}>Add Card</Button>
                            </form>
                        )}

                        {paymentMethods.length === 0 ? (
                            <p style={{ color: 'var(--color-text-secondary)', fontSize: 'var(--font-size-sm)' }}>
                                No card registered. Add a card for automatic payment on exit!
                            </p>
                        ) : (
                            <div className="flex flex-col gap-2">
                                {paymentMethods.slice(0, 1).map(pm => (
                                    <div key={pm.id} style={{
                                        display: 'flex',
                                        justifyContent: 'space-between',
                                        alignItems: 'center',
                                        padding: 'var(--spacing-4)',
                                        backgroundColor: 'var(--color-bg-secondary)',
                                        borderRadius: 'var(--border-radius-md)'
                                    }}>
                                        <div>
                                            <div style={{ fontWeight: '600' }}>
                                                {pm.card_type.toUpperCase()} •••• {pm.card_last_four}
                                                {pm.auto_pay && (
                                                    <span style={{
                                                        marginLeft: '8px',
                                                        backgroundColor: 'var(--color-success)',
                                                        color: 'white',
                                                        padding: '2px 8px',
                                                        borderRadius: '4px',
                                                        fontSize: 'var(--font-size-xs)'
                                                    }}>AUTO PAY</span>
                                                )}
                                            </div>
                                            <div style={{ fontSize: 'var(--font-size-sm)', color: 'var(--color-text-secondary)' }}>
                                                {pm.card_holder_name} • Exp: {pm.expiry_month}/{pm.expiry_year}
                                            </div>
                                        </div>
                                        <button
                                            onClick={() => removeCard(pm.id)}
                                            style={{
                                                background: 'none',
                                                border: 'none',
                                                color: 'var(--color-danger)',
                                                cursor: 'pointer',
                                                fontSize: 'var(--font-size-lg)'
                                            }}
                                        >
                                            X
                                        </button>
                                    </div>
                                ))}
                            </div>
                        )}
                    </Card>
                </div>

                {/* Info */}
                <Card style={{ padding: 'var(--spacing-6)', backgroundColor: 'var(--color-bg-secondary)' }}>
                    <h3 style={{ fontSize: 'var(--font-size-md)', fontWeight: '600', marginBottom: 'var(--spacing-2)' }}>
                        How does automatic payment work?
                    </h3>
                    <p style={{ fontSize: 'var(--font-size-sm)', color: 'var(--color-text-secondary)' }}>
                        When you exit the parking lot, the amount will be automatically debited from your primary card.
                        You will receive a notification in the mobile app with the payment receipt.
                    </p>
                </Card>
            </div>
        </div>
    );
}
