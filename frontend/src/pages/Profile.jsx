// Página de Perfil - TugaPark v2.0
// Gestão de veículos e cartões de pagamento

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

    // Formulário de novo veículo
    const [showVehicleForm, setShowVehicleForm] = useState(false);
    const [newVehicle, setNewVehicle] = useState({
        plate: '', brand: '', model: '', color: '', is_primary: false
    });

    // Formulário de novo cartão
    const [showCardForm, setShowCardForm] = useState(false);
    const [newCard, setNewCard] = useState({
        card_type: 'visa',
        card_number: '',
        card_holder_name: '',
        expiry_month: '',
        expiry_year: '',
        is_default: false
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
            setError('Erro ao carregar dados: ' + err.message);
        } finally {
            setLoading(false);
        }
    };

    // Adicionar veículo
    const addVehicle = async (e) => {
        e.preventDefault();
        setError('');
        try {
            await apiPost('/api/user/vehicles', newVehicle);
            setMessage('Veículo adicionado com sucesso!');
            setShowVehicleForm(false);
            setNewVehicle({ plate: '', brand: '', model: '', color: '', is_primary: false });
            loadData();
            refreshUser();
        } catch (err) {
            setError(err.message);
        }
    };

    // Remover veículo
    const removeVehicle = async (id) => {
        if (!confirm('Tem a certeza que deseja remover este veículo?')) return;
        try {
            await apiDelete(`/api/user/vehicles/${id}`);
            setMessage('Veículo removido.');
            loadData();
            refreshUser();
        } catch (err) {
            setError(err.message);
        }
    };

    // Adicionar cartão
    const addCard = async (e) => {
        e.preventDefault();
        setError('');
        try {
            await apiPost('/api/user/payment-methods', newCard);
            setMessage('Cartão adicionado com sucesso!');
            setShowCardForm(false);
            setNewCard({
                card_type: 'visa',
                card_number: '',
                card_holder_name: '',
                expiry_month: '',
                expiry_year: '',
                is_default: false
            });
            loadData();
        } catch (err) {
            setError(err.message);
        }
    };

    // Remover cartão
    const removeCard = async (id) => {
        if (!confirm('Tem a certeza que deseja remover este cartão?')) return;
        try {
            await apiDelete(`/api/user/payment-methods/${id}`);
            setMessage('Cartão removido.');
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
        <div className="flex flex-col gap-6">
            {/* Header */}
            <Card className="p-4">
                <div className="flex justify-between items-center">
                    <div>
                        <h1 style={{ fontSize: 'var(--font-size-2xl)', fontWeight: 'bold' }}>
                            My Profile
                        </h1>
                        <p style={{ color: 'var(--color-text-secondary)', marginTop: 'var(--spacing-1)' }}>
                            {user?.email} • <span style={{
                                backgroundColor: user?.role === 'admin' ? 'var(--color-primary)' : 'var(--color-success)',
                                padding: '2px 8px',
                                borderRadius: '4px',
                                fontSize: 'var(--font-size-xs)'
                            }}>
                                {user?.role === 'admin' ? 'Admin' : 'Cliente'}
                            </span>
                        </p>
                    </div>
                    <Button variant="ghost" onClick={handleLogout} style={{ color: 'var(--color-danger)' }}>
                        Terminar Sessão
                    </Button>
                </div>
            </Card>

            {/* Mensagens */}
            {message && (
                <Card className="p-3" style={{ backgroundColor: 'var(--color-success)', color: 'white' }}>
                    {message}
                    <button onClick={() => setMessage('')} style={{ float: 'right', background: 'none', border: 'none', color: 'white', cursor: 'pointer' }}>×</button>
                </Card>
            )}
            {error && (
                <Card className="p-3" style={{ backgroundColor: 'var(--color-danger)', color: 'white' }}>
                    {error}
                    <button onClick={() => setError('')} style={{ float: 'right', background: 'none', border: 'none', color: 'white', cursor: 'pointer' }}>×</button>
                </Card>
            )}

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(350px, 1fr))', gap: 'var(--spacing-4)' }}>
                {/* Veículos */}
                <Card className="p-4">
                    <div className="flex justify-between items-center" style={{ marginBottom: 'var(--spacing-4)' }}>
                        <h2 style={{ fontSize: 'var(--font-size-lg)', fontWeight: '600' }}>My Vehicles</h2>
                        <Button variant="secondary" onClick={() => setShowVehicleForm(!showVehicleForm)}>
                            {showVehicleForm ? 'Cancelar' : '+ Adicionar'}
                        </Button>
                    </div>

                    {showVehicleForm && (
                        <form onSubmit={addVehicle} className="flex flex-col gap-3" style={{
                            marginBottom: 'var(--spacing-4)',
                            padding: 'var(--spacing-3)',
                            backgroundColor: 'var(--color-bg-secondary)',
                            borderRadius: 'var(--border-radius-md)'
                        }}>
                            <Input
                                label="Matrícula *"
                                placeholder="AA-00-BB"
                                value={newVehicle.plate}
                                onChange={(e) => setNewVehicle({ ...newVehicle, plate: e.target.value })}
                                required
                            />
                            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--spacing-2)' }}>
                                <Input
                                    label="Marca"
                                    placeholder="BMW"
                                    value={newVehicle.brand}
                                    onChange={(e) => setNewVehicle({ ...newVehicle, brand: e.target.value })}
                                />
                                <Input
                                    label="Modelo"
                                    placeholder="Serie 3"
                                    value={newVehicle.model}
                                    onChange={(e) => setNewVehicle({ ...newVehicle, model: e.target.value })}
                                />
                            </div>
                            <Input
                                label="Cor"
                                placeholder="Preto"
                                value={newVehicle.color}
                                onChange={(e) => setNewVehicle({ ...newVehicle, color: e.target.value })}
                            />
                            <label style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: 'var(--font-size-sm)' }}>
                                <input
                                    type="checkbox"
                                    checked={newVehicle.is_primary}
                                    onChange={(e) => setNewVehicle({ ...newVehicle, is_primary: e.target.checked })}
                                />
                                Veículo principal (para login com matrícula)
                            </label>
                            <Button type="submit">Adicionar Veículo</Button>
                        </form>
                    )}

                    {vehicles.length === 0 ? (
                        <p style={{ color: 'var(--color-text-secondary)', fontSize: 'var(--font-size-sm)' }}>
                            Nenhum veículo registado. Adicione o seu primeiro carro!
                        </p>
                    ) : (
                        <div className="flex flex-col gap-2">
                            {vehicles.map(v => (
                                <div key={v.id} style={{
                                    display: 'flex',
                                    justifyContent: 'space-between',
                                    alignItems: 'center',
                                    padding: 'var(--spacing-3)',
                                    backgroundColor: 'var(--color-bg-secondary)',
                                    borderRadius: 'var(--border-radius-md)',
                                    border: v.is_primary ? '2px solid var(--color-primary)' : 'none'
                                }}>
                                    <div>
                                        <div style={{ fontWeight: '600' }}>
                                            {v.plate} {v.is_primary && <span style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-primary)' }}>★ Principal</span>}
                                        </div>
                                        <div style={{ fontSize: 'var(--font-size-sm)', color: 'var(--color-text-secondary)' }}>
                                            {[v.brand, v.model, v.color].filter(Boolean).join(' • ') || 'Sem detalhes'}
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

                {/* Cartões de Pagamento */}
                <Card className="p-4">
                    <div className="flex justify-between items-center" style={{ marginBottom: 'var(--spacing-4)' }}>
                        <h2 style={{ fontSize: 'var(--font-size-lg)', fontWeight: '600' }}>Payment Methods</h2>
                        <Button variant="secondary" onClick={() => setShowCardForm(!showCardForm)}>
                            {showCardForm ? 'Cancelar' : '+ Adicionar'}
                        </Button>
                    </div>

                    {showCardForm && (
                        <form onSubmit={addCard} className="flex flex-col gap-3" style={{
                            marginBottom: 'var(--spacing-4)',
                            padding: 'var(--spacing-3)',
                            backgroundColor: 'var(--color-bg-secondary)',
                            borderRadius: 'var(--border-radius-md)'
                        }}>
                            <div>
                                <label style={{ display: 'block', marginBottom: '4px', fontSize: 'var(--font-size-sm)' }}>Tipo de Cartão</label>
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
                                    <option value="other">Outro</option>
                                </select>
                            </div>
                            <Input
                                label="Número do Cartão *"
                                placeholder="4242 4242 4242 4242"
                                value={newCard.card_number}
                                onChange={(e) => setNewCard({ ...newCard, card_number: e.target.value })}
                                required
                            />
                            <Input
                                label="Nome no Cartão *"
                                placeholder="JOÃO SILVA"
                                value={newCard.card_holder_name}
                                onChange={(e) => setNewCard({ ...newCard, card_holder_name: e.target.value })}
                                required
                            />
                            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--spacing-2)' }}>
                                <Input
                                    type="number"
                                    label="Mês Exp. *"
                                    placeholder="12"
                                    min="1"
                                    max="12"
                                    value={newCard.expiry_month}
                                    onChange={(e) => setNewCard({ ...newCard, expiry_month: parseInt(e.target.value) || '' })}
                                    required
                                />
                                <Input
                                    type="number"
                                    label="Ano Exp. *"
                                    placeholder="2027"
                                    min="2024"
                                    value={newCard.expiry_year}
                                    onChange={(e) => setNewCard({ ...newCard, expiry_year: parseInt(e.target.value) || '' })}
                                    required
                                />
                            </div>
                            <label style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: 'var(--font-size-sm)' }}>
                                <input
                                    type="checkbox"
                                    checked={newCard.is_default}
                                    onChange={(e) => setNewCard({ ...newCard, is_default: e.target.checked })}
                                />
                                Cartão principal (para pagamento automático)
                            </label>
                            <Button type="submit">Adicionar Cartão</Button>
                        </form>
                    )}

                    {paymentMethods.length === 0 ? (
                        <p style={{ color: 'var(--color-text-secondary)', fontSize: 'var(--font-size-sm)' }}>
                            Nenhum cartão registado. Adicione um cartão para pagamento automático na saída!
                        </p>
                    ) : (
                        <div className="flex flex-col gap-2">
                            {paymentMethods.map(pm => (
                                <div key={pm.id} style={{
                                    display: 'flex',
                                    justifyContent: 'space-between',
                                    alignItems: 'center',
                                    padding: 'var(--spacing-3)',
                                    backgroundColor: 'var(--color-bg-secondary)',
                                    borderRadius: 'var(--border-radius-md)',
                                    border: pm.is_default ? '2px solid var(--color-primary)' : 'none'
                                }}>
                                    <div>
                                        <div style={{ fontWeight: '600' }}>
                                            {pm.card_type.toUpperCase()} •••• {pm.card_last_four}
                                            {pm.is_default && <span style={{ marginLeft: '8px', fontSize: 'var(--font-size-xs)', color: 'var(--color-primary)' }}>★ Principal</span>}
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
            <Card className="p-4" style={{ backgroundColor: 'var(--color-bg-secondary)' }}>
                <h3 style={{ fontSize: 'var(--font-size-md)', fontWeight: '600', marginBottom: 'var(--spacing-2)' }}>
                    How does automatic payment work?
                </h3>
                <p style={{ fontSize: 'var(--font-size-sm)', color: 'var(--color-text-secondary)' }}>
                    Quando sair do estacionamento, o valor será automaticamente debitado do seu cartão principal.
                    Receberá uma notificação na app mobile com o comprovativo de pagamento.
                </p>
            </Card>
        </div>
    );
}
