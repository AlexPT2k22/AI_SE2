// Payment Page - Simulated Payment System (Academic Project)
import React from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { api } from '../api.js';
import Card from '../components/common/Card';
import Button from '../components/common/Button';

export default function Payment() {
    const { sessionId } = useParams();
    const navigate = useNavigate();
    const [session, setSession] = React.useState(null);
    const [loading, setLoading] = React.useState(true);
    const [error, setError] = React.useState('');
    const [paymentMethod, setPaymentMethod] = React.useState('card');
    const [processing, setProcessing] = React.useState(false);
    const [success, setSuccess] = React.useState(false);

    React.useEffect(() => {
        loadSession();
    }, [sessionId]);

    const loadSession = async () => {
        try {
            const data = await api(`/api/sessions/${sessionId}`);
            setSession(data);
            setError('');
        } catch (e) {
            setError(e.message);
        } finally {
            setLoading(false);
        }
    };

    const handlePayment = async () => {
        if (!session) return;

        setProcessing(true);
        setError('');

        // Simulate processing delay
        await new Promise(resolve => setTimeout(resolve, 2000));

        try {
            await api(`/api/sessions/${sessionId}/simulate-payment`, {
                method: 'POST',
                body: JSON.stringify({
                    session_id: session.id,
                    amount: session.amount_due,
                    method: paymentMethod
                })
            });

            setSuccess(true);
            setTimeout(() => {
                navigate('/sessions');
            }, 3000);
        } catch (e) {
            setError(e.message);
        } finally {
            setProcessing(false);
        }
    };

    if (loading) {
        return (
            <Card style={{ padding: 'var(--spacing-6)', textAlign: 'center' }}>
                <p style={{ color: 'var(--color-text-secondary)' }}>A carregar sessão...</p>
            </Card>
        );
    }

    if (error && !session) {
        return (
            <Card style={{ padding: 'var(--spacing-6)', textAlign: 'center' }}>
                <p style={{ color: 'var(--color-danger)' }}>Erro: {error}</p>
                <Button onClick={() => navigate('/sessions')} style={{ marginTop: 'var(--spacing-4)' }}>
                    Voltar
                </Button>
            </Card>
        );
    }

    if (success) {
        return (
            <Card style={{ padding: 'var(--spacing-6)', textAlign: 'center' }}>
                <div style={{ fontSize: '4rem', marginBottom: 'var(--spacing-4)' }}>✅</div>
                <h2 style={{ fontSize: 'var(--font-size-2xl)', fontWeight: 'bold', marginBottom: 'var(--spacing-2)', color: 'var(--color-success)' }}>
                    Pagamento Concluído!
                </h2>
                <p style={{ color: 'var(--color-text-secondary)', marginBottom: 'var(--spacing-4)' }}>
                    O pagamento de €{session.amount_due.toFixed(2)} foi processado com sucesso.
                </p>
                <p style={{ fontSize: 'var(--font-size-sm)', color: 'var(--color-text-muted)' }}>
                    A redirecionar...
                </p>
            </Card>
        );
    }

    const amountDue = session.amount_due - session.amount_paid;

    return (
        <div className="flex flex-col gap-4" style={{ maxWidth: '600px', margin: '0 auto' }}>
            <Card style={{ padding: 'var(--spacing-4)' }}>
                <h1 style={{ fontSize: 'var(--font-size-2xl)', fontWeight: 'bold', marginBottom: 'var(--spacing-2)' }}>
                    Pagamento Simulado
                </h1>
                <p style={{ color: 'var(--color-text-secondary)', fontSize: 'var(--font-size-sm)' }}>
                    Sistema de pagamento simulado para fins académicos
                </p>
            </Card>

            {/* Session Details */}
            <Card>
                <h3 style={{ fontSize: 'var(--font-size-lg)', fontWeight: '600', marginBottom: 'var(--spacing-4)' }}>
                    Detalhes da Sessão
                </h3>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--spacing-2)' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', padding: 'var(--spacing-2)', borderBottom: '1px solid var(--color-surface-hover)' }}>
                        <span style={{ color: 'var(--color-text-secondary)' }}>ID da Sessão:</span>
                        <span style={{ fontWeight: 'bold' }}>{session.id}</span>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', padding: 'var(--spacing-2)', borderBottom: '1px solid var(--color-surface-hover)' }}>
                        <span style={{ color: 'var(--color-text-secondary)' }}>Matrícula:</span>
                        <span style={{ fontWeight: 'bold' }}>{session.plate}</span>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', padding: 'var(--spacing-2)', borderBottom: '1px solid var(--color-surface-hover)' }}>
                        <span style={{ color: 'var(--color-text-secondary)' }}>Entrada:</span>
                        <span>{session.entry_time ? new Date(session.entry_time).toLocaleString('pt-PT') : '-'}</span>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', padding: 'var(--spacing-2)', borderBottom: '1px solid var(--color-surface-hover)' }}>
                        <span style={{ color: 'var(--color-text-secondary)' }}>Saída:</span>
                        <span>{session.exit_time ? new Date(session.exit_time).toLocaleString('pt-PT') : '-'}</span>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', padding: 'var(--spacing-2)', borderBottom: '1px solid var(--color-surface-hover)' }}>
                        <span style={{ color: 'var(--color-text-secondary)' }}>Valor Total:</span>
                        <span style={{ fontWeight: 'bold' }}>€{session.amount_due.toFixed(2)}</span>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', padding: 'var(--spacing-2)', borderBottom: '1px solid var(--color-surface-hover)' }}>
                        <span style={{ color: 'var(--color-text-secondary)' }}>Já Pago:</span>
                        <span>€{session.amount_paid.toFixed(2)}</span>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', padding: 'var(--spacing-3)', backgroundColor: 'var(--color-surface)', borderRadius: 'var(--border-radius-md)', marginTop: 'var(--spacing-2)' }}>
                        <span style={{ fontSize: 'var(--font-size-lg)', fontWeight: 'bold' }}>A Pagar:</span>
                        <span style={{ fontSize: 'var(--font-size-2xl)', fontWeight: 'bold', color: 'var(--color-primary)' }}>
                            €{amountDue.toFixed(2)}
                        </span>
                    </div>
                </div>
            </Card>

            {/* Payment Method */}
            <Card>
                <h3 style={{ fontSize: 'var(--font-size-lg)', fontWeight: '600', marginBottom: 'var(--spacing-4)' }}>
                    Método de Pagamento
                </h3>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--spacing-2)' }}>
                    {['card', 'cash', 'mbway'].map((method) => {
                        const labels = {
                            card: '💳 Cartão',
                            cash: '💵 Dinheiro',
                            mbway: '📱 MB WAY'
                        };

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
                                    transition: 'all 0.2s ease',
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
                                <span style={{ fontSize: 'var(--font-size-base)', fontWeight: '500' }}>
                                    {labels[method]}
                                </span>
                            </label>
                        );
                    })}
                </div>
            </Card>

            {/* Pay Button */}
            <Card style={{ padding: 'var(--spacing-4)', textAlign: 'center' }}>
                {error && (
                    <p style={{ color: 'var(--color-danger)', marginBottom: 'var(--spacing-3)' }}>
                        {error}
                    </p>
                )}

                <Button
                    onClick={handlePayment}
                    disabled={processing || amountDue <= 0}
                    style={{ 
                        width: '100%', 
                        padding: 'var(--spacing-3)',
                        fontSize: 'var(--font-size-lg)',
                        fontWeight: 'bold'
                    }}
                >
                    {processing ? '🔄 A processar...' : `💳 Pagar €${amountDue.toFixed(2)}`}
                </Button>

                <p style={{ 
                    marginTop: 'var(--spacing-3)', 
                    fontSize: 'var(--font-size-xs)', 
                    color: 'var(--color-text-muted)' 
                }}>
                    ⚠️ Sistema de pagamento simulado para fins académicos
                </p>

                <Button
                    variant="ghost"
                    onClick={() => navigate('/sessions')}
                    style={{ marginTop: 'var(--spacing-2)' }}
                    disabled={processing}
                >
                    ← Voltar
                </Button>
            </Card>
        </div>
    );
}
