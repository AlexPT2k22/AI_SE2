// Live Monitor page - real-time parking spot monitoring with WebSocket
import React from 'react';
import Card from '../components/common/Card';

export default function LiveMonitor() {
    const [spots, setSpots] = React.useState({});
    const [wsStatus, setWsStatus] = React.useState('Connecting...');
    const [wsConnected, setWsConnected] = React.useState(false);
    const wsRef = React.useRef(null);

    const getWsUrl = () => {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        return `${protocol}//${window.location.host}/ws`;
    };

    React.useEffect(() => {
        const wsUrl = getWsUrl();
        const ws = new WebSocket(wsUrl);
        wsRef.current = ws;

        ws.onopen = () => {
            setWsStatus('Connected');
            setWsConnected(true);
        };

        ws.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);

                // Check if this is a notification message
                if (data.type === 'notification' && data.data) {
                    // Notification messages are handled by NotificationBell component
                    // Just log here for debugging
                    console.log('[LiveMonitor] Notification received (handled by NotificationBell):', data.data.notification_type);
                } else {
                    // Regular spot status update
                    setSpots(data);
                }
            } catch (e) {
                console.error('Failed to parse WebSocket message:', e);
            }
        };


        ws.onerror = (error) => {
            console.error('WebSocket error:', error);
            setWsStatus('Error');
            setWsConnected(false);
        };

        ws.onclose = () => {
            setWsStatus('Disconnected');
            setWsConnected(false);
        };

        return () => {
            if (ws.readyState === WebSocket.OPEN) {
                ws.close();
            }
        };
    }, []);

    const spotNames = Object.keys(spots).sort();
    const occupied = spotNames.filter(name => spots[name]?.occupied).length;
    const free = spotNames.length - occupied;
    const videoFeedUrl = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000') + '/video_feed';

    return (
        <div className="flex flex-col gap-4">
            <Card className="p-2">
                <div className="flex items-center gap-2">
                    <span className="text-sm">WebSocket:</span>
                    <span style={{
                        backgroundColor: wsConnected ? 'var(--color-success)' : 'var(--color-danger)',
                        padding: '0.25rem 0.5rem',
                        borderRadius: 'var(--border-radius-sm)',
                        fontSize: '0.75rem',
                        fontWeight: 'bold'
                    }}>
                        {wsStatus}
                    </span>
                    <span className="text-sm" style={{ marginLeft: 'auto' }}>
                        Total: {spotNames.length} | Free: {free} | Occupied: {occupied}
                    </span>
                </div>
            </Card>

            <div style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))',
                gap: 'var(--spacing-4)'
            }}>
                <div style={{ gridColumn: 'span 1' }}>
                    <Card>
                        <h2 style={{ fontSize: 'var(--font-size-lg)', fontWeight: '600', marginBottom: 'var(--spacing-4)' }}>
                            Annotated Video
                        </h2>
                        <div style={{
                            aspectRatio: '16/9',
                            backgroundColor: 'black',
                            borderRadius: 'var(--border-radius-md)',
                            overflow: 'hidden'
                        }}>
                            <img
                                src={videoFeedUrl}
                                alt="Video stream"
                                style={{ width: '100%', height: '100%', objectFit: 'contain' }}
                            />
                        </div>
                    </Card>
                </div>

                <div style={{ gridColumn: 'span 1' }}>
                    <Card>
                        <h2 style={{ fontSize: 'var(--font-size-lg)', fontWeight: '600', marginBottom: 'var(--spacing-4)' }}>
                            Spot Status
                        </h2>
                        <div style={{ maxHeight: '500px', overflowY: 'auto' }}>
                            <div className="flex flex-col gap-2">
                                {spotNames.length === 0 ? (
                                    <p style={{ color: 'var(--color-text-secondary)', fontSize: 'var(--font-size-sm)' }}>
                                        Waiting for data...
                                    </p>
                                ) : (
                                    spotNames.map((name) => {
                                        const spot = spots[name];
                                        const isOccupied = spot.occupied;
                                        const isReserved = spot.reserved;
                                        const isViolation = spot.violation;
                                        const plate = spot.plate;
                                        const reservedPlate = spot.reserved_plate || spot.reservation?.plate;

                                        let bgColor = isOccupied ? 'var(--color-danger)' : 'var(--color-success)';
                                        let borderStyle = '1px solid transparent';
                                        let statusText = isOccupied ? 'OCCUPIED' : 'FREE';
                                        let statusIcon = isOccupied ? '🚗' : '✓';

                                        if (isViolation) {
                                            bgColor = '#c41e3a';
                                            borderStyle = '3px solid var(--color-warning)';
                                            statusIcon = '⚠️';
                                        } else if (isReserved && !isOccupied) {
                                            // Reservado mas ainda livre
                                            bgColor = 'var(--color-primary)';
                                            borderStyle = '2px solid var(--color-warning)';
                                            statusText = 'RESERVED';
                                            statusIcon = '📅';
                                        } else if (isReserved) {
                                            borderStyle = '2px solid var(--color-primary)';
                                        }

                                        return (
                                            <div key={name} style={{
                                                backgroundColor: bgColor,
                                                border: borderStyle,
                                                borderRadius: 'var(--border-radius-md)',
                                                padding: 'var(--spacing-3)',
                                                color: 'white',
                                                transition: 'all 0.2s ease',
                                                boxShadow: '0 2px 4px rgba(0,0,0,0.1)'
                                            }}>
                                                <div className="flex justify-between items-center">
                                                    <div>
                                                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.25rem' }}>
                                                            <span style={{ fontSize: '1.25rem' }}>{statusIcon}</span>
                                                            <span className="font-bold" style={{ fontSize: '1.1rem' }}>{name}</span>
                                                        </div>
                                                        <span style={{
                                                            fontSize: '0.875rem',
                                                            opacity: 0.9,
                                                            fontWeight: '500'
                                                        }}>
                                                            {statusText}
                                                        </span>
                                                    </div>
                                                    <div className="flex gap-1">
                                                        {isReserved && <span style={{ backgroundColor: 'var(--color-primary)', padding: '0.25rem 0.5rem', borderRadius: '6px', fontSize: '0.75rem', fontWeight: 'bold' }}>RESERVED</span>}
                                                        {isViolation && <span style={{ backgroundColor: 'var(--color-warning)', color: 'black', padding: '0.25rem 0.5rem', borderRadius: '6px', fontSize: '0.75rem', fontWeight: 'bold' }}>VIOLATION</span>}
                                                    </div>
                                                </div>
                                                {plate && (
                                                    <div style={{ fontSize: '0.875rem', marginTop: '0.5rem', paddingTop: '0.5rem', borderTop: '1px solid rgba(255,255,255,0.2)' }}>
                                                        <strong>License Plate:</strong> <code style={{ color: 'white', backgroundColor: 'rgba(0,0,0,0.3)', padding: '0.2rem 0.5rem', borderRadius: '4px', marginLeft: '0.25rem' }}>{plate}</code>
                                                    </div>
                                                )}
                                                {spot.reservation?.plate && (
                                                    <div style={{ fontSize: '0.875rem', marginTop: '0.25rem', opacity: 0.85 }}>
                                                        Reserved for: <strong>{spot.reservation.plate}</strong>
                                                    </div>
                                                )}
                                                {!isOccupied && reservedPlate && !spot.reservation?.plate && (
                                                    <div style={{ fontSize: '0.875rem', marginTop: '0.25rem', opacity: 0.85 }}>
                                                        🔖 Reserved for: <strong>{reservedPlate}</strong>
                                                    </div>
                                                )}
                                            </div>
                                        );
                                    })
                                )}
                            </div>
                        </div>
                    </Card>
                </div>
            </div>
        </div>
    );
}
