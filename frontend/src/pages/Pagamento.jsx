// Pagamento Page - Search by plate and pay (Public - no login required)
import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../api.js';
import Card from '../components/common/Card';
import Button from '../components/common/Button';
import Input from '../components/common/Input';

export default function Pagamento() {
    const navigate = useNavigate();
    const [plate, setPlate] = useState('');
    const [session, setSession] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    const [paymentMethod, setPaymentMethod] = useState('card');
    const [processing, setProcessing] = useState(false);
    const [success, setSuccess] = useState(false);

    const searchSession = async () => {
        if (!plate.trim()) {
            setError('Introduza a matrícula');
            return;
        }

        setLoading(true);
        setError('');
        setSession(null);

        try {
            const data = await api(`/api/sessions?plate=${encodeURIComponent(plate.toUpperCase())}&status=open&limit=1`);

            if (!data.sessions || data.sessions.length === 0) {
                setError('Nenhuma sessão aberta encontrada para esta matrícula');
                return;
            }

            setSession(data.sessions[0]);
        } catch (e) {
            setError(e.message || 'Erro ao procurar sessão');
        } finally {
            setLoading(false);
        }
    };

    const handlePayment = async () => {
        if (!session) return;

        setProcessing(true);
        setError('');

        // Calculate amount based on time
        const entry = new Date(session.entry_time);
        const now = new Date();
        const diffMs = now - entry;
        const amount = Math.max(0.50, (diffMs / 3600000) * 1.50);

        try {
            await api('/api/payments', {
                method: 'POST',
                body: JSON.stringify({
                    session_id: session.id,
                    amount: parseFloat(amount.toFixed(2)),
                    method: paymentMethod
                })
            });

            setSuccess(true);
        } catch (e) {
            setError(e.message || 'Erro no pagamento');
        } finally {
            setProcessing(false);
        }
    };

    const formatDuration = (entryTime) => {
        const entry = new Date(entryTime);
        const now = new Date();
        const diffMs = now - entry;
        const hours = Math.floor(diffMs / 3600000);
        const mins = Math.floor((diffMs % 3600000) / 60000);
        return `${hours}h ${mins}min`;
    };

    const calculateAmount = (entryTime) => {
        const entry = new Date(entryTime);
        const now = new Date();
        const diffMs = now - entry;
        return Math.max(0.50, (diffMs / 3600000) * 1.50).toFixed(2);
    };

    if (success) {
        return (
            <div style={{ maxWidth: '500px', margin: '0 auto', padding: 'var(--spacing-4)' }}>
                <Card style={{ padding: 'var(--spacing-6)', textAlign: 'center' }}>
                    <div style={{ fontSize: '4rem', marginBottom: 'var(--spacing-4)' }}>✅</div>
                    <h2 style={{ fontSize: 'var(--font-size-2xl)', fontWeight: 'bold', marginBottom: 'var(--spacing-2)', color: 'var(--color-success)' }}>
                        Pagamento Concluído!
                    </h2>
                    <p style={{ color: 'var(--color-text-secondary)', marginBottom: 'var(--spacing-4)' }}>
                        O pagamento foi processado com sucesso.
                    </p>
                    <div style={{
                        backgroundColor: 'rgba(239, 68, 68, 0.1)',
                        border: '2px solid var(--color-danger)',
                        borderRadius: 'var(--border-radius-md)',
                        padding: 'var(--spacing-4)',
                        marginBottom: 'var(--spacing-4)'
                    }}>
                        <p style={{ fontSize: 'var(--font-size-lg)', fontWeight: 'bold', color: 'var(--color-danger)' }}>
                            ⏱️ Tem 10 minutos para sair do parque!
                        </p>
                    </div>
                    <Button onClick={() => navigate('/')} style={{ marginTop: 'var(--spacing-2)' }}>
                        Voltar ao Início
                    </Button>
                </Card>
            </div>
        );
    }

    return (
        <div style={{ maxWidth: '500px', margin: '0 auto', padding: 'var(--spacing-4)' }}>
            <h1 style={{ fontSize: 'var(--font-size-2xl)', fontWeight: 'bold', marginBottom: 'var(--spacing-4)', textAlign: 'center' }}>
                💳 Pagamento de Estacionamento
            </h1>

            {/* Search Section */}
            <Card style={{ marginBottom: 'var(--spacing-4)' }}>
                <h3 style={{ fontSize: 'var(--font-size-lg)', fontWeight: '600', marginBottom: 'var(--spacing-3)' }}>
                    Procurar minha sessão
                </h3>
                <div style={{ display: 'flex', gap: 'var(--spacing-2)' }}>
                    <Input
                        type="text"
                        placeholder="Matrícula (ex: AB-12-CD)"
                        value={plate}
                        onChange={(e) => setPlate(e.target.value.toUpperCase())}
                        onKeyPress={(e) => e.key === 'Enter' && searchSession()}
                        style={{ flex: 1, textTransform: 'uppercase' }}
                    />
                    <Button onClick={searchSession} disabled={loading}>
                        {loading ? '...' : 'Procurar'}
                    </Button>
                </div>
                {error && (
                    <p style={{ color: 'var(--color-danger)', marginTop: 'var(--spacing-2)', fontSize: 'var(--font-size-sm)' }}>
                        {error}
                    </p>
                )}
            </Card>

            {/* Session Details */}
            {session && (
                <>
                    <Card style={{ marginBottom: 'var(--spacing-4)' }}>
                        <h3 style={{ fontSize: 'var(--font-size-lg)', fontWeight: '600', marginBottom: 'var(--spacing-3)' }}>
                            Detalhes da Sessão
                        </h3>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--spacing-2)' }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', padding: 'var(--spacing-2)', borderBottom: '1px solid var(--color-surface-hover)' }}>
                                <span style={{ color: 'var(--color-text-secondary)' }}>Matrícula:</span>
                                <span style={{ fontWeight: 'bold' }}>{session.plate}</span>
                            </div>
                            <div style={{ display: 'flex', justifyContent: 'space-between', padding: 'var(--spacing-2)', borderBottom: '1px solid var(--color-surface-hover)' }}>
                                <span style={{ color: 'var(--color-text-secondary)' }}>Entrada:</span>
                                <span>{new Date(session.entry_time).toLocaleString('pt-PT')}</span>
                            </div>
                            <div style={{ display: 'flex', justifyContent: 'space-between', padding: 'var(--spacing-2)', borderBottom: '1px solid var(--color-surface-hover)' }}>
                                <span style={{ color: 'var(--color-text-secondary)' }}>Vaga:</span>
                                <span>{session.spot || 'Não atribuída'}</span>
                            </div>
                            <div style={{ display: 'flex', justifyContent: 'space-between', padding: 'var(--spacing-2)', borderBottom: '1px solid var(--color-surface-hover)' }}>
                                <span style={{ color: 'var(--color-text-secondary)' }}>Tempo:</span>
                                <span>{formatDuration(session.entry_time)}</span>
                            </div>
                            <div style={{ display: 'flex', justifyContent: 'space-between', padding: 'var(--spacing-2)', borderBottom: '1px solid var(--color-surface-hover)' }}>
                                <span style={{ color: 'var(--color-text-secondary)' }}>Estado:</span>
                                <span style={{
                                    padding: '2px 10px',
                                    borderRadius: '12px',
                                    backgroundColor: session.amount_paid > 0 ? 'var(--color-success)' : 'var(--color-primary)',
                                    fontSize: 'var(--font-size-sm)'
                                }}>
                                    {session.amount_paid > 0 ? 'PAGO' : 'AGUARDA PAGAMENTO'}
                                </span>
                            </div>
                        </div>

                        {/* Amount */}
                        <div style={{
                            textAlign: 'center',
                            marginTop: 'var(--spacing-4)',
                            padding: 'var(--spacing-4)',
                            backgroundColor: 'var(--color-surface)',
                            borderRadius: 'var(--border-radius-md)'
                        }}>
                            <p style={{ color: 'var(--color-text-secondary)', marginBottom: 'var(--spacing-1)' }}>Valor a pagar:</p>
                            <p style={{
                                fontSize: '2.5rem',
                                fontWeight: 'bold',
                                color: session.amount_paid > 0 ? 'var(--color-success)' : 'var(--color-primary)'
                            }}>
                                {session.amount_paid > 0 ? '✅ PAGO' : `€${calculateAmount(session.entry_time)}`}
                            </p>
                        </div>
                    </Card>

                    {/* Payment Method */}
                    {session.amount_paid === 0 && (
                        <Card style={{ marginBottom: 'var(--spacing-4)' }}>
                            <h3 style={{ fontSize: 'var(--font-size-lg)', fontWeight: '600', marginBottom: 'var(--spacing-3)' }}>
                                Método de Pagamento
                            </h3>
                            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--spacing-2)' }}>
                                {['card', 'mbway', 'cash'].map((method) => {
                                    const labels = { card: '💳 Cartão', mbway: '📱 MB WAY', cash: '💵 Numerário' };
                                    return (
                                        <label
                                            key={method}
                                            style={{
                                                display: 'flex',
                                                alignItems: 'center',
                                                padding: 'var(--spacing-3)',
                                                border: `2px solid ${paymentMethod === method ? 'var(--color-primary)' : 'var(--color-surface-hover)'}`,
                                                borderRadius: 'var(--border-radius-md)',
                                                cursor: 'pointer',
                                                backgroundColor: paymentMethod === method ? 'rgba(99, 102, 241, 0.1)' : 'transparent'
                                            }}
                                        >
                                            <input
                                                type="radio"
                                                name="payment-method"
                                                value={method}
                                                checked={paymentMethod === method}
                                                onChange={(e) => setPaymentMethod(e.target.value)}
                                                style={{ marginRight: 'var(--spacing-2)' }}
                                            />
                                            <span style={{ fontWeight: '500' }}>{labels[method]}</span>
                                        </label>
                                    );
                                })}
                            </div>

                            <Button
                                onClick={handlePayment}
                                disabled={processing}
                                style={{ width: '100%', marginTop: 'var(--spacing-4)', padding: 'var(--spacing-3)', fontSize: 'var(--font-size-lg)', fontWeight: 'bold' }}
                            >
                                {processing ? '🔄 A processar...' : `💳 Pagar €${calculateAmount(session.entry_time)}`}
                            </Button>

                            <p style={{ textAlign: 'center', marginTop: 'var(--spacing-2)', fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)' }}>
                                ⚠️ Sistema simulado para fins académicos
                            </p>
                        </Card>
                    )}

                    {session.amount_paid > 0 && (
                        <Card style={{ textAlign: 'center', backgroundColor: 'rgba(34, 197, 94, 0.1)' }}>
                            <p style={{ fontSize: 'var(--font-size-lg)', fontWeight: 'bold', color: 'var(--color-success)' }}>
                                ✅ Já pagou! Pode sair do parque.
                            </p>
                            {session.payment_deadline && (
                                <p style={{ marginTop: 'var(--spacing-2)', color: 'var(--color-text-secondary)' }}>
                                    Prazo para sair: {new Date(session.payment_deadline).toLocaleString('pt-PT')}
                                </p>
                            )}
                        </Card>
                    )}
                </>
            )}

            {/* Back link */}
            <div style={{ textAlign: 'center', marginTop: 'var(--spacing-4)' }}>
                <Button variant="ghost" onClick={() => navigate('/')}>
                    ← Voltar ao Início
                </Button>
            </div>
        </div>
    );
}
