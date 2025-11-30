import React from 'react';
import Card from './Card';

export default function StatsCard({ title, value, subtitle, icon, color = 'var(--color-primary)' }) {
    return (
        <Card style={{ padding: 'var(--spacing-4)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <div style={{ flex: 1 }}>
                    <p style={{ 
                        color: 'var(--color-text-secondary)', 
                        fontSize: 'var(--font-size-sm)',
                        marginBottom: 'var(--spacing-2)',
                        fontWeight: '500'
                    }}>
                        {title}
                    </p>
                    <h3 style={{ 
                        fontSize: 'var(--font-size-3xl)', 
                        fontWeight: 'bold',
                        marginBottom: 'var(--spacing-1)',
                        color: 'var(--color-text-primary)'
                    }}>
                        {value}
                    </h3>
                    {subtitle && (
                        <p style={{ 
                            color: 'var(--color-text-muted)', 
                            fontSize: 'var(--font-size-xs)'
                        }}>
                            {subtitle}
                        </p>
                    )}
                </div>
                {icon && (
                    <div style={{
                        fontSize: '2rem',
                        opacity: 0.2,
                        color: color
                    }}>
                        {icon}
                    </div>
                )}
            </div>
        </Card>
    );
}
