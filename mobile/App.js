// TugaPark Mobile App - Simplified Main Entry
import React, { useState, useEffect } from 'react';
import { 
  View, 
  Text, 
  TextInput, 
  TouchableOpacity, 
  StyleSheet, 
  SafeAreaView,
  Alert,
  ActivityIndicator,
  ScrollView,
  KeyboardAvoidingView,
  Platform,
  RefreshControl,
  Modal,
} from 'react-native';
import { StatusBar } from 'expo-status-bar';
import AsyncStorage from '@react-native-async-storage/async-storage';
import axios from 'axios';
import Svg, { Path } from 'react-native-svg';

// SVG Icon Components
const DangerIcon = ({ size = 24, color = '#ef4444' }) => (
  <Svg width={size} height={size} viewBox="0 0 30 30">
    <Path
      fill={color}
      d="M 15 3 C 14.168432 3 13.456063 3.5067238 13.154297 4.2285156 L 2.3007812 22.947266 L 2.3007812 22.949219 A 2 2 0 0 0 2 24 A 2 2 0 0 0 4 26 A 2 2 0 0 0 4.140625 25.994141 L 4.1445312 26 L 15 26 L 25.855469 26 L 25.859375 25.992188 A 2 2 0 0 0 26 26 A 2 2 0 0 0 28 24 A 2 2 0 0 0 27.699219 22.947266 L 27.683594 22.919922 A 2 2 0 0 0 27.681641 22.917969 L 16.845703 4.2285156 C 16.543937 3.5067238 15.831568 3 15 3 z M 13.787109 11.359375 L 16.212891 11.359375 L 16.011719 17.832031 L 13.988281 17.832031 L 13.787109 11.359375 z M 15.003906 19.810547 C 15.825906 19.810547 16.318359 20.252813 16.318359 21.007812 C 16.318359 21.748812 15.825906 22.189453 15.003906 22.189453 C 14.175906 22.189453 13.679688 21.748813 13.679688 21.007812 C 13.679688 20.252813 14.174906 19.810547 15.003906 19.810547 z"
    />
  </Svg>
);

const ClockIcon = ({ size = 24, color = '#f59e0b' }) => (
  <Svg width={size} height={size} viewBox="0 0 64 64">
    <Path
      fill={color}
      d="M32,10c12.15,0,22,9.85,22,22s-9.85,22-22,22s-22-9.85-22-22S19.85,10,32,10z M34,32c0-0.366,0-13.634,0-14c0-1.105-0.896-2-2-2s-2,0.895-2,2c0,0.282,0,8.196,0,12c-2.66,0-9.698,0-10,0c-1.105,0-2,0.896-2,2s0.895,2,2,2c0.366,0,11.826,0,12,0C33.104,34,34,33.105,34,32z"
    />
  </Svg>
);

const PaymentIcon = ({ size = 24, color = '#3b82f6' }) => (
  <Svg width={size} height={size} viewBox="0 0 30 30">
    <Path
      fill={color}
      d="M 19 2 C 15.134 2 12 5.134 12 9 C 12 12.866 15.134 16 19 16 C 22.866 16 26 12.866 26 9 C 26 5.134 22.866 2 19 2 z M 18.001953 4 L 20.001953 4 L 20.001953 5.0039062 C 21.269953 5.3019063 22.097047 6.1583594 22.123047 7.3183594 L 20.287109 7.3183594 C 20.244109 6.7663594 19.719531 6.3808594 19.019531 6.3808594 C 18.319531 6.3808594 17.859375 6.7124219 17.859375 7.2324219 C 17.859375 7.6604219 18.206297 7.9083125 19.029297 8.0703125 L 20.037109 8.265625 C 21.581109 8.563625 22.275391 9.2639063 22.275391 10.503906 C 22.274391 11.839906 21.428 12.730672 20 13.013672 L 20 14 L 18 14 L 18 13.021484 C 16.606 12.756484 15.752562 11.917641 15.726562 10.681641 L 17.621094 10.681641 C 17.670094 11.250641 18.2395 11.613281 19.0625 11.613281 C 19.8045 11.613281 20.314453 11.255234 20.314453 10.740234 C 20.314453 10.307234 19.971125 10.075484 19.078125 9.8964844 L 18.050781 9.6894531 C 16.620781 9.4184531 15.882813 8.6391563 15.882812 7.4101562 C 15.882812 6.1731562 16.695953 5.2910937 18.001953 4.9960938 L 18.001953 4 z M 8 15 A 3 3 0 0 0 6.8828125 15.216797 L 2 17 L 2 25 L 6.2207031 23.166016 C 6.7187031 22.950016 7.2821563 22.942438 7.7851562 23.148438 L 16.849609 26.851562 C 16.849609 26.851562 16.853494 26.851563 16.853516 26.851562 A 1.5 1.5 0 0 0 17.5 27 A 1.5 1.5 0 0 0 18.238281 26.802734 C 18.238413 26.802691 18.244057 26.802776 18.244141 26.802734 L 27.230469 21.810547 L 27.228516 21.808594 A 1.5 1.5 0 0 0 28 20.5 A 1.5 1.5 0 0 0 26.5 19 A 1.5 1.5 0 0 0 25.863281 19.144531 L 25.863281 19.142578 L 19 22 L 17.5 22 A 1.5 1.5 0 0 0 19 20.5 A 1.5 1.5 0 0 0 17.964844 19.074219 L 17.964844 19.072266 L 9.2714844 15.28125 L 9.2597656 15.28125 A 3 3 0 0 0 8 15 z"
    />
  </Svg>
);

// API Configuration
//const API_BASE_URL = 'http://10.0.2.2:8000'; // Android emulator
const API_BASE_URL = 'http://192.168.68.125:8000'; // Replace with your IP for physical device

// Colors - Light Theme (matching frontend)
const colors = {
  primary: '#97d700',          // Lime Green
  primaryDark: '#31a100',
  secondary: '#1e1e1e',        // Dark
  background: '#f5f5f5',       // Light gray
  surface: '#ffffff',          // White
  surfaceHover: '#f0f0f0',
  text: '#1a1a1a',             // Dark text
  textSecondary: '#666666',
  textMuted: '#999999',
  textInverse: '#ffffff',
  border: '#e5e5e5',
  success: '#22c55e',
  danger: '#ef4444',
  warning: '#f59e0b',
  info: '#3b82f6',
  spotAvailable: '#c8e620',
  spotOccupied: '#ef4444',
  spotReserved: '#f59e0b',
};

// API Client
const api = axios.create({
  baseURL: API_BASE_URL,
  headers: { 'Content-Type': 'application/json' },
  timeout: 10000,
});

api.interceptors.request.use(async (config) => {
  const token = await AsyncStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Login Screen Component
const LoginScreen = ({ onLogin }) => {
  const [name, setName] = useState('');
  const [plate, setPlate] = useState('');
  const [isRegister, setIsRegister] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async () => {
    if (!name.trim() || !plate.trim()) {
      setError('Preencha todos os campos');
      return;
    }

    setLoading(true);
    setError('');

    try {
      const endpoint = isRegister ? '/api/mobile/register' : '/api/mobile/login';
      const response = await api.post(endpoint, {
        name: name.trim(),
        plate: plate.trim().toUpperCase(),
      });

      await AsyncStorage.setItem('token', response.data.token);
      await AsyncStorage.setItem('user', JSON.stringify(response.data.user));
      onLogin(response.data.user);
    } catch (e) {
      setError(e.response?.data?.detail || e.message || 'Erro ao conectar');
    } finally {
      setLoading(false);
    }
  };

  return (
    <SafeAreaView style={styles.container}>
      <StatusBar style="dark" />
      <KeyboardAvoidingView 
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
        style={{ flex: 1 }}
      >
        <ScrollView 
          contentContainerStyle={styles.scrollContent}
          keyboardShouldPersistTaps="handled"
        >
          <View style={styles.header}>
            <Text style={styles.title}>TugaPark</Text>
            <Text style={styles.subtitle}>Estacionamento inteligente</Text>
          </View>

          <View style={styles.card}>
            <Text style={styles.cardTitle}>{isRegister ? 'Criar Conta' : 'Entrar'}</Text>
            
            <Text style={styles.label}>Nome completo</Text>
            <TextInput
            style={styles.input}
            placeholder="João Silva"
            placeholderTextColor={colors.textMuted}
            value={name}
            onChangeText={setName}
            autoCapitalize="words"
          />

          <Text style={styles.label}>Matrícula</Text>
          <TextInput
            style={styles.input}
            placeholder="AA-00-BB"
            placeholderTextColor={colors.textMuted}
            value={plate}
            onChangeText={(t) => setPlate(t.toUpperCase())}
            autoCapitalize="characters"
          />

          {error ? <Text style={styles.error}>{error}</Text> : null}

          <TouchableOpacity
            style={[styles.button, loading && styles.buttonDisabled]}
            onPress={handleSubmit}
            disabled={loading}
          >
            {loading ? (
              <ActivityIndicator color={colors.text} />
            ) : (
              <Text style={styles.buttonText}>
                {isRegister ? 'Registar' : 'Entrar'}
              </Text>
            )}
          </TouchableOpacity>

          <TouchableOpacity
            style={styles.switchButton}
            onPress={() => { setIsRegister(!isRegister); setError(''); }}
          >
            <Text style={styles.switchText}>
              {isRegister ? 'Já tem conta? Entrar' : 'Não tem conta? Registar'}
            </Text>
          </TouchableOpacity>
          </View>
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
};

// Home Screen Component
const HomeScreen = ({ user, onLogout }) => {
  const [spots, setSpots] = useState({});
  const [sessions, setSessions] = useState([]);
  const [reservations, setReservations] = useState([]);
  const [parkingRate, setParkingRate] = useState(1.50); // Default, will be fetched
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [activeTab, setActiveTab] = useState('home');
  
  // Reservation modal state
  const [showReserveModal, setShowReserveModal] = useState(false);
  const [selectedSpot, setSelectedSpot] = useState(null);
  const [selectedDuration, setSelectedDuration] = useState(1);
  
  // Timer state for active sessions
  const [currentTime, setCurrentTime] = useState(Date.now());
  
  // Update timer every second
  useEffect(() => {
    const timer = setInterval(() => {
      setCurrentTime(Date.now());
    }, 1000);
    return () => clearInterval(timer);
  }, []);
  
  // Calculate elapsed time for a session
  const getElapsedTime = (entryTime) => {
    const entry = new Date(entryTime).getTime();
    const elapsed = Math.floor((currentTime - entry) / 1000);
    const hours = Math.floor(elapsed / 3600);
    const minutes = Math.floor((elapsed % 3600) / 60);
    const seconds = elapsed % 60;
    if (hours > 0) {
      return `${hours}h ${minutes}m ${seconds}s`;
    }
    return `${minutes}m ${seconds}s`;
  };
  
  // Calculate current cost using rate from backend
  const getCurrentCost = (entryTime) => {
    const entry = new Date(entryTime).getTime();
    const elapsed = (currentTime - entry) / 1000 / 60 / 60; // hours
    return (elapsed * parkingRate).toFixed(2);
  };
  
  // Get alerts for expiring reservations and payment deadlines
  const getAlerts = () => {
    const alerts = [];
    
    // Check reservations expiring soon (< 1 hour)
    reservations.forEach(res => {
      const expiresIn = (res.expires_at * 1000 - currentTime) / 1000 / 60; // minutes
      if (expiresIn > 0 && expiresIn < 60) {
        alerts.push({
          type: 'warning',
          icon: 'clock',
          title: 'Reserva a expirar',
          message: `Vaga ${res.spot} expira em ${Math.floor(expiresIn)} min`,
        });
      }
    });
    
    // Check payment deadlines
    sessions.forEach(session => {
      if (session.payment_deadline) {
        const deadline = new Date(session.payment_deadline).getTime();
        const timeLeft = (deadline - currentTime) / 1000 / 60; // minutes
        if (timeLeft > 0 && timeLeft < 10) {
          alerts.push({
            type: 'danger',
            icon: 'danger',
            title: 'Prazo de saída',
            message: `Tem ${Math.floor(timeLeft)} min para sair!`,
          });
        }
      }
    });
    
    // Check pending payments
    const pendingPayments = sessions.filter(s => s.status === 'open' && s.amount_due > 0);
    if (pendingPayments.length > 0) {
      alerts.push({
        type: 'info',
        icon: 'payment',
        title: 'Pagamento pendente',
        message: `${pendingPayments.length} sessão(ões) a aguardar pagamento`,
      });
    }
    
    return alerts;
  };
  
  const alerts = getAlerts();
  
  const durationOptions = [1, 2, 3, 4, 6, 12, 24];

  const loadData = async () => {
    try {
      const [spotsRes, sessionsRes, reservationsRes, configRes] = await Promise.all([
        api.get('/parking'),
        api.get('/api/mobile/sessions'),
        api.get('/api/mobile/reservations'),
        api.get('/api/config'),
      ]);
      setSpots(spotsRes.data);
      setSessions(sessionsRes.data.sessions || []);
      setReservations(reservationsRes.data.reservations || []);
      if (configRes.data?.parking_rate_per_hour) {
        setParkingRate(configRes.data.parking_rate_per_hour);
      }
    } catch (e) {
      console.log('Load error:', e.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 15000);
    return () => clearInterval(interval);
  }, []);

  const openReserveModal = (spotName) => {
    setSelectedSpot(spotName);
    setSelectedDuration(1);
    setShowReserveModal(true);
  };

  const handleReserve = async () => {
    if (!selectedSpot) return;
    try {
      await api.post('/api/mobile/reservations', { 
        spot: selectedSpot, 
        duration_hours: selectedDuration 
      });
      Alert.alert('Sucesso!', `Vaga ${selectedSpot} reservada por ${selectedDuration}h!`);
      setShowReserveModal(false);
      setSelectedSpot(null);
      loadData();
    } catch (e) {
      Alert.alert('Erro', e.response?.data?.detail || 'Falha ao reservar');
    }
  };

  const handleCancelReservation = async (spotName) => {
    Alert.alert(
      'Cancelar Reserva',
      `Deseja cancelar a reserva da vaga ${spotName}?`,
      [
        { text: 'Não', style: 'cancel' },
        {
          text: 'Sim, Cancelar',
          style: 'destructive',
          onPress: async () => {
            try {
              await api.delete(`/api/mobile/reservations/${spotName}`);
              Alert.alert('Sucesso!', 'Reserva cancelada.');
              loadData();
            } catch (e) {
              Alert.alert('Erro', e.response?.data?.detail || 'Falha ao cancelar');
            }
          },
        },
      ]
    );
  };

  const handlePay = async (sessionId, amount) => {
    try {
      await api.post('/api/mobile/payments', {
        session_id: sessionId,
        amount: amount,
        method: 'card',
      });
      Alert.alert('Sucesso!', 'Pagamento efetuado! Tem 15 min para sair.');
      loadData();
    } catch (e) {
      Alert.alert('Erro', e.response?.data?.detail || 'Falha ao pagar');
    }
  };

  const spotsList = Object.entries(spots).map(([name, data]) => ({ name, ...data }));
  const freeSpots = spotsList.filter(s => !s.occupied && !s.reserved);
  const occupiedSpots = spotsList.filter(s => s.occupied);

  if (loading) {
    return (
      <View style={[styles.container, styles.centered]}>
        <ActivityIndicator size="large" color={colors.primary} />
        <Text style={styles.loadingText}>A carregar...</Text>
      </View>
    );
  }

  return (
    <SafeAreaView style={styles.container}>
      <StatusBar style="dark" />
      
      {/* Header */}
      <View style={styles.homeHeader}>
        <View>
          <Text style={styles.greeting}>Olá, {user?.name?.split(' ')[0]}!</Text>
          <Text style={styles.plate}>{user?.plate}</Text>
        </View>
        <TouchableOpacity onPress={onLogout}>
          <Text style={styles.logoutText}>Sair</Text>
        </TouchableOpacity>
      </View>

      {/* Tabs */}
      <View style={styles.tabs}>
        {['home', 'spots', 'settings'].map((tab) => (
          <TouchableOpacity
            key={tab}
            style={[styles.tab, activeTab === tab && styles.tabActive]}
            onPress={() => setActiveTab(tab)}
          >
            <Text style={[styles.tabText, activeTab === tab && styles.tabTextActive]}>
              {tab === 'home' ? 'Início' : tab === 'spots' ? 'Vagas' : 'Definições'}
            </Text>
          </TouchableOpacity>
        ))}
      </View>

      <ScrollView 
        style={styles.content}
        refreshControl={
          <RefreshControl
            refreshing={refreshing}
            onRefresh={async () => {
              setRefreshing(true);
              await loadData();
              setRefreshing(false);
            }}
            tintColor={colors.primary}
            colors={[colors.primary]}
          />
        }
      >
        {activeTab === 'home' && (
          <>
            {/* Alerts */}
            {alerts.length > 0 && (
              <View style={styles.alertsSection}>
                {alerts.map((alert, i) => (
                  <View key={i} style={[
                    styles.alertCard,
                    alert.type === 'warning' && styles.alertWarning,
                    alert.type === 'danger' && styles.alertDanger,
                    alert.type === 'info' && styles.alertInfo,
                  ]}>
                    <View style={styles.alertIconContainer}>
                      {alert.icon === 'clock' && <ClockIcon size={24} color="#fff" />}
                      {alert.icon === 'danger' && <DangerIcon size={24} color="#fff" />}
                      {alert.icon === 'payment' && <PaymentIcon size={24} color="#fff" />}
                    </View>
                    <View style={styles.alertContent}>
                      <Text style={styles.alertTitle}>{alert.title}</Text>
                      <Text style={styles.alertMessage}>{alert.message}</Text>
                    </View>
                  </View>
                ))}
              </View>
            )}
            
            {/* Active Session Timer */}
            {sessions.filter(s => s.status === 'open').length > 0 && (
              <View style={styles.activeSessionSection}>
                <Text style={styles.sectionTitle}>Sessão Ativa</Text>
                {sessions.filter(s => s.status === 'open').slice(0, 1).map((session, i) => (
                  <View key={i} style={styles.timerCard}>
                    <View style={styles.timerHeader}>
                      <Text style={styles.timerSpot}>
                        {session.spot ? `Vaga ${session.spot}` : 'Estacionado'}
                      </Text>
                      <View style={styles.timerBadge}>
                        <Text style={styles.timerBadgeText}>EM CURSO</Text>
                      </View>
                    </View>
                    <View style={styles.timerDisplay}>
                      <Text style={styles.timerTime}>
                        {getElapsedTime(session.entry_time)}
                      </Text>
                      <Text style={styles.timerCost}>
                        €{getCurrentCost(session.entry_time)}
                      </Text>
                    </View>
                    <Text style={styles.timerEntry}>
                      Entrada: {new Date(session.entry_time).toLocaleTimeString('pt-PT')}
                    </Text>
                  </View>
                ))}
              </View>
            )}
            
            {/* Pending Sessions */}
            {sessions.filter(s => s.status === 'open').length > 0 && (
              <View style={styles.section}>
                <Text style={styles.sectionTitle}>Sessões a Pagar</Text>
                {sessions.filter(s => s.status === 'open').map((session, i) => (
                  <View key={i} style={styles.card}>
                    <Text style={styles.cardTitle}>
                      {session.spot ? `Vaga ${session.spot}` : 'Em curso'}
                    </Text>
                    <Text style={styles.cardText}>€{getCurrentCost(session.entry_time)}</Text>
                    <TouchableOpacity
                      style={styles.smallButton}
                      onPress={() => handlePay(session.id, parseFloat(getCurrentCost(session.entry_time)))}
                    >
                      <Text style={styles.buttonText}>Pagar</Text>
                    </TouchableOpacity>
                  </View>
                ))}
              </View>
            )}
            
            {/* Stats */}
            <View style={styles.section}>
              <Text style={styles.sectionTitle}>Estacionamentos</Text>
              <View style={styles.statsRow}>
              <View style={[styles.statCardFree]}>
                <Text style={styles.statNumber}>{freeSpots.length}</Text>
                <Text style={styles.statLabel}>Livres</Text>
              </View>
              <View style={[styles.statCardOccupied]}>
                <Text style={styles.statNumber}>{occupiedSpots.length}</Text>
                <Text style={styles.statLabel}>Ocupados</Text>
              </View>
            </View>
            </View>
            

            {/* Reservations */}
            {reservations.length > 0 && (
              <View style={styles.section}>
                <Text style={styles.sectionTitle}>Minhas Reservas</Text>
                {reservations.map((res, i) => (
                  <View key={i} style={styles.reservationCard}>
                    <View>
                      <Text style={styles.cardTitle}>Vaga {res.spot}</Text>
                      <Text style={styles.cardText}>
                        Expira: {new Date(res.expires_at * 1000).toLocaleString('pt-PT')}
                      </Text>
                    </View>
                    <TouchableOpacity
                      style={styles.cancelButton}
                      onPress={() => handleCancelReservation(res.spot)}
                    >
                      <Text style={styles.cancelButtonText}>Cancelar</Text>
                    </TouchableOpacity>
                  </View>
                ))}
              </View>
            )}
            
            {/* Session History */}
            <View style={styles.section}>
              <Text style={styles.sectionTitle}>Histórico</Text>
              {sessions.filter(s => s.status !== 'open').length === 0 ? (
                <Text style={styles.emptyText}>Nenhuma sessão anterior</Text>
              ) : (
                sessions.filter(s => s.status !== 'open').slice(0, 5).map((session, i) => (
                  <View key={i} style={styles.card}>
                    <View style={styles.sessionHeader}>
                      <Text style={styles.cardTitle}>
                        {session.spot ? `Vaga ${session.spot}` : 'Sessão'}
                      </Text>
                      <Text style={[
                        styles.sessionStatus,
                        { color: session.status === 'paid' ? colors.success : colors.warning }
                      ]}>
                        {session.status === 'paid' ? 'Pago' : 'Terminada'}
                      </Text>
                    </View>
                    <Text style={styles.cardText}>
                      {new Date(session.entry_time).toLocaleString('pt-PT')}
                    </Text>
                    {session.amount_paid > 0 && (
                      <Text style={styles.amount}>€{session.amount_paid.toFixed(2)}</Text>
                    )}
                  </View>
                ))
              )}
            </View>
          </>
        )}

        {activeTab === 'spots' && (
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>Vagas Disponíveis</Text>
            {spotsList.map((spot, i) => (
              <View key={i} style={styles.spotCard}>
                <View>
                  <Text style={styles.spotName}>{spot.name}</Text>
                  <Text style={[
                    styles.spotStatus,
                    { color: spot.occupied ? colors.danger : spot.reserved ? colors.warning : colors.success }
                  ]}>
                    {spot.occupied ? 'Ocupado' : spot.reserved ? 'Reservado' : 'Livre'}
                  </Text>
                </View>
                {!spot.occupied && !spot.reserved && (
                  <TouchableOpacity
                    style={styles.smallButton}
                    onPress={() => openReserveModal(spot.name)}
                  >
                    <Text style={styles.buttonText}>Reservar</Text>
                  </TouchableOpacity>
                )}
              </View>
            ))}
          </View>
        )}

        {activeTab === 'settings' && (
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>Definições</Text>
            
            {/* User Info */}
            <View style={styles.settingsCard}>
              <Text style={styles.settingsLabel}>Nome</Text>
              <Text style={styles.settingsValue}>{user?.name}</Text>
            </View>
            
            <View style={styles.settingsCard}>
              <Text style={styles.settingsLabel}>Matrícula</Text>
              <Text style={styles.settingsValue}>{user?.plate}</Text>
            </View>
            
            <View style={styles.settingsCard}>
              <Text style={styles.settingsLabel}>Tarifa</Text>
              <Text style={styles.settingsValue}>€{parkingRate.toFixed(2)}/hora</Text>
            </View>
            
            {/* Logout Button */}
            <TouchableOpacity
              style={styles.logoutButton}
              onPress={onLogout}
            >
              <Text style={styles.logoutButtonText}>Terminar Sessão</Text>
            </TouchableOpacity>
          </View>
        )}
      </ScrollView>

      {/* Duration Picker Modal */}
      <Modal
        visible={showReserveModal}
        transparent={true}
        animationType="slide"
        onRequestClose={() => setShowReserveModal(false)}
      >
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <Text style={styles.modalTitle}>Reservar {selectedSpot}</Text>
            <Text style={styles.modalSubtitle}>Selecione a duração</Text>
            
            <View style={styles.durationGrid}>
              {durationOptions.map((hours) => (
                <TouchableOpacity
                  key={hours}
                  style={[
                    styles.durationButton,
                    selectedDuration === hours && styles.durationButtonActive
                  ]}
                  onPress={() => setSelectedDuration(hours)}
                >
                  <Text style={[
                    styles.durationButtonText,
                    selectedDuration === hours && styles.durationButtonTextActive
                  ]}>
                    {hours}h
                  </Text>
                </TouchableOpacity>
              ))}
            </View>
            
            <View style={styles.modalButtons}>
              <TouchableOpacity
                style={styles.modalCancelBtn}
                onPress={() => setShowReserveModal(false)}
              >
                <Text style={styles.modalCancelText}>Cancelar</Text>
              </TouchableOpacity>
              <TouchableOpacity
                style={styles.modalConfirmBtn}
                onPress={handleReserve}
              >
                <Text style={styles.buttonText}>Reservar</Text>
              </TouchableOpacity>
            </View>
          </View>
        </View>
      </Modal>
    </SafeAreaView>
  );
};

// Main App
export default function App() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    checkAuth();
  }, []);

  const checkAuth = async () => {
    try {
      const storedUser = await AsyncStorage.getItem('user');
      const token = await AsyncStorage.getItem('token');
      if (storedUser && token) {
        setUser(JSON.parse(storedUser));
      }
    } catch (e) {
      console.log('Auth check error:', e);
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = async () => {
    await AsyncStorage.removeItem('token');
    await AsyncStorage.removeItem('user');
    setUser(null);
  };

  if (loading) {
    return (
      <View style={[styles.container, styles.centered]}>
        <Text style={styles.logo}>🚗</Text>
        <Text style={styles.title}>TugaPark</Text>
        <ActivityIndicator color={colors.primary} style={{ marginTop: 20 }} />
      </View>
    );
  }

  return user ? (
    <HomeScreen user={user} onLogout={handleLogout} />
  ) : (
    <LoginScreen onLogin={setUser} />
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.background,
  },
  centered: {
    justifyContent: 'center',
    alignItems: 'center',
  },
  scrollContent: {
    flexGrow: 1,
    padding: 24,
    justifyContent: 'center',
  },
  header: {
    alignItems: 'center',
    marginBottom: 32,
  },
  logo: {
    fontSize: 64,
    marginBottom: 8,
  },
  title: {
    fontSize: 40,
    fontWeight: 'bold',
    color: colors.text,
  },
  subtitle: {
    fontSize: 16,
    color: colors.textSecondary,
    marginTop: 4,
  },
  card: {
    backgroundColor: colors.surface,
    borderRadius: 16,
    padding: 16,
    marginBottom: 12,
    borderWidth: 1,
    borderColor: colors.border,
  },
  cardTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: colors.text,
    marginBottom: 4,
  },
  cardText: {
    fontSize: 14,
    color: colors.textSecondary,
  },
  label: {
    fontSize: 14,
    color: colors.textSecondary,
    marginBottom: 4,
    marginTop: 12,
  },
  input: {
    backgroundColor: colors.background,
    borderRadius: 12,
    padding: 16,
    fontSize: 16,
    color: colors.text,
    borderWidth: 1,
    borderColor: colors.border,
  },
  error: {
    color: colors.danger,
    fontSize: 14,
    marginTop: 12,
    textAlign: 'center',
  },
  button: {
    backgroundColor: colors.primary,
    borderRadius: 12,
    padding: 16,
    alignItems: 'center',
    marginTop: 24,
  },
  buttonDisabled: {
    opacity: 0.6,
  },
  buttonText: {
    color: colors.secondary,
    fontSize: 16,
    fontWeight: '600',
  },
  switchButton: {
    marginTop: 16,
    alignItems: 'center',
  },
  switchText: {
    color: colors.secondary,
    fontSize: 14,
  },
  homeHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 16,
    paddingTop: 30,
    backgroundColor: colors.surface,
  },
  greeting: {
    fontSize: 20,
    fontWeight: 'bold',
    color: colors.text,
  },
  plate: {
    fontSize: 14,
    color: colors.primary,
    marginTop: 2,
  },
  logoutText: {
    color: colors.danger,
    fontSize: 14,
  },
  tabs: {
    flexDirection: 'row',
    backgroundColor: colors.surface,
    paddingHorizontal: 8,
    paddingBottom: 8,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
  },
  tab: {
    flex: 1,
    paddingVertical: 10,
    alignItems: 'center',
    borderRadius: 8,
  },
  tabActive: {
    backgroundColor: colors.primary,
  },
  tabText: {
    fontSize: 12,
    color: colors.textSecondary,
  },
  tabTextActive: {
    color: colors.text,
    fontWeight: '600',
  },
  content: {
    flex: 1,
    padding: 16,
  },
  statsRow: {
    flexDirection: 'row',
    gap: 12,
    marginBottom: 16,
  },
  statCardFree: {
    flex: 1,
    backgroundColor: colors.surface,
    borderRadius: 12,
    padding: 16,
    alignItems: 'center',
    borderColor: colors.primary,
    borderWidth: 1,
  },
  statCardOccupied: {
    flex: 1,
    backgroundColor: colors.surface,
    borderRadius: 12,
    padding: 16,
    alignItems: 'center',
    borderColor: colors.danger,
    borderWidth: 1,
  },
  statNumber: {
    fontSize: 32,
    fontWeight: 'bold',
    color: colors.text,
  },
  statLabel: {
    fontSize: 12,
    color: colors.textSecondary,
    marginTop: 4,
  },
  section: {
    marginBottom: 16,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: colors.text,
    marginBottom: 12,
  },
  spotCard: {
    backgroundColor: colors.surface,
    borderRadius: 12,
    padding: 16,
    marginBottom: 8,
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    borderWidth: 1,
    borderColor: colors.border,
  },
  spotName: {
    fontSize: 18,
    fontWeight: 'bold',
    color: colors.text,
  },
  spotStatus: {
    fontSize: 14,
    marginTop: 4,
  },
  smallButton: {
    backgroundColor: colors.primary,
    borderRadius: 8,
    paddingVertical: 8,
    paddingHorizontal: 16,
    marginTop: 8,
  },
  sessionHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  sessionStatus: {
    fontSize: 12,
    fontWeight: '600',
  },
  amount: {
    fontSize: 18,
    fontWeight: 'bold',
    color: colors.primary,
    marginTop: 8,
  },
  emptyText: {
    color: colors.textSecondary,
    textAlign: 'center',
    padding: 32,
  },
  loadingText: {
    color: colors.textSecondary,
    marginTop: 16,
  },
  // Reservation card
  reservationCard: {
    backgroundColor: colors.surface,
    borderRadius: 12,
    padding: 16,
    marginBottom: 8,
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    borderWidth: 1,
    borderColor: colors.warning,
  },
  cancelButton: {
    backgroundColor: colors.danger,
    borderRadius: 8,
    paddingVertical: 8,
    paddingHorizontal: 12,
  },
  cancelButtonText: {
    color: colors.textInverse,
    fontSize: 12,
    fontWeight: '600',
  },
  // Settings styles
  settingsCard: {
    backgroundColor: colors.surface,
    borderRadius: 12,
    padding: 16,
    marginBottom: 8,
    borderWidth: 1,
    borderColor: colors.border,
  },
  settingsLabel: {
    fontSize: 12,
    color: colors.textSecondary,
    marginBottom: 4,
  },
  settingsValue: {
    fontSize: 16,
    color: colors.text,
    fontWeight: '500',
  },
  logoutButton: {
    backgroundColor: colors.danger,
    borderRadius: 12,
    padding: 16,
    alignItems: 'center',
    marginTop: 24,
  },
  logoutButtonText: {
    color: colors.textInverse,
    fontSize: 16,
    fontWeight: '600',
  },
  // Modal styles
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.5)',
    justifyContent: 'flex-end',
  },
  modalContent: {
    backgroundColor: colors.surface,
    borderTopLeftRadius: 24,
    borderTopRightRadius: 24,
    padding: 24,
  },
  modalTitle: {
    fontSize: 20,
    fontWeight: 'bold',
    color: colors.text,
    textAlign: 'center',
  },
  modalSubtitle: {
    fontSize: 14,
    color: colors.textSecondary,
    textAlign: 'center',
    marginTop: 4,
    marginBottom: 20,
  },
  durationGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 12,
    justifyContent: 'center',
    marginBottom: 24,
  },
  durationButton: {
    width: 64,
    height: 44,
    borderRadius: 12,
    borderWidth: 2,
    borderColor: colors.border,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: colors.background,
  },
  durationButtonActive: {
    borderColor: colors.primary,
    backgroundColor: colors.primary,
  },
  durationButtonText: {
    fontSize: 16,
    fontWeight: '600',
    color: colors.text,
  },
  durationButtonTextActive: {
    color: colors.secondary,
  },
  modalButtons: {
    flexDirection: 'row',
    gap: 12,
  },
  modalCancelBtn: {
    flex: 1,
    padding: 16,
    borderRadius: 12,
    alignItems: 'center',
    backgroundColor: colors.background,
    borderWidth: 1,
    borderColor: colors.border,
  },
  modalCancelText: {
    color: colors.text,
    fontSize: 16,
    fontWeight: '600',
  },
  modalConfirmBtn: {
    flex: 1,
    padding: 16,
    borderRadius: 12,
    alignItems: 'center',
    backgroundColor: colors.primary,
  },
  // Alert styles
  alertsSection: {
    marginBottom: 16,
  },
  alertCard: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 12,
    borderRadius: 12,
    marginBottom: 8,
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.border,
  },
  alertWarning: {
    backgroundColor: '#fef3c7',
    borderColor: '#f59e0b',
  },
  alertDanger: {
    backgroundColor: '#fee2e2',
    borderColor: '#ef4444',
  },
  alertInfo: {
    backgroundColor: '#dbeafe',
    borderColor: '#3b82f6',
  },
  alertIconContainer: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: 'rgba(0,0,0,0.15)',
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 12,
  },
  alertContent: {
    flex: 1,
  },
  alertTitle: {
    fontSize: 14,
    fontWeight: '600',
    color: colors.text,
  },
  alertMessage: {
    fontSize: 12,
    color: colors.textSecondary,
    marginTop: 2,
  },
  // Timer styles
  activeSessionSection: {
    marginBottom: 16,
  },
  timerCard: {
    backgroundColor: colors.primary,
    borderRadius: 16,
    padding: 20,
    marginTop: 8,
  },
  timerHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 12,
  },
  timerSpot: {
    fontSize: 18,
    fontWeight: 'bold',
    color: colors.secondary,
  },
  timerBadge: {
    backgroundColor: colors.secondary,
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 12,
  },
  timerBadgeText: {
    color: colors.primary,
    fontSize: 10,
    fontWeight: 'bold',
  },
  timerDisplay: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'baseline',
  },
  timerTime: {
    fontSize: 36,
    fontWeight: 'bold',
    color: colors.secondary,
  },
  timerCost: {
    fontSize: 24,
    fontWeight: '600',
    color: colors.secondary,
  },
  timerEntry: {
    fontSize: 12,
    color: colors.secondary,
    marginTop: 8,
    opacity: 0.7,
  },
});
