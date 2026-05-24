const now = new Date();
const today = now.toISOString().split('T')[0];
const tomorrow = new Date(now);
tomorrow.setDate(tomorrow.getDate() + 1);
const tomorrowStr = tomorrow.toISOString().split('T')[0];

export const MOCK_USER = {
  id: 1,
  email: 'demo@tugapark.com',
  full_name: 'Demo User',
  role: 'admin',
  created_at: '2025-01-15T10:00:00Z'
};

export const MOCK_SPOTS = {
  'A1': { occupied: false, reserved: false },
  'A2': { occupied: true, reserved: false, plate: 'AB-12-CD' },
  'A3': { occupied: false, reserved: true, reserved_plate: 'XY-99-ZZ' },
  'B1': { occupied: true, reserved: false, plate: 'KA-87-BC', violation: true, reservation: { plate: 'XX-00-AA' } },
  'B2': { occupied: false, reserved: false },
  'B3': { occupied: true, reserved: false, plate: 'FT-45-HJ' },
  'C1': { occupied: false, reserved: true },
  'C2': { occupied: false, reserved: false },
  'C3': { occupied: true, reserved: false, plate: 'MN-33-KL' }
};

export const MOCK_VEHICLES = [
  { id: 1, plate: 'AB-12-CD', brand: 'BMW', model: 'Series 3', color: 'Black', is_primary: true },
  { id: 2, plate: 'XY-99-ZZ', brand: 'Tesla', model: 'Model 3', color: 'White', is_primary: false }
];

let spotIndex = 0;
const spotNames = Object.keys(MOCK_SPOTS);

export function getNextMockSpots() {
  spotIndex = (spotIndex + 1) % spotNames.length;
  const randomSpot = spotNames[spotIndex];
  const updated = { ...MOCK_SPOTS };
  
  if (Math.random() > 0.7) {
    updated[randomSpot] = {
      ...updated[randomSpot],
      occupied: !updated[randomSpot].occupied,
      plate: updated[randomSpot].occupied ? undefined : 'XX-99-XX'
    };
  }
  
  return updated;
}

export function getMockSpots() {
  return { ...MOCK_SPOTS };
}

export const MOCK_RESERVATIONS = [
  { id: 1, spot: 'A3', plate: 'XY-99-ZZ', reservation_date: today, was_used: false, fine_applied: false },
  { id: 2, spot: 'C1', plate: 'AB-12-CD', reservation_date: tomorrowStr, was_used: false, fine_applied: false }
];

export const MOCK_SESSIONS = [
  { id: 101, plate: 'AB-12-CD', spot: 'A2', entry_time: new Date(now - 7200000).toISOString(), exit_time: null, amount_due: 3.00, amount_paid: 0, status: 'open' },
  { id: 102, plate: 'KA-87-BC', spot: 'B1', entry_time: new Date(now - 3600000).toISOString(), exit_time: null, amount_due: 1.50, amount_paid: 0, status: 'open' },
  { id: 103, plate: 'FT-45-HJ', spot: 'B3', entry_time: new Date(now - 10800000).toISOString(), exit_time: new Date(now - 5400000).toISOString(), amount_due: 4.50, amount_paid: 4.50, status: 'paid' },
  { id: 104, plate: 'MN-33-KL', spot: 'C3', entry_time: new Date(now - 18000000).toISOString(), exit_time: null, amount_due: 7.50, amount_paid: 0, status: 'open' },
  { id: 105, plate: 'AB-12-CD', spot: 'A2', entry_time: new Date(now - 86400000).toISOString(), exit_time: new Date(now - 72000000).toISOString(), amount_due: 6.00, amount_paid: 6.00, status: 'paid' }
];

export const MOCK_PAYMENT_METHODS = [
  { id: 1, card_type: 'visa', card_last_four: '4242', card_holder_name: 'Demo User', expiry_month: 12, expiry_year: 2027, is_default: true, auto_pay: true }
];

export const MOCK_ADMIN_STATS = {
  total_spots: 9,
  occupied_spots: 5,
  free_spots: 4,
  total_sessions: 105,
  active_sessions: 3,
  total_revenue: 1245.50,
  today_sessions: 5,
  avg_duration_minutes: 87,
  recent_sessions: MOCK_SESSIONS.slice(0, 3)
};

export const MOCK_NOTIFICATIONS = [
  { id: 1, title: 'Reservation Violation', body: 'Vehicle KA-87-BC parked in reserved spot B1 (reserved for XX-00-AA)', notification_type: 'violation_alert', created_at: now.toISOString(), is_read: false },
  { id: 2, title: 'Payment Received', body: 'Payment of €4.50 for session #103 completed', notification_type: 'payment', created_at: new Date(now - 3600000).toISOString(), is_read: false }
];
