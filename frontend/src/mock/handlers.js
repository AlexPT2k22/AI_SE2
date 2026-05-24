import {
  MOCK_USER, MOCK_VEHICLES, MOCK_RESERVATIONS, MOCK_SESSIONS,
  MOCK_PAYMENT_METHODS, MOCK_ADMIN_STATS, MOCK_NOTIFICATIONS,
  getMockSpots, getNextMockSpots
} from './data';

let mockUser = { ...MOCK_USER };
let mockVehicles = [...MOCK_VEHICLES];
let mockReservations = [...MOCK_RESERVATIONS];
let mockSessions = [...MOCK_SESSIONS];
let mockPaymentMethods = [...MOCK_PAYMENT_METHODS];
let mockNotifications = [...MOCK_NOTIFICATIONS];

export function resetMockState() {
  mockUser = { ...MOCK_USER };
  mockVehicles = [...MOCK_VEHICLES];
  mockReservations = [...MOCK_RESERVATIONS];
  mockSessions = [...MOCK_SESSIONS];
  mockPaymentMethods = [...MOCK_PAYMENT_METHODS];
  mockNotifications = [...MOCK_NOTIFICATIONS];
}

export const mockHandlers = {
  'GET /parking': () => getMockSpots(),

  'GET /api/auth/me': () => mockUser,

  'POST /api/auth/login': () => ({
    token: 'mock-jwt-token-demo',
    user: mockUser
  }),

  'POST /api/auth/register': () => ({
    token: 'mock-jwt-token-demo',
    user: mockUser
  }),

  'GET /api/reservations': () => ({
    reservations: mockReservations
  }),

  'POST /api/reservations': (body) => {
    const newReservation = {
      id: mockReservations.length + 1,
      spot: body.spot,
      plate: body.plate,
      reservation_date: body.reservation_date,
      was_used: false,
      fine_applied: false
    };
    mockReservations.push(newReservation);
    return { reservation: newReservation, message: 'Reservation created' };
  },

  'DELETE /api/reservations/:spot': (params) => {
    mockReservations = mockReservations.filter(r => r.spot !== params.spot);
    return { message: `Reservation for spot ${params.spot} cancelled` };
  },

  'GET /api/user/vehicles': () => ({
    vehicles: mockVehicles
  }),

  'POST /api/user/vehicles': (body) => {
    const newVehicle = {
      id: mockVehicles.length + 1,
      plate: body.plate,
      brand: body.brand || '',
      model: body.model || '',
      color: body.color || '',
      is_primary: mockVehicles.length === 0
    };
    mockVehicles.push(newVehicle);
    return { vehicle: newVehicle, message: 'Vehicle added' };
  },

  'DELETE /api/user/vehicles/:id': (params) => {
    mockVehicles = mockVehicles.filter(v => v.id !== parseInt(params.id));
    return { message: 'Vehicle removed' };
  },

  'GET /api/user/payment-methods': () => ({
    payment_methods: mockPaymentMethods
  }),

  'POST /api/user/payment-methods': (body) => {
    const lastFour = body.card_number.slice(-4);
    const newCard = {
      id: mockPaymentMethods.length + 1,
      card_type: body.card_type,
      card_last_four: lastFour,
      card_holder_name: body.card_holder_name,
      expiry_month: body.expiry_month,
      expiry_year: body.expiry_year,
      is_default: true,
      auto_pay: body.auto_pay || false
    };
    mockPaymentMethods = [newCard];
    return { payment_method: newCard, message: 'Card added' };
  },

  'DELETE /api/user/payment-methods/:id': (params) => {
    mockPaymentMethods = mockPaymentMethods.filter(pm => pm.id !== parseInt(params.id));
    return { message: 'Card removed' };
  },

  'GET /api/user/sessions': () => ({
    sessions: mockSessions
  }),

  'GET /api/sessions': () => mockSessions,

  'GET /api/sessions/:id': (params) => {
    const session = mockSessions.find(s => s.id === parseInt(params.id));
    if (!session) throw new Error('Session not found');
    return session;
  },

  'POST /api/sessions/:id/simulate-payment': (params, body) => {
    const idx = mockSessions.findIndex(s => s.id === parseInt(params.id));
    if (idx === -1) throw new Error('Session not found');
    mockSessions[idx] = {
      ...mockSessions[idx],
      status: 'paid',
      amount_paid: body.amount
    };
    return { message: 'Payment processed', session: mockSessions[idx] };
  },

  'GET /api/user/notifications': () => ({
    notifications: mockNotifications.filter(n => !n.is_read)
  }),

  'POST /api/user/notifications/:id/read': (params) => {
    const idx = mockNotifications.findIndex(n => n.id === parseInt(params.id));
    if (idx !== -1) mockNotifications[idx].is_read = true;
    return { message: 'Notification marked as read' };
  },

  'GET /api/admin/stats': () => MOCK_ADMIN_STATS,

  'GET /api/admin/users': () => ({
    users: [
      { id: 1, email: 'demo@tugapark.com', full_name: 'Demo User', role: 'admin' },
      { id: 2, email: 'user@test.com', full_name: 'Test Client', role: 'client' }
    ],
    total: 2
  })
};

export function getMockWebSocketMessage() {
  return JSON.stringify(getNextMockSpots());
}
