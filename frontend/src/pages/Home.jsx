// Home page
import React from 'react';
import { Link } from 'react-router-dom';
import Button from '../components/common/Button';
import Card from '../components/common/Card';
import Occupancy from './Occupancy.jsx';

export default function Home() {
    return (
        <div className="flex flex-col gap-4">
            {/* Hero section */}
            <Card className="text-center p-8" style={{ padding: 'clamp(1.5rem, 5vw, 2rem)' }}>
                <h1 style={{
                    fontSize: 'clamp(1.5rem, 5vw, 1.875rem)',
                    fontWeight: 'bold',
                    marginBottom: 'var(--spacing-4)',
                    background: 'linear-gradient(to right, var(--color-primary), var(--color-info))',
                    WebkitBackgroundClip: 'text',
                    WebkitTextFillColor: 'transparent'
                }}>
                    Bem-vindo ao TugaPark
                </h1>
                <p style={{
                    color: 'var(--color-text-secondary)',
                    fontSize: 'clamp(0.875rem, 3vw, 1.125rem)',
                    marginBottom: 'var(--spacing-8)'
                }}>
                    Sistema inteligente de gestão de estacionamento com deteção em tempo real
                </p>
                <div className="flex gap-4 justify-center" style={{ flexWrap: 'wrap', gap: 'var(--spacing-3)' }}>
                    <Link to="/live">
                        <Button variant="primary" size="lg" style={{ width: '100%', minWidth: '150px' }}>
                            Ver Monitor ao Vivo
                        </Button>
                    </Link>
                    <Link to="/reservar">
                        <Button variant="outline" size="lg" style={{ width: '100%', minWidth: '150px' }}>
                            Reservar Vaga
                        </Button>
                    </Link>
                </div>
            </Card>

            {/* Features */}
            <div style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))',
                gap: 'var(--spacing-4)'
            }}>
                <Card>
                    <h3 style={{ fontSize: 'var(--font-size-lg)', fontWeight: '600', marginBottom: 'var(--spacing-2)' }}>
                        🎥 Monitorização em Tempo Real
                    </h3>
                    <p style={{ color: 'var(--color-text-secondary)', fontSize: 'var(--font-size-sm)' }}>
                        Deteção automática de ocupação usando visão computacional e redes neuronais
                    </p>
                </Card>

                <Card>
                    <h3 style={{ fontSize: 'var(--font-size-lg)', fontWeight: '600', marginBottom: 'var(--spacing-2)' }}>
                        🚗 Reconhecimento de Matrículas (ALPR)
                    </h3>
                    <p style={{ color: 'var(--color-text-secondary)', fontSize: 'var(--font-size-sm)' }}>
                        Identificação automática de veículos em vagas reservadas
                    </p>
                </Card>

                <Card>
                    <h3 style={{ fontSize: 'var(--font-size-lg)', fontWeight: '600', marginBottom: 'var(--spacing-2)' }}>
                        📱 Sistema de Reservas
                    </h3>
                    <p style={{ color: 'var(--color-text-secondary)', fontSize: 'var(--font-size-sm)' }}>
                        Reserve vagas online com autenticação segura
                    </p>
                </Card>
            </div>

            {/* Current occupancy */}
            <Occupancy />
        </div>
    );
}
