// TugaPark Mobile App - Simplified Main Entry
import React, { useState, useEffect, useRef } from 'react';
import {
 View,
 Text,
 TextInput,
 TouchableOpacity,
 StyleSheet,
 SafeAreaView,
 ActivityIndicator,
 ScrollView,
 KeyboardAvoidingView,
 Platform,
 RefreshControl,
 Modal,
 Animated,
 Switch,
 Dimensions,
} from 'react-native';
import { StatusBar } from 'expo-status-bar';
import AsyncStorage from '@react-native-async-storage/async-storage';
import axios from 'axios';
import Svg, { Path, Circle, Rect } from 'react-native-svg';
import * as Haptics from 'expo-haptics';
import * as LocalAuthentication from 'expo-local-authentication';
import { LinearGradient } from 'expo-linear-gradient';
import Toast from 'react-native-toast-message';

const { width: SCREEN_WIDTH } = Dimensions.get('window');

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

// Empty State Icon
const EmptyBoxIcon = ({ size = 80, color = '#999999' }) => (
 <Svg width={size} height={size} viewBox="0 0 24 24">
 <Path
 fill={color}
 d="M20 2H4C2.9 2 2 2.9 2 4V20C2 21.1 2.9 22 4 22H20C21.1 22 22 21.1 22 20V4C22 2.9 21.1 2 20 2ZM20 20H4V4H20V20ZM6 10H18V12H6ZM6 14H14V16H6Z"
 />
 </Svg>
);

// Parking Icon for Empty Spots
const ParkingIcon = ({ size = 80, color = '#999999' }) => (
 <Svg width={size} height={size} viewBox="0 0 24 24">
 <Path
 fill={color}
 d="M13 3H6V21H10V15H13C16.31 15 19 12.31 19 9S16.31 3 13 3ZM13 11H10V7H13C14.1 7 15 7.9 15 9S14.1 11 13 11Z"
 />
 </Svg>
);

// History Icon for Empty Sessions
const HistoryIcon = ({ size = 80, color = '#999999' }) => (
 <Svg width={size} height={size} viewBox="0 0 24 24">
 <Path
 fill={color}
 d="M13 3C8.03 3 4 7.03 4 12H1L4.89 15.89L4.96 16.03L9 12H6C6 8.13 9.13 5 13 5S20 8.13 20 12 16.87 19 13 19C11.07 19 9.32 18.21 8.06 16.94L6.64 18.36C8.27 20 10.5 21 13 21C17.97 21 22 16.97 22 12S17.97 3 13 3ZM12 8V13L16.28 15.54L17 14.33L13.5 12.25V8H12Z"
 />
 </Svg>
);

// Biometric Icon
const BiometricIcon = ({ size = 24, color = '#666666' }) => (
 <Svg width={size} height={size} viewBox="0 0 24 24">
 <Path
 fill={color}
 d="M17.81 4.47C17.73 4.47 17.65 4.45 17.58 4.41C16.21 3.82 14.53 3.5 12.75 3.5C10.97 3.5 9.29 3.82 7.92 4.41C7.66 4.51 7.35 4.39 7.25 4.13C7.15 3.86 7.27 3.56 7.54 3.47C9.03 2.81 10.85 2.5 12.75 2.5C14.65 2.5 16.47 2.81 17.96 3.47C18.22 3.57 18.34 3.87 18.24 4.13C18.17 4.34 17.99 4.47 17.81 4.47ZM3.5 9.72C3.38 9.72 3.26 9.68 3.16 9.6C2.93 9.41 2.91 9.08 3.1 8.85C4.04 7.72 5.26 6.82 6.7 6.2C9.62 4.94 13.17 4.94 16.09 6.2C17.54 6.82 18.75 7.72 19.7 8.85C19.89 9.08 19.87 9.41 19.64 9.6C19.41 9.79 19.08 9.77 18.89 9.54C18.04 8.54 17.04 7.73 15.83 7.2C13.21 6.06 10.08 6.06 7.46 7.2C6.25 7.73 5.25 8.54 4.4 9.54C4.3 9.66 4.15 9.72 3.5 9.72ZM9.75 21.79C9.62 21.79 9.5 21.74 9.39 21.64C8.52 20.77 8 19.63 8 18.5C8 15.88 10.14 13.75 12.75 13.75C15.36 13.75 17.5 15.88 17.5 18.5C17.5 18.77 17.27 19 17 19C16.73 19 16.5 18.77 16.5 18.5C16.5 16.43 14.82 14.75 12.75 14.75C10.68 14.75 9 16.43 9 18.5C9 19.34 9.39 20.21 10.06 20.88C10.26 21.08 10.26 21.42 10.06 21.62C9.97 21.73 9.86 21.79 9.75 21.79ZM12.75 22.5C12.48 22.5 12.25 22.27 12.25 22V20.5C12.25 20.23 12.48 20 12.75 20C13.02 20 13.25 20.23 13.25 20.5V22C13.25 22.27 13.02 22.5 12.75 22.5ZM20.75 22.5C20.63 22.5 20.5 22.45 20.4 22.36C19.32 21.34 18.75 19.97 18.75 18.5C18.75 15.19 21.44 12.5 24.75 12.5C24.75 12.5 25 12.73 25 13C25 13.27 24.77 13.5 24.5 13.5C22.02 13.5 19.75 15.47 19.75 18.5C19.75 19.71 20.22 20.86 21.1 21.7C21.31 21.9 21.31 22.23 21.11 22.44C21.01 22.48 20.88 22.5 20.75 22.5Z"
 />
 </Svg>
);

// Moon Icon for Dark Mode
const MoonIcon = ({ size = 24, color = '#666666' }) => (
 <Svg width={size} height={size} viewBox="0 0 64 64">
 <Path
 fill={color}
 d="M55.68,36.83c0.32,0.45,0.41,1.02,0.22,1.57C52.59,47.73,43.72,54,33.83,54c-12.9,0-23.4-10.5-23.4-23.41c0-11.02,7.83-20.65,18.61-22.9c0.12-0.03,0.24-0.04,0.36-0.04c0.65,0,1.23,0.37,1.53,0.96c0.3,0.61,0.24,1.33-0.19,1.89C28.25,13.62,27,17,27,23c0.44,5.97,3.66,11.21,9,14c2.42,1.23,5.62,1.82,8.38,1.82c3.14,0,6.24-0.86,8.96-2.48c0.27-0.17,0.58-0.25,0.9-0.25C54.81,36.09,55.35,36.36,55.68,36.83z"
 />
 </Svg>
);

// API Configuration
const API_BASE_URL = 'http:

// WebSocket URL (derived from API URL)
const WS_URL = API_BASE_URL.replace('http://', 'ws://').replace('https://', 'wss://') + '/ws';

// Colors - Light Theme (matching frontend)
const lightColors = {
 primary: '#c8e620', // Lime Green
 primaryDark: '#9fc21a',
 secondary: '#1e1e1e', // Dark
 background: '#f5f5f5', // Light gray
 surface: '#ffffff', // White
 surfaceHover: '#f0f0f0',
 text: '#1a1a1a', // Dark text
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
 skeleton: '#e0e0e0',
 skeletonHighlight: '#f5f5f5',
};

// Colors - Dark Theme
const darkColors = {
 primary: '#97d700', // Keep lime green
 primaryDark: '#7ab800',
 secondary: '#ffffff', // Invert for contrast
 background: '#121212', // Dark background
 surface: '#1e1e1e', // Dark surface
 surfaceHover: '#2a2a2a',
 text: '#ffffff', // Light text
 textSecondary: '#a0a0a0',
 textMuted: '#666666',
 textInverse: '#1a1a1a',
 border: '#333333',
 success: '#22c55e',
 danger: '#ef4444',
 warning: '#f59e0b',
 info: '#3b82f6',
 spotAvailable: '#c8e620',
 spotOccupied: '#ef4444',
 spotReserved: '#f59e0b',
 skeleton: '#2a2a2a',
 skeletonHighlight: '#3a3a3a',
};

// Default colors (will be overridden by theme)
let colors = lightColors;

// Helper function to trigger haptic feedback
const triggerHaptic = (style = 'light') => {
 const styles = {
 light: Haptics.ImpactFeedbackStyle.Light,
 medium: Haptics.ImpactFeedbackStyle.Medium,
 heavy: Haptics.ImpactFeedbackStyle.Heavy,
 };
 Haptics.impactAsync(styles[style] || styles.light);
};

// Helper function to show toast
const showToast = (type, text1, text2 = '') => {
 Toast.show({
 text1,
 text2,
 position: 'top',
 visibilityTime: 3000,
 autoHide: true,
 topOffset: 60,
 });
};

// Skeleton Loading Component
const SkeletonBox = ({ width, height, borderRadius = 8, style }) => {
 const animatedValue = useRef(new Animated.Value(0)).current;

 useEffect(() => {
 const animation = Animated.loop(
 Animated.sequence([
 Animated.timing(animatedValue, {
 toValue: 1,
 duration: 1000,
 useNativeDriver: true,
 }),
 Animated.timing(animatedValue, {
 toValue: 0,
 duration: 1000,
 useNativeDriver: true,
 }),
 ])
 );
 animation.start();
 return () => animation.stop();
 }, []);

 const opacity = animatedValue.interpolate({
 inputRange: [0, 1],
 outputRange: [0.3, 0.7],
 });

 return (
 <Animated.View
 style={[
 {
 width,
 height,
 borderRadius,
 backgroundColor: colors.skeleton,
 opacity,
 },
 style,
 ]}
 />
 );
};

// Skeleton Card for Spots/Sessions
const SkeletonCard = () => (
 <View style={[styles.card, { padding: 16, marginBottom: 12 }]}>
 <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' }}>
 <View>
 <SkeletonBox width={80} height={20} style={{ marginBottom: 8 }} />
 <SkeletonBox width={60} height={14} />
 </View>
 <SkeletonBox width={80} height={36} borderRadius={8} />
 </View>
 </View>
);

// Empty State Component
const EmptyState = ({ icon: Icon, title, subtitle, theme }) => (
 <View style={styles.emptyStateContainer}>
 <Icon size={80} color={theme.textMuted} />
 <Text style={[styles.emptyStateTitle, { color: theme.text }]}>{title}</Text>
 <Text style={[styles.emptyStateSubtitle, { color: theme.textSecondary }]}>{subtitle}</Text>
 </View>
);

// Confirmation Modal Component
const ConfirmModal = ({ visible, title, message, confirmText, cancelText, onConfirm, onCancel, theme, isDanger = false }) => (
 <Modal
 visible={visible}
 transparent={true}
 animationType="fade"
 onRequestClose={onCancel}
 >
 <View style={styles.confirmModalOverlay}>
 <View style={[styles.confirmModalContent, { backgroundColor: theme.surface }]}>
 <Text style={[styles.confirmModalTitle, { color: theme.text }]}>{title}</Text>
 <Text style={[styles.confirmModalMessage, { color: theme.textSecondary }]}>{message}</Text>
 <View style={styles.confirmModalButtons}>
 <TouchableOpacity
 style={[styles.confirmModalBtn, { backgroundColor: theme.background, borderColor: theme.border, borderWidth: 1 }]}
 onPress={() => {
 triggerHaptic('light');
 onCancel();
 }}
 >
 <Text style={[styles.confirmModalBtnText, { color: theme.text }]}>{cancelText || 'Cancelar'}</Text>
 </TouchableOpacity>
 <TouchableOpacity
 style={[styles.confirmModalBtn, { backgroundColor: isDanger ? theme.danger : theme.primary }]}
 onPress={() => {
 triggerHaptic('medium');
 onConfirm();
 }}
 >
 <Text style={[styles.confirmModalBtnText, { color: isDanger ? '#fff' : theme.secondary }]}>{confirmText || 'Confirmar'}</Text>
 </TouchableOpacity>
 </View>
 </View>
 </View>
 </Modal>
);

// Splash Screen Component
const SplashScreen = ({ onFinish, theme }) => {
 const fadeAnim = useRef(new Animated.Value(0)).current;
 const scaleAnim = useRef(new Animated.Value(0.8)).current;
 const logoFade = useRef(new Animated.Value(0)).current;

 // Cores do gradiente baseadas no tema
 const isDark = theme === darkColors;
 const gradientColors = isDark
 ? ['#1e1e1e', '#2d2d2d', '#1e1e1e'] // Dark mode
 : ['#f5f5f5', '#ffffff', '#f5f5f5']; // Light mode

 useEffect(() => {
 // Animate in
 Animated.parallel([
 Animated.timing(fadeAnim, {
 toValue: 1,
 duration: 500,
 useNativeDriver: true,
 }),
 Animated.spring(scaleAnim, {
 toValue: 1,
 friction: 8,
 tension: 40,
 useNativeDriver: true,
 }),
 Animated.timing(logoFade, {
 toValue: 1,
 duration: 800,
 delay: 200,
 useNativeDriver: true,
 }),
 ]).start();

 // Minimum splash duration
 const timer = setTimeout(() => {
 Animated.timing(fadeAnim, {
 toValue: 0,
 duration: 400,
 useNativeDriver: true,
 }).start(() => onFinish());
 }, 2000);

 return () => clearTimeout(timer);
 }, []);

 return (
 <Animated.View style={[styles.splashContainer, { opacity: fadeAnim }]}>
 <LinearGradient
 colors={gradientColors}
 style={styles.splashGradient}
 >
 <StatusBar style={isDark ? 'light' : 'dark'} />
 <Animated.View style={{ transform: [{ scale: scaleAnim }], opacity: logoFade }}>
 <Text style={[styles.splashTitle, { color: theme.primary }]}>TugaPark</Text>
 <Text style={[styles.splashSubtitle, { color: theme.textSecondary }]}>Estacionamento inteligente</Text>
 </Animated.View>
 <ActivityIndicator color={theme.primary} size="large" style={{ marginTop: 40 }} />
 </LinearGradient>
 </Animated.View>
 );
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
const LoginScreen = ({ onLogin, theme }) => {
 const [email, setEmail] = useState('');
 const [password, setPassword] = useState('');
 const [name, setName] = useState('');
 const [isRegister, setIsRegister] = useState(false);
 const [loading, setLoading] = useState(false);
 const [error, setError] = useState('');

 const handleSubmit = async () => {
 triggerHaptic('medium');

 if (!email.trim() || !password.trim()) {
 setError('Preencha email e password');
 return;
 }

 if (isRegister && !name.trim()) {
 setError('Preencha o nome');
 return;
 }

 setLoading(true);
 setError('');

 try {
 let response;
 if (isRegister) {
 // Register with email, password, name
 response = await api.post('/api/auth/register', {
 email: email.trim().toLowerCase(),
 password: password,
 full_name: name.trim(),
 });
 } else {
 // Login with email (identifier) + password
 response = await api.post('/api/auth/login', {
 identifier: email.trim().toLowerCase(),
 password: password,
 });
 }

 await AsyncStorage.setItem('token', response.data.token);
 await AsyncStorage.setItem('user', JSON.stringify(response.data.user));
 showToast('success', isRegister ? 'Conta criada!' : 'Bem-vindo!', `Olá, ${response.data.user.name}`);
 onLogin(response.data.user);
 } catch (e) {
 const errorMsg = e.response?.data?.detail || e.message || 'Erro ao conectar';
 setError(errorMsg);
 showToast('error', 'Erro', errorMsg);
 } finally {
 setLoading(false);
 }
 };

 return (
 <SafeAreaView style={[styles.container, { backgroundColor: theme.background }]}>
 <StatusBar style={theme === darkColors ? 'light' : 'dark'} />
 <KeyboardAvoidingView
 behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
 style={{ flex: 1 }}
 >
 <ScrollView
 contentContainerStyle={styles.scrollContent}
 keyboardShouldPersistTaps="handled"
 >
 <View style={styles.header}>
 <Text style={[styles.title, { color: theme.primary }]}>TugaPark</Text>
 <Text style={[styles.subtitle, { color: theme.textSecondary }]}>Estacionamento inteligente</Text>
 </View>

 <View style={[styles.card, { backgroundColor: theme.surface, borderColor: theme.border }]}>
 <Text style={[styles.cardTitle, { color: theme.text }]}>{isRegister ? 'Criar Conta' : 'Entrar'}</Text>

 {isRegister && (
 <>
 <Text style={[styles.label, { color: theme.textSecondary }]}>Nome completo</Text>
 <TextInput
 style={[styles.input, { backgroundColor: theme.background, borderColor: theme.border, color: theme.text }]}
 placeholder="João Silva"
 placeholderTextColor={theme.textMuted}
 value={name}
 onChangeText={setName}
 autoCapitalize="words"
 />
 </>
 )}

 <Text style={[styles.label, { color: theme.textSecondary }]}>Email</Text>
 <TextInput
 style={[styles.input, { backgroundColor: theme.background, borderColor: theme.border, color: theme.text }]}
 placeholder="email@exemplo.com"
 placeholderTextColor={theme.textMuted}
 value={email}
 onChangeText={setEmail}
 autoCapitalize="none"
 keyboardType="email-address"
 autoComplete="email"
 />

 <Text style={[styles.label, { color: theme.textSecondary }]}>Password</Text>
 <TextInput
 style={[styles.input, { backgroundColor: theme.background, borderColor: theme.border, color: theme.text }]}
 placeholder="••••••••"
 placeholderTextColor={theme.textMuted}
 value={password}
 onChangeText={setPassword}
 secureTextEntry
 autoComplete="password"
 />

 {error ? <Text style={styles.error}>{error}</Text> : null}

 <TouchableOpacity
 style={[styles.button, { backgroundColor: theme.primary }, loading && styles.buttonDisabled]}
 onPress={handleSubmit}
 disabled={loading}
 >
 {loading ? (
 <ActivityIndicator color={theme.secondary} />
 ) : (
 <Text style={[styles.buttonText, { color: theme.secondary }]}>
 {isRegister ? 'Registar' : 'Entrar'}
 </Text>
 )}
 </TouchableOpacity>

 <TouchableOpacity
 style={styles.switchButton}
 onPress={() => {
 triggerHaptic('light');
 setIsRegister(!isRegister);
 setError('');
 }}
 >
 <Text style={[styles.switchText, { color: theme.textSecondary }]}>
 {isRegister ? 'Já tem conta? Entrar' : 'Não tem conta? Registar'}
 </Text>
 </TouchableOpacity>

 {isRegister && (
 <Text style={[{ color: theme.textMuted, fontSize: 12, textAlign: 'center', marginTop: 12 }]}>
 Após criar conta, adicione os seus veículos nas Definições
 </Text>
 )}
 </View>
 </ScrollView>
 </KeyboardAvoidingView>
 </SafeAreaView>
 );
};

// Car Icon for Vehicles
const CarIcon = ({ size = 24, color = '#666666' }) => (
 <Svg width={size} height={size} viewBox="0 0 24 24">
 <Path
 fill={color}
 d="M5,11L6.5,6.5H17.5L19,11M17.5,16A1.5,1.5 0 0,1 16,14.5A1.5,1.5 0 0,1 17.5,13A1.5,1.5 0 0,1 19,14.5A1.5,1.5 0 0,1 17.5,16M6.5,16A1.5,1.5 0 0,1 5,14.5A1.5,1.5 0 0,1 6.5,13A1.5,1.5 0 0,1 8,14.5A1.5,1.5 0 0,1 6.5,16M18.92,6C18.72,5.42 18.16,5 17.5,5H6.5C5.84,5 5.28,5.42 5.08,6L3,12V20A1,1 0 0,0 4,21H5A1,1 0 0,0 6,20V19H18V20A1,1 0 0,0 19,21H20A1,1 0 0,0 21,20V12L18.92,6Z"
 />
 </Svg>
);

// Credit Card Icon
const CreditCardIcon = ({ size = 24, color = '#666666' }) => (
 <Svg width={size} height={size} viewBox="0 0 24 24">
 <Path
 fill={color}
 d="M20,8H4V6H20M20,18H4V12H20M20,4H4C2.89,4 2,4.89 2,6V18A2,2 0 0,0 4,20H20A2,2 0 0,0 22,18V6C22,4.89 21.1,4 20,4Z"
 />
 </Svg>
);

// Plus Icon
const PlusIcon = ({ size = 24, color = '#666666' }) => (
 <Svg width={size} height={size} viewBox="0 0 24 24">
 <Path
 fill={color}
 d="M19,13H13V19H11V13H5V11H11V5H13V11H19V13Z"
 />
 </Svg>
);

// Settings Tab Component with Vehicles and Cards Management
const SettingsTab = ({ user, theme, isDarkMode, setIsDarkMode, parkingRate, onLogout, onSetupChange }) => {
 // Vehicles state
 const [vehicles, setVehicles] = useState([]);
 const [showVehicleForm, setShowVehicleForm] = useState(false);
 const [vehicleForm, setVehicleForm] = useState({ plate: '', brand: '', model: '', color: '' });
 const [vehicleLoading, setVehicleLoading] = useState(false);

 // Payment methods state
 const [paymentMethods, setPaymentMethods] = useState([]);
 const [showCardForm, setShowCardForm] = useState(false);
 const [cardForm, setCardForm] = useState({
 card_type: 'visa',
 card_number: '',
 card_holder_name: '',
 expiry_month: '',
 expiry_year: '',
 });
 const [cardLoading, setCardLoading] = useState(false);

 // Loading state
 const [loading, setLoading] = useState(true);

 // Load data on mount
 useEffect(() => {
 loadUserData();
 }, []);

 const loadUserData = async () => {
 setLoading(true);
 try {
 const [vehiclesRes, methodsRes] = await Promise.all([
 api.get('/api/user/vehicles'),
 api.get('/api/user/payment-methods'),
 ]);
 setVehicles(vehiclesRes.data.vehicles || []);
 setPaymentMethods(methodsRes.data.payment_methods || []);
 } catch (e) {
 console.log('Error loading user data:', e.message);
 } finally {
 setLoading(false);
 }
 };

 // Add vehicle
 const addVehicle = async () => {
 if (!vehicleForm.plate.trim()) {
 showToast('error', 'Erro', 'Indique a matrícula');
 return;
 }

 setVehicleLoading(true);
 try {
 await api.post('/api/user/vehicles', vehicleForm);
 showToast('success', 'Veículo adicionado!', vehicleForm.plate.toUpperCase());
 setVehicleForm({ plate: '', brand: '', model: '', color: '' });
 setShowVehicleForm(false);
 loadUserData();
 if (onSetupChange) onSetupChange();
 } catch (e) {
 showToast('error', 'Erro', e.response?.data?.detail || 'Falha ao adicionar veículo');
 } finally {
 setVehicleLoading(false);
 }
 };

 // Remove vehicle
 const removeVehicle = async (id, plate) => {
 try {
 await api.delete(`/api/user/vehicles/${id}`);
 showToast('success', 'Veículo removido', plate);
 loadUserData();
 if (onSetupChange) onSetupChange();
 } catch (e) {
 showToast('error', 'Erro', e.response?.data?.detail || 'Falha ao remover veículo');
 }
 };

 // Set vehicle as primary
 const setPrimaryVehicle = async (plate) => {
 try {
 await api.put(`/api/mobile/vehicles/${plate}/set-primary`);
 showToast('success', 'Veículo principal', `${plate} é agora o veículo principal`);
 loadUserData();
 if (onSetupChange) onSetupChange();
 } catch (e) {
 showToast('error', 'Erro', e.response?.data?.detail || 'Falha ao definir veículo principal');
 }
 };

 // Add payment card
 const addCard = async () => {
 if (!cardForm.card_number.trim() || !cardForm.card_holder_name.trim()) {
 showToast('error', 'Erro', 'Preencha todos os campos obrigatórios');
 return;
 }

 setCardLoading(true);
 try {
 await api.post('/api/user/payment-methods', {
 ...cardForm,
 expiry_month: parseInt(cardForm.expiry_month) || 12,
 expiry_year: parseInt(cardForm.expiry_year) || 2025,
 is_default: true,
 });
 showToast('success', 'Cartão adicionado!', '');
 setCardForm({
 card_type: 'visa',
 card_number: '',
 card_holder_name: '',
 expiry_month: '',
 expiry_year: '',
 });
 setShowCardForm(false);
 loadUserData();
 if (onSetupChange) onSetupChange();
 } catch (e) {
 showToast('error', 'Erro', e.response?.data?.detail || 'Falha ao adicionar cartão');
 } finally {
 setCardLoading(false);
 }
 };

 // Remove payment card
 const removeCard = async (id) => {
 try {
 await api.delete(`/api/user/payment-methods/${id}`);
 showToast('success', 'Cartão removido', '');
 loadUserData();
 if (onSetupChange) onSetupChange();
 } catch (e) {
 showToast('error', 'Erro', e.response?.data?.detail || 'Falha ao remover cartão');
 }
 };

 return (
 <>
 {/* User Info */}
 <View style={styles.section}>
 <Text style={[styles.sectionTitle, { color: theme.text }]}>Conta</Text>
 <View style={[styles.settingsCard, { backgroundColor: theme.surface, borderColor: theme.border }]}>
 <Text style={[styles.settingsLabel, { color: theme.textSecondary }]}>Nome</Text>
 <Text style={[styles.settingsValue, { color: theme.text }]}>{user?.name}</Text>
 </View>
 <View style={[styles.settingsCard, { backgroundColor: theme.surface, borderColor: theme.border }]}>
 <Text style={[styles.settingsLabel, { color: theme.textSecondary }]}>Email</Text>
 <Text style={[styles.settingsValue, { color: theme.text }]}>{user?.email}</Text>
 </View>
 <View style={[styles.settingsCard, { backgroundColor: theme.surface, borderColor: theme.border }]}>
 <Text style={[styles.settingsLabel, { color: theme.textSecondary }]}>Tarifa</Text>
 <Text style={[styles.settingsValue, { color: theme.text }]}>€{parkingRate.toFixed(2)}/hora</Text>
 </View>
 </View>

 {/* Vehicles Section */}
 <View style={styles.section}>
 <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
 <Text style={[styles.sectionTitle, { color: theme.text, marginBottom: 0 }]}>Meus Veículos</Text>
 <TouchableOpacity
 style={[styles.smallAddButton, { backgroundColor: theme.primary }]}
 onPress={() => {
 triggerHaptic('light');
 setShowVehicleForm(!showVehicleForm);
 }}
 >
 <PlusIcon size={18} color={theme.secondary} />
 <Text style={[{ color: theme.secondary, fontSize: 12, fontWeight: '600', marginLeft: 4 }]}>
 Adicionar
 </Text>
 </TouchableOpacity>
 </View>

 {/* Add Vehicle Form */}
 {showVehicleForm && (
 <View style={[styles.formCard, { backgroundColor: theme.surface, borderColor: theme.border }]}>
 <TextInput
 style={[styles.formInput, { backgroundColor: theme.background, borderColor: theme.border, color: theme.text }]}
 placeholder="Matrícula *"
 placeholderTextColor={theme.textMuted}
 value={vehicleForm.plate}
 onChangeText={(t) => setVehicleForm({ ...vehicleForm, plate: t.toUpperCase() })}
 autoCapitalize="characters"
 />
 <View style={{ flexDirection: 'row', gap: 8 }}>
 <TextInput
 style={[styles.formInput, { flex: 1, backgroundColor: theme.background, borderColor: theme.border, color: theme.text }]}
 placeholder="Marca"
 placeholderTextColor={theme.textMuted}
 value={vehicleForm.brand}
 onChangeText={(t) => setVehicleForm({ ...vehicleForm, brand: t })}
 />
 <TextInput
 style={[styles.formInput, { flex: 1, backgroundColor: theme.background, borderColor: theme.border, color: theme.text }]}
 placeholder="Modelo"
 placeholderTextColor={theme.textMuted}
 value={vehicleForm.model}
 onChangeText={(t) => setVehicleForm({ ...vehicleForm, model: t })}
 />
 </View>
 <TextInput
 style={[styles.formInput, { backgroundColor: theme.background, borderColor: theme.border, color: theme.text }]}
 placeholder="Cor"
 placeholderTextColor={theme.textMuted}
 value={vehicleForm.color}
 onChangeText={(t) => setVehicleForm({ ...vehicleForm, color: t })}
 />
 <View style={{ flexDirection: 'row', gap: 8, marginTop: 8 }}>
 <TouchableOpacity
 style={[styles.formButton, { flex: 1, backgroundColor: theme.background, borderColor: theme.border, borderWidth: 1 }]}
 onPress={() => setShowVehicleForm(false)}
 >
 <Text style={{ color: theme.text }}>Cancelar</Text>
 </TouchableOpacity>
 <TouchableOpacity
 style={[styles.formButton, { flex: 1, backgroundColor: theme.primary }]}
 onPress={() => {
 triggerHaptic('medium');
 addVehicle();
 }}
 disabled={vehicleLoading}
 >
 {vehicleLoading ? (
 <ActivityIndicator size="small" color={theme.secondary} />
 ) : (
 <Text style={{ color: theme.secondary, fontWeight: '600' }}>Adicionar</Text>
 )}
 </TouchableOpacity>
 </View>
 </View>
 )}

 {/* Vehicles List */}
 {loading ? (
 <SkeletonCard />
 ) : vehicles.length === 0 ? (
 <View style={[styles.settingsCard, { backgroundColor: theme.surface, borderColor: theme.border, alignItems: 'center', paddingVertical: 24 }]}>
 <CarIcon size={40} color={theme.textMuted} />
 <Text style={[{ color: theme.textSecondary, marginTop: 8, textAlign: 'center' }]}>
 Nenhum veículo registado
 </Text>
 </View>
 ) : (
 vehicles.map((v) => (
 <View key={v.id} style={[styles.vehicleCard, { backgroundColor: theme.surface, borderColor: v.is_primary ? theme.primary : theme.border, borderWidth: v.is_primary ? 2 : 1 }]}>
 <View style={{ flexDirection: 'row', alignItems: 'center', flex: 1 }}>
 <View style={{
 width: 40,
 height: 40,
 borderRadius: 20,
 backgroundColor: v.is_primary ? theme.primary + '20' : theme.background,
 alignItems: 'center',
 justifyContent: 'center',
 }}>
 <CarIcon size={22} color={v.is_primary ? theme.primary : theme.textSecondary} />
 </View>
 <View style={{ marginLeft: 12, flex: 1 }}>
 <View style={{ flexDirection: 'row', alignItems: 'center' }}>
 <Text style={[styles.vehiclePlate, { color: theme.text }]}>{v.plate}</Text>
 {v.is_primary && (
 <View style={{
 backgroundColor: theme.primary,
 paddingHorizontal: 6,
 paddingVertical: 2,
 borderRadius: 4,
 marginLeft: 8,
 }}>
 <Text style={{ fontSize: 9, fontWeight: '600', color: theme.secondary }}>PRINCIPAL</Text>
 </View>
 )}
 </View>
 <Text style={[{ color: theme.textSecondary, fontSize: 12 }]}>
 {[v.brand, v.model, v.color].filter(Boolean).join(' • ') || 'Sem detalhes'}
 </Text>
 </View>
 </View>
 <View style={{ flexDirection: 'row', gap: 8 }}>
 {!v.is_primary && (
 <TouchableOpacity
 style={[styles.smallButton, { backgroundColor: theme.primary }]}
 onPress={() => {
 triggerHaptic('light');
 setPrimaryVehicle(v.plate);
 }}
 >
 <Text style={{ color: theme.secondary, fontSize: 11, fontWeight: '600' }}>Principal</Text>
 </TouchableOpacity>
 )}
 <TouchableOpacity
 style={[styles.deleteButton, { backgroundColor: theme.danger }]}
 onPress={() => {
 triggerHaptic('medium');
 removeVehicle(v.id, v.plate);
 }}
 >
 <Text style={{ color: '#fff', fontSize: 11, fontWeight: '600' }}>Remover</Text>
 </TouchableOpacity>
 </View>
 </View>
 ))
 )}
 </View>

 {/* Payment Methods Section */}
 <View style={styles.section}>
 <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
 <Text style={[styles.sectionTitle, { color: theme.text, marginBottom: 0 }]}>Método de Pagamento</Text>
 {paymentMethods.length === 0 && (
 <TouchableOpacity
 style={[styles.smallAddButton, { backgroundColor: theme.primary }]}
 onPress={() => {
 triggerHaptic('light');
 setShowCardForm(!showCardForm);
 }}
 >
 <PlusIcon size={18} color={theme.secondary} />
 <Text style={[{ color: theme.secondary, fontSize: 12, fontWeight: '600', marginLeft: 4 }]}>
 Adicionar
 </Text>
 </TouchableOpacity>
 )}
 </View>

 {/* Add Card Form */}
 {showCardForm && (
 <View style={[styles.formCard, { backgroundColor: theme.surface, borderColor: theme.border }]}>
 <View style={[styles.formInput, { backgroundColor: theme.background, borderColor: theme.border, paddingVertical: 0 }]}>
 <Text style={{ color: theme.textMuted, fontSize: 12, marginBottom: 4, marginTop: 8 }}>Tipo de Cartão</Text>
 <View style={{ flexDirection: 'row', paddingBottom: 8 }}>
 {['visa', 'mastercard', 'amex'].map((type) => (
 <TouchableOpacity
 key={type}
 style={[
 styles.cardTypeButton,
 { borderColor: theme.border },
 cardForm.card_type === type && { borderColor: theme.primary, backgroundColor: theme.primary + '20' }
 ]}
 onPress={() => setCardForm({ ...cardForm, card_type: type })}
 >
 <Text style={[{ color: theme.text, fontSize: 12 }, cardForm.card_type === type && { fontWeight: '600' }]}>
 {type.charAt(0).toUpperCase() + type.slice(1)}
 </Text>
 </TouchableOpacity>
 ))}
 </View>
 </View>
 <TextInput
 style={[styles.formInput, { backgroundColor: theme.background, borderColor: theme.border, color: theme.text }]}
 placeholder="Número do Cartão *"
 placeholderTextColor={theme.textMuted}
 value={cardForm.card_number}
 onChangeText={(t) => setCardForm({ ...cardForm, card_number: t })}
 keyboardType="number-pad"
 />
 <TextInput
 style={[styles.formInput, { backgroundColor: theme.background, borderColor: theme.border, color: theme.text }]}
 placeholder="Nome no Cartão *"
 placeholderTextColor={theme.textMuted}
 value={cardForm.card_holder_name}
 onChangeText={(t) => setCardForm({ ...cardForm, card_holder_name: t.toUpperCase() })}
 autoCapitalize="characters"
 />
 <View style={{ flexDirection: 'row', gap: 8 }}>
 <TextInput
 style={[styles.formInput, { flex: 1, backgroundColor: theme.background, borderColor: theme.border, color: theme.text }]}
 placeholder="Mês (MM)"
 placeholderTextColor={theme.textMuted}
 value={cardForm.expiry_month}
 onChangeText={(t) => setCardForm({ ...cardForm, expiry_month: t })}
 keyboardType="number-pad"
 maxLength={2}
 />
 <TextInput
 style={[styles.formInput, { flex: 1, backgroundColor: theme.background, borderColor: theme.border, color: theme.text }]}
 placeholder="Ano (AAAA)"
 placeholderTextColor={theme.textMuted}
 value={cardForm.expiry_year}
 onChangeText={(t) => setCardForm({ ...cardForm, expiry_year: t })}
 keyboardType="number-pad"
 maxLength={4}
 />
 </View>
 <View style={{ flexDirection: 'row', gap: 8, marginTop: 8 }}>
 <TouchableOpacity
 style={[styles.formButton, { flex: 1, backgroundColor: theme.background, borderColor: theme.border, borderWidth: 1 }]}
 onPress={() => setShowCardForm(false)}
 >
 <Text style={{ color: theme.text }}>Cancelar</Text>
 </TouchableOpacity>
 <TouchableOpacity
 style={[styles.formButton, { flex: 1, backgroundColor: theme.primary }]}
 onPress={() => {
 triggerHaptic('medium');
 addCard();
 }}
 disabled={cardLoading}
 >
 {cardLoading ? (
 <ActivityIndicator size="small" color={theme.secondary} />
 ) : (
 <Text style={{ color: theme.secondary, fontWeight: '600' }}>Adicionar</Text>
 )}
 </TouchableOpacity>
 </View>
 </View>
 )}

 {/* Cards List */}
 {loading ? (
 <SkeletonCard />
 ) : paymentMethods.length === 0 ? (
 <View style={[styles.settingsCard, { backgroundColor: theme.surface, borderColor: theme.border, alignItems: 'center', paddingVertical: 24 }]}>
 <CreditCardIcon size={40} color={theme.textMuted} />
 <Text style={[{ color: theme.textSecondary, marginTop: 8, textAlign: 'center' }]}>
 Nenhum cartão registado
 </Text>
 <Text style={[{ color: theme.textMuted, fontSize: 12, marginTop: 4, textAlign: 'center' }]}>
 Adicione um cartão para pagamento automático na saída
 </Text>
 </View>
 ) : (
 paymentMethods.slice(0, 1).map((pm) => (
 <View key={pm.id} style={[styles.vehicleCard, { backgroundColor: theme.surface, borderColor: theme.border }]}>
 <View style={{ flexDirection: 'row', alignItems: 'center', flex: 1 }}>
 <CreditCardIcon size={24} color={theme.primary} />
 <View style={{ marginLeft: 12, flex: 1 }}>
 <Text style={[styles.vehiclePlate, { color: theme.text }]}>
 {pm.card_type?.toUpperCase()} •••• {pm.card_last_four}
 </Text>
 <Text style={[{ color: theme.textSecondary, fontSize: 12 }]}>
 {pm.card_holder_name} • Exp: {pm.expiry_month}/{pm.expiry_year}
 </Text>
 </View>
 </View>
 <TouchableOpacity
 style={[styles.deleteButton, { backgroundColor: theme.danger }]}
 onPress={() => {
 triggerHaptic('medium');
 removeCard(pm.id);
 }}
 >
 <Text style={{ color: '#fff', fontSize: 12, fontWeight: '600' }}>Remover</Text>
 </TouchableOpacity>
 </View>
 ))
 )}
 </View>

 {/* Settings */}
 <View style={styles.section}>
 <Text style={[styles.sectionTitle, { color: theme.text }]}>Definições</Text>

 {/* Dark Mode Toggle */}
 <View style={[styles.settingsCard, styles.settingsRow, { backgroundColor: theme.surface, borderColor: theme.border }]}>
 <View style={styles.settingsRowLeft}>
 <MoonIcon size={24} color={theme.textSecondary} />
 <View style={{ marginLeft: 12 }}>
 <Text style={[styles.settingsValue, { color: theme.text }]}>Modo Escuro</Text>
 <Text style={[styles.settingsLabel, { color: theme.textSecondary, marginTop: 2 }]}>
 {isDarkMode ? 'Ativado' : 'Desativado'}
 </Text>
 </View>
 </View>
 <Switch
 value={isDarkMode}
 onValueChange={(value) => {
 triggerHaptic('light');
 setIsDarkMode(value);
 }}
 trackColor={{ false: theme.border, true: theme.primary }}
 thumbColor={isDarkMode ? theme.secondary : '#f4f3f4'}
 />
 </View>

 {/* Logout Button */}
 <TouchableOpacity
 style={[styles.logoutButton, { backgroundColor: theme.danger }]}
 onPress={() => {
 triggerHaptic('medium');
 onLogout();
 }}
 >
 <Text style={[styles.logoutButtonText, { color: theme.textInverse }]}>Terminar Sessão</Text>
 </TouchableOpacity>
 </View>
 </>
 );
};

// Home Screen Component
const HomeScreen = ({ user, onLogout, theme, isDarkMode, setIsDarkMode, biometricsEnabled, setBiometricsEnabled }) => {
 const [spots, setSpots] = useState({});
 const [sessions, setSessions] = useState([]);
 const [reservations, setReservations] = useState([]);
 const [parkingRate, setParkingRate] = useState(1.50); // Default, will be fetched
 const [loading, setLoading] = useState(true);
 const [refreshing, setRefreshing] = useState(false);
 const [activeTab, setActiveTab] = useState('home');

 // User setup state (vehicles and cards)
 const [userVehicles, setUserVehicles] = useState([]);
 const [userCards, setUserCards] = useState([]);

 // Reservation modal state
 const [showReserveModal, setShowReserveModal] = useState(false);
 const [selectedSpot, setSelectedSpot] = useState(null);
 const [reserveForToday, setReserveForToday] = useState(true); // true = today, false = tomorrow
 const [selectedVehicleForReservation, setSelectedVehicleForReservation] = useState(null);

 // Confirmation modal state
 const [showConfirmModal, setShowConfirmModal] = useState(false);
 const [confirmAction, setConfirmAction] = useState(null);
 const [confirmSpot, setConfirmSpot] = useState(null);
 const [spotReservationStatus, setSpotReservationStatus] = useState({}); // { today_reserved: bool, tomorrow_reserved: bool }

 // Animation for reservation modal slide up
 const reserveModalSlideAnim = useRef(new Animated.Value(300)).current;

 // Trigger slide animation when modal visibility changes
 useEffect(() => {
 if (showReserveModal) {
 // Slide up
 Animated.timing(reserveModalSlideAnim, {
 toValue: 0,
 duration: 250,
 useNativeDriver: true,
 }).start();
 } else {
 // Reset to bottom for next open
 reserveModalSlideAnim.setValue(300);
 }
 }, [showReserveModal]);

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

 // Get alerts for reservations and payment deadlines
 const getAlerts = () => {
 const alerts = [];

 // Show reminder for today's reservations
 const todayReservations = reservations.filter(res => {
 const today = new Date().toISOString().split('T')[0];
 return res.reservation_date === today || !res.reservation_date;
 });
 if (todayReservations.length > 0) {
 alerts.push({
 type: 'warning',
 icon: 'clock',
 title: 'Reservas para hoje',
 message: `${todayReservations.length} reserva(s) ativa(s). Multa de 20€ se não usar!`,
 });
 }

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

 // Check if user has completed onboarding (has vehicles and cards)
 const hasCompletedSetup = userVehicles.length > 0 && userCards.length > 0;
 const needsVehicle = userVehicles.length === 0;
 const needsCard = userVehicles.length > 0 && userCards.length === 0;

 // Day-based reservation - no duration options needed

 const loadData = async () => {
 try {
 const [spotsRes, sessionsRes, reservationsRes, configRes, vehiclesRes, cardsRes] = await Promise.all([
 api.get('/parking'),
 api.get('/api/mobile/sessions'),
 api.get('/api/mobile/reservations'),
 api.get('/api/config'),
 api.get('/api/user/vehicles'),
 api.get('/api/user/payment-methods'),
 ]);
 console.log('[DEBUG] vehiclesRes:', JSON.stringify(vehiclesRes.data));
 console.log('[DEBUG] cardsRes:', JSON.stringify(cardsRes.data));
 setSpots(spotsRes.data);
 setSessions(sessionsRes.data.sessions || []);
 setReservations(reservationsRes.data.reservations || []);
 const vehicles = vehiclesRes.data.vehicles || [];
 const cards = cardsRes.data.payment_methods || [];
 console.log('[DEBUG] Setting userVehicles:', vehicles.length, 'userCards:', cards.length);
 setUserVehicles(vehicles);
 setUserCards(cards);
 if (configRes.data?.parking_rate_per_hour) {
 setParkingRate(configRes.data.parking_rate_per_hour);
 }
 } catch (e) {
 console.log('Load error:', e.message, e.response?.data);
 } finally {
 setLoading(false);
 }
 };

 // WebSocket connection for real-time spot updates
 const wsRef = useRef(null);
 const reconnectTimeoutRef = useRef(null);

 const connectWebSocket = () => {
 if (wsRef.current?.readyState === WebSocket.OPEN) return;

 try {
 console.log('[WS] Connecting to', WS_URL);
 wsRef.current = new WebSocket(WS_URL);

 wsRef.current.onopen = () => {
 console.log('[WS] Connected');
 showToast('success', 'Conectado', 'Atualizações em tempo real ativas');
 };

 wsRef.current.onmessage = (event) => {
 try {
 const data = JSON.parse(event.data);
 // Update spots with real-time data
 setSpots(data);
 } catch (e) {
 console.log('[WS] Parse error:', e.message);
 }
 };

 wsRef.current.onclose = () => {
 console.log('[WS] Disconnected, reconnecting in 5s...');
 // Reconnect after 5 seconds
 reconnectTimeoutRef.current = setTimeout(connectWebSocket, 5000);
 };

 wsRef.current.onerror = (error) => {
 console.log('[WS] Error:', error.message);
 };
 } catch (e) {
 console.log('[WS] Connection failed:', e.message);
 }
 };

 useEffect(() => {
 // Initial data load
 loadData();

 // Connect WebSocket for real-time spot updates
 connectWebSocket();

 // Fallback: refresh sessions/reservations every 60 seconds (spots come via WS)
 const interval = setInterval(async () => {
 try {
 const [sessionsRes, reservationsRes] = await Promise.all([
 api.get('/api/mobile/sessions'),
 api.get('/api/mobile/reservations'),
 ]);
 setSessions(sessionsRes.data.sessions || []);
 setReservations(reservationsRes.data.reservations || []);
 } catch (e) {
 console.log('Refresh error:', e.message);
 }
 }, 60000);

 return () => {
 clearInterval(interval);
 if (reconnectTimeoutRef.current) {
 clearTimeout(reconnectTimeoutRef.current);
 }
 if (wsRef.current) {
 wsRef.current.close();
 }
 };
 }, []);

 const openReserveModal = async (spotName) => {
 setSelectedSpot(spotName);
 setReserveForToday(true);

 // Auto-select primary vehicle or first vehicle if only one
 const primaryVehicle = userVehicles.find(v => v.is_primary);
 setSelectedVehicleForReservation(primaryVehicle?.plate || userVehicles[0]?.plate || null);

 // Check if this spot already has reservations for today/tomorrow (from any user)
 try {
 const res = await api.get('/api/reservations/check', {
 params: { spot: spotName }
 });
 setSpotReservationStatus(res.data || {});
 } catch (e) {
 console.log('Could not check spot reservation status:', e.message);
 setSpotReservationStatus({});
 }

 setShowReserveModal(true);
 };

 const handleReserve = async () => {
 if (!selectedSpot) return;
 if (!selectedVehicleForReservation) {
 showToast('error', 'Selecione um veículo', 'Escolha qual carro vai usar nesta reserva.');
 return;
 }
 try {
 await api.post('/api/mobile/reservations', {
 spot: selectedSpot,
 reservation_date: reserveForToday ? 'today' : 'tomorrow',
 plate: selectedVehicleForReservation
 });
 showToast('success', 'Reserva confirmada!', `Vaga ${selectedSpot} reservada para ${reserveForToday ? 'hoje' : 'amanhã'}. Multa de 20€ se não usar.`);
 setShowReserveModal(false);
 setSelectedSpot(null);
 loadData();
 } catch (e) {
 showToast('error', 'Erro na reserva', e.response?.data?.detail || 'Falha ao reservar');
 }
 };

 const handleCancelReservation = async (spotName) => {
 setConfirmSpot(spotName);
 setConfirmAction('cancel');
 setShowConfirmModal(true);
 };

 const executeCancelReservation = async () => {
 if (!confirmSpot) return;
 try {
 await api.delete(`/api/mobile/reservations/${confirmSpot}`);
 showToast('success', 'Reserva cancelada', `Vaga ${confirmSpot} está agora disponível`);
 loadData();
 } catch (e) {
 showToast('error', 'Erro', e.response?.data?.detail || 'Falha ao cancelar');
 } finally {
 setShowConfirmModal(false);
 setConfirmSpot(null);
 }
 };

 const handlePay = async (sessionId, amount) => {
 try {
 await api.post('/api/mobile/payments', {
 session_id: sessionId,
 amount: amount,
 method: 'card',
 });
 showToast('success', 'Pagamento efetuado!', 'Tem 15 minutos para sair do parque');
 loadData();
 } catch (e) {
 showToast('error', 'Erro no pagamento', e.response?.data?.detail || 'Falha ao processar pagamento');
 }
 };

 const spotsList = Object.entries(spots).map(([name, data]) => ({ name, ...data }));
 const freeSpots = spotsList.filter(s => !s.occupied && !s.reserved);
 const occupiedSpots = spotsList.filter(s => s.occupied);

 // Skeleton Loading State
 if (loading) {
 return (
 <SafeAreaView style={[styles.container, { backgroundColor: theme.background }]}>
 <StatusBar style={isDarkMode ? 'light' : 'dark'} />
 <View style={[styles.homeHeader, { backgroundColor: theme.surface }]}>
 <View>
 <SkeletonBox width={120} height={24} style={{ marginBottom: 8 }} />
 <SkeletonBox width={80} height={16} />
 </View>
 <SkeletonBox width={40} height={20} />
 </View>
 <View style={[styles.tabs, { backgroundColor: theme.surface, borderBottomColor: theme.border }]}>
 <SkeletonBox width={80} height={36} style={{ marginHorizontal: 8 }} />
 <SkeletonBox width={80} height={36} style={{ marginHorizontal: 8 }} />
 <SkeletonBox width={80} height={36} style={{ marginHorizontal: 8 }} />
 </View>
 <View style={styles.content}>
 <SkeletonBox width={150} height={24} style={{ marginBottom: 16 }} />
 <View style={[styles.statsRow, { marginBottom: 24 }]}>
 <View style={{ flex: 1, marginRight: 6 }}>
 <SkeletonBox width="100%" height={80} borderRadius={12} />
 </View>
 <View style={{ flex: 1, marginLeft: 6 }}>
 <SkeletonBox width="100%" height={80} borderRadius={12} />
 </View>
 </View>
 <SkeletonCard />
 <SkeletonCard />
 <SkeletonCard />
 </View>
 </SafeAreaView>
 );
 }

 return (
 <SafeAreaView style={[styles.container, { backgroundColor: theme.background }]}>
 <StatusBar style={isDarkMode ? 'light' : 'dark'} />

 {/* Header */}
 <View style={[styles.homeHeader, { backgroundColor: theme.surface }]}>
 <View>
 <Text style={[styles.greeting, { color: theme.text }]}>Olá, {user?.name?.split(' ')[0]}!</Text>
 </View>
 </View>

 {/* Tabs */}
 <View style={[styles.tabs, { backgroundColor: theme.surface, borderBottomColor: theme.border }]}>
 {['home', 'spots', 'settings'].map((tab) => (
 <TouchableOpacity
 key={tab}
 style={[styles.tab, activeTab === tab && { backgroundColor: theme.primary }]}
 onPress={() => {
 triggerHaptic('light');
 setActiveTab(tab);
 }}
 >
 <Text style={[styles.tabText, { color: theme.textSecondary }, activeTab === tab && { color: theme.secondary, fontWeight: '600' }]}>
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
 tintColor={theme.primary}
 colors={[theme.primary]}
 />
 }
 >
 {activeTab === 'home' && (
 <>
 {/* Onboarding - Show setup prompts if user hasn't completed setup */}
 {!hasCompletedSetup && (
 <View style={styles.section}>
 <View style={[styles.onboardingCard, { backgroundColor: theme.surface, borderColor: theme.border }]}>
 {needsVehicle ? (
 <>
 <CarIcon size={64} color={theme.textMuted} />
 <Text style={[styles.onboardingTitle, { color: theme.text }]}>
 Adicione o seu veículo
 </Text>
 <Text style={[styles.onboardingSubtitle, { color: theme.textSecondary }]}>
 Para utilizar o estacionamento, precisa de registar pelo menos um veículo.
 </Text>
 <TouchableOpacity
 style={[styles.onboardingButton, { backgroundColor: theme.primary }]}
 onPress={() => {
 triggerHaptic('medium');
 setActiveTab('settings');
 }}
 >
 <PlusIcon size={20} color={theme.secondary} />
 <Text style={[styles.onboardingButtonText, { color: theme.secondary }]}>
 Adicionar Veículo
 </Text>
 </TouchableOpacity>
 </>
 ) : needsCard ? (
 <>
 <CreditCardIcon size={64} color={theme.textMuted} />
 <Text style={[styles.onboardingTitle, { color: theme.text }]}>
 Adicione um método de pagamento
 </Text>
 <Text style={[styles.onboardingSubtitle, { color: theme.textSecondary }]}>
 Para pagar o estacionamento automaticamente, precisa de registar um cartão.
 </Text>
 <View style={[styles.onboardingVehiclePreview, { backgroundColor: theme.background, borderColor: theme.border }]}>
 <CarIcon size={20} color={theme.primary} />
 <Text style={{ color: theme.text, marginLeft: 8, fontWeight: '600' }}>
 {userVehicles[0]?.plate}
 </Text>
 <Text style={{ color: theme.success, marginLeft: 'auto', fontSize: 12 }}>Registado</Text>
 </View>
 <TouchableOpacity
 style={[styles.onboardingButton, { backgroundColor: theme.primary }]}
 onPress={() => {
 triggerHaptic('medium');
 setActiveTab('settings');
 }}
 >
 <PlusIcon size={20} color={theme.secondary} />
 <Text style={[styles.onboardingButtonText, { color: theme.secondary }]}>
 Adicionar Cartão
 </Text>
 </TouchableOpacity>
 </>
 ) : null}
 </View>
 </View>
 )}

 {/* Only show parking info if setup is complete */}
 {hasCompletedSetup && (
 <>
 {/* Alerts */}
 {alerts.length > 0 && (
 <View style={styles.alertsSection}>
 {alerts.map((alert, i) => (
 <View key={i} style={[
 styles.alertCard,
 { backgroundColor: theme.surface, borderColor: theme.border },
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
 <Text style={[styles.alertTitle, { color: theme.text }]}>{alert.title}</Text>
 <Text style={[styles.alertMessage, { color: theme.textSecondary }]}>{alert.message}</Text>
 </View>
 </View>
 ))}
 </View>
 )}

 {/* Active Session Timer */}
 {sessions.filter(s => s.status === 'open').length > 0 && (
 <View style={styles.activeSessionSection}>
 <Text style={[styles.sectionTitle, { color: theme.text }]}>Sessão Ativa</Text>
 {sessions.filter(s => s.status === 'open').slice(0, 1).map((session, i) => (
 <View key={i} style={[styles.timerCard, { backgroundColor: theme.primary }]}>
 <View style={styles.timerHeader}>
 <Text style={[styles.timerSpot, { color: theme.secondary }]}>
 {session.spot ? `Vaga ${session.spot}` : 'Estacionado'}
 </Text>
 <View style={[styles.timerBadge, { backgroundColor: theme.secondary }]}>
 <Text style={[styles.timerBadgeText, { color: theme.primary }]}>EM CURSO</Text>
 </View>
 </View>
 <View style={styles.timerDisplay}>
 <Text style={[styles.timerTime, { color: theme.secondary }]}>
 {getElapsedTime(session.entry_time)}
 </Text>
 <Text style={[styles.timerCost, { color: theme.secondary }]}>
 €{getCurrentCost(session.entry_time)}
 </Text>
 </View>
 <Text style={[styles.timerEntry, { color: theme.secondary }]}>
 Entrada: {new Date(session.entry_time).toLocaleTimeString('pt-PT')}
 </Text>
 </View>
 ))}
 </View>
 )}

 {/* Pending Sessions */}
 {sessions.filter(s => s.status === 'open').length > 0 && (
 <View style={styles.section}>
 <Text style={[styles.sectionTitle, { color: theme.text }]}>Sessões a Pagar</Text>
 {sessions.filter(s => s.status === 'open').map((session, i) => (
 <View key={i} style={[styles.card, { backgroundColor: theme.surface, borderColor: theme.border }]}>
 <Text style={[styles.cardTitle, { color: theme.text }]}>
 {session.spot ? `Vaga ${session.spot}` : 'Em curso'}
 </Text>
 <Text style={[styles.cardText, { color: theme.textSecondary }]}>€{getCurrentCost(session.entry_time)}</Text>
 <TouchableOpacity
 style={[styles.smallButton, { backgroundColor: theme.primary }]}
 onPress={() => {
 triggerHaptic('medium');
 handlePay(session.id, parseFloat(getCurrentCost(session.entry_time)));
 }}
 >
 <Text style={[styles.buttonText, { color: theme.secondary }]}>Pagar</Text>
 </TouchableOpacity>
 </View>
 ))}
 </View>
 )}

 {/* Stats */}
 <View style={styles.section}>
 <Text style={[styles.sectionTitle, { color: theme.text }]}>Estacionamentos</Text>
 <View style={styles.statsRow}>
 <View style={[styles.statCardFree, { backgroundColor: theme.surface, borderColor: theme.primary }]}>
 <Text style={[styles.statNumber, { color: theme.text }]}>{freeSpots.length}</Text>
 <Text style={[styles.statLabel, { color: theme.textSecondary }]}>Livres</Text>
 </View>
 <View style={[styles.statCardOccupied, { backgroundColor: theme.surface, borderColor: theme.danger }]}>
 <Text style={[styles.statNumber, { color: theme.text }]}>{occupiedSpots.length}</Text>
 <Text style={[styles.statLabel, { color: theme.textSecondary }]}>Ocupados</Text>
 </View>
 </View>
 </View>


 {/* Reservations */}
 {reservations.length > 0 && (
 <View style={styles.section}>
 <Text style={[styles.sectionTitle, { color: theme.text }]}>Minhas Reservas</Text>
 {reservations.map((res, i) => (
 <View key={i} style={[styles.reservationCard, { backgroundColor: theme.surface, borderColor: theme.warning }]}>
 <View>
 <Text style={[styles.cardTitle, { color: theme.text }]}>Vaga {res.spot}</Text>
 <Text style={[styles.cardText, { color: theme.textSecondary }]}>
 Para: {res.reservation_date || 'Hoje'}
 </Text>
 <Text style={[{ color: theme.warning, fontSize: 11, marginTop: 2 }]}>
 Multa de 20€ se não usar
 </Text>
 </View>
 <TouchableOpacity
 style={[styles.cancelButton, { backgroundColor: theme.danger }]}
 onPress={() => {
 triggerHaptic('medium');
 handleCancelReservation(res.spot);
 }}
 >
 <Text style={[styles.cancelButtonText, { color: theme.textInverse }]}>Cancelar</Text>
 </TouchableOpacity>
 </View>
 ))}
 </View>
 )}

 {/* Session History */}
 <View style={styles.section}>
 <Text style={[styles.sectionTitle, { color: theme.text }]}>Histórico</Text>
 {sessions.filter(s => s.status !== 'open').length === 0 ? (
 <EmptyState
 icon={HistoryIcon}
 title="Sem histórico"
 subtitle="As suas sessões anteriores aparecerão aqui"
 theme={theme}
 />
 ) : (
 sessions.filter(s => s.status !== 'open').slice(0, 5).map((session, i) => (
 <View key={i} style={[styles.card, { backgroundColor: theme.surface, borderColor: theme.border }]}>
 <View style={styles.sessionHeader}>
 <Text style={[styles.cardTitle, { color: theme.text }]}>
 {session.spot ? `Vaga ${session.spot}` : 'Sessão'}
 </Text>
 <Text style={[
 styles.sessionStatus,
 { color: session.status === 'paid' ? theme.success : theme.warning }
 ]}>
 {session.status === 'paid' ? 'Pago' : 'Terminada'}
 </Text>
 </View>
 <Text style={[styles.cardText, { color: theme.textSecondary }]}>
 {new Date(session.entry_time).toLocaleString('pt-PT')}
 </Text>
 {session.amount_paid > 0 && (
 <Text style={[styles.amount, { color: theme.primary }]}>€{session.amount_paid.toFixed(2)}</Text>
 )}
 </View>
 ))
 )}
 </View>
 </>
 )}
 </>
 )}

 {activeTab === 'spots' && (
 <View style={styles.section}>
 <Text style={[styles.sectionTitle, { color: theme.text }]}>Vagas Disponíveis</Text>
 {spotsList.length === 0 ? (
 <EmptyState
 icon={ParkingIcon}
 title="Sem vagas"
 subtitle="Nenhuma vaga disponível no momento"
 theme={theme}
 />
 ) : (
 spotsList.map((spot, i) => (
 <View key={i} style={[styles.spotCard, { backgroundColor: theme.surface, borderColor: theme.border }]}>
 <View>
 <Text style={[styles.spotName, { color: theme.text }]}>{spot.name}</Text>
 <Text style={[
 styles.spotStatus,
 { color: spot.occupied ? theme.danger : spot.reserved ? theme.warning : theme.success }
 ]}>
 {spot.occupied ? 'Ocupado' : spot.reserved ? 'Reservado' : 'Livre'}
 </Text>
 </View>
 {!spot.occupied && !spot.reserved && (
 <TouchableOpacity
 style={[styles.smallButton, { backgroundColor: theme.primary }]}
 onPress={() => {
 triggerHaptic('medium');
 openReserveModal(spot.name);
 }}
 >
 <Text style={[styles.buttonText, { color: theme.secondary }]}>Reservar</Text>
 </TouchableOpacity>
 )}
 </View>
 ))
 )}
 </View>
 )}

 {activeTab === 'settings' && (
 <SettingsTab
 user={user}
 theme={theme}
 isDarkMode={isDarkMode}
 setIsDarkMode={setIsDarkMode}
 parkingRate={parkingRate}
 onLogout={onLogout}
 onSetupChange={loadData}
 />
 )}
 </ScrollView>

 {/* Day Picker Modal - Today or Tomorrow */}
 <Modal
 visible={showReserveModal}
 transparent={true}
 animationType="none"
 onRequestClose={() => setShowReserveModal(false)}
 >
 <View style={styles.modalOverlay}>
 <Animated.View
 style={[
 styles.modalContent,
 {
 backgroundColor: theme.surface,
 transform: [{ translateY: reserveModalSlideAnim }],
 }
 ]}
 >
 <Text style={[styles.modalTitle, { color: theme.text }]}>Reservar {selectedSpot}</Text>

 {/* Vehicle Selector - scrollable list for scalability */}
 {userVehicles.length > 0 && (
 <>
 <Text style={[styles.modalSubtitle, { color: theme.textSecondary, marginBottom: 8 }]}>
 {userVehicles.length > 1 ? 'Selecione o veículo' : 'Veículo'}
 </Text>
 <View style={{
 maxHeight: userVehicles.length > 3 ? 150 : undefined,
 marginBottom: 12,
 borderRadius: 12,
 overflow: 'hidden',
 }}>
 <ScrollView
 nestedScrollEnabled={true}
 showsVerticalScrollIndicator={userVehicles.length > 3}
 >
 {userVehicles.map((vehicle, index) => {
 const isSelected = selectedVehicleForReservation === vehicle.plate;
 return (
 <TouchableOpacity
 key={vehicle.plate}
 style={[
 {
 flexDirection: 'row',
 alignItems: 'center',
 justifyContent: 'space-between',
 padding: 12,
 backgroundColor: isSelected ? theme.primary : theme.background,
 borderWidth: 1,
 borderColor: isSelected ? theme.primary : theme.border,
 borderRadius: 10,
 marginBottom: index < userVehicles.length - 1 ? 8 : 0,
 }
 ]}
 onPress={() => {
 triggerHaptic('light');
 setSelectedVehicleForReservation(vehicle.plate);
 }}
 >
 <View style={{ flexDirection: 'row', alignItems: 'center', flex: 1 }}>
 {/* Car icon */}
 <View style={{
 width: 36,
 height: 36,
 borderRadius: 18,
 backgroundColor: isSelected ? theme.secondary + '20' : theme.surface,
 alignItems: 'center',
 justifyContent: 'center',
 marginRight: 12,
 }}>
 <CarIcon size={22} color={isSelected ? theme.secondary : theme.primary} />
 </View>
 <View style={{ flex: 1 }}>
 <View style={{ flexDirection: 'row', alignItems: 'center' }}>
 <Text style={[
 {
 fontSize: 15,
 fontWeight: '600',
 color: isSelected ? theme.secondary : theme.text,
 }
 ]}>
 {vehicle.plate}
 </Text>
 {vehicle.is_primary && (
 <View style={{
 backgroundColor: isSelected ? theme.secondary : theme.primary,
 paddingHorizontal: 6,
 paddingVertical: 2,
 borderRadius: 4,
 marginLeft: 8,
 }}>
 <Text style={{
 fontSize: 9,
 fontWeight: '600',
 color: isSelected ? theme.primary : theme.secondary,
 }}>
 PRINCIPAL
 </Text>
 </View>
 )}
 </View>
 {vehicle.created_at && (
 <Text style={{
 fontSize: 11,
 color: isSelected ? theme.secondary + '80' : theme.textSecondary,
 marginTop: 2,
 }}>
 Adicionado em {new Date(vehicle.created_at).toLocaleDateString('pt-PT')}
 </Text>
 )}
 </View>
 </View>
 {/* Checkmark for selected */}
 {isSelected && (
 <View style={{
 width: 24,
 height: 24,
 borderRadius: 12,
 backgroundColor: theme.secondary,
 alignItems: 'center',
 justifyContent: 'center',
 }}>
 <Text style={{ color: theme.primary, fontWeight: 'bold', fontSize: 14 }}></Text>
 </View>
 )}
 </TouchableOpacity>
 );
 })}
 </ScrollView>
 </View>
 </>
 )}

 <Text style={[styles.modalSubtitle, { color: theme.textSecondary, marginTop: 4 }]}>Selecione o dia</Text>

 <View style={styles.durationGrid}>
 <TouchableOpacity
 style={[
 styles.durationButton,
 { borderColor: theme.border, backgroundColor: theme.background, flex: 1, marginRight: 8 },
 reserveForToday && !spotReservationStatus.today_reserved && { borderColor: theme.primary, backgroundColor: theme.primary },
 spotReservationStatus.today_reserved && { opacity: 0.4, backgroundColor: theme.error + '20' }
 ]}
 onPress={() => {
 if (spotReservationStatus.today_reserved) {
 showToast('error', 'Indisponível', 'Esta vaga já está reservada para hoje.');
 return;
 }
 triggerHaptic('light');
 setReserveForToday(true);
 }}
 disabled={spotReservationStatus.today_reserved}
 >
 <Text style={[
 styles.durationButtonText,
 { color: theme.text },
 reserveForToday && !spotReservationStatus.today_reserved && { color: theme.secondary },
 spotReservationStatus.today_reserved && { color: theme.error, textDecorationLine: 'line-through' }
 ]}>
 Hoje
 </Text>
 </TouchableOpacity>
 <TouchableOpacity
 style={[
 styles.durationButton,
 { borderColor: theme.border, backgroundColor: theme.background, flex: 1, marginLeft: 8 },
 !reserveForToday && !spotReservationStatus.tomorrow_reserved && { borderColor: theme.primary, backgroundColor: theme.primary },
 spotReservationStatus.tomorrow_reserved && { opacity: 0.4, backgroundColor: theme.error + '20' }
 ]}
 onPress={() => {
 if (spotReservationStatus.tomorrow_reserved) {
 showToast('error', 'Indisponível', 'Esta vaga já está reservada para amanhã.');
 return;
 }
 triggerHaptic('light');
 setReserveForToday(false);
 }}
 disabled={spotReservationStatus.tomorrow_reserved}
 >
 <Text style={[
 styles.durationButtonText,
 { color: theme.text },
 !reserveForToday && !spotReservationStatus.tomorrow_reserved && { color: theme.secondary },
 spotReservationStatus.tomorrow_reserved && { color: theme.error, textDecorationLine: 'line-through' }
 ]}>
 Amanhã
 </Text>
 </TouchableOpacity>
 </View>

 <Text style={[styles.modalSubtitle, { color: theme.warning, marginTop: 12, fontSize: 13 }]}>
 Multa de 20€ se não usar a reserva
 </Text>

 <View style={styles.modalButtons}>
 <TouchableOpacity
 style={[styles.modalCancelBtn, { backgroundColor: theme.background, borderColor: theme.border }]}
 onPress={() => {
 triggerHaptic('light');
 setShowReserveModal(false);
 }}
 >
 <Text style={[styles.modalCancelText, { color: theme.text }]}>Cancelar</Text>
 </TouchableOpacity>
 <TouchableOpacity
 style={[
 styles.modalConfirmBtn,
 { backgroundColor: theme.primary },
 (reserveForToday && spotReservationStatus.today_reserved) || (!reserveForToday && spotReservationStatus.tomorrow_reserved)
 ? { opacity: 0.5 } : {}
 ]}
 onPress={() => {
 if (reserveForToday && spotReservationStatus.today_reserved) {
 showToast('error', 'Indisponível', 'Esta vaga já está reservada para hoje.');
 return;
 }
 if (!reserveForToday && spotReservationStatus.tomorrow_reserved) {
 showToast('error', 'Indisponível', 'Esta vaga já está reservada para amanhã.');
 return;
 }
 triggerHaptic('medium');
 handleReserve();
 }}
 >
 <Text style={[styles.buttonText, { color: theme.secondary }]}>Reservar</Text>
 </TouchableOpacity>
 </View>
 </Animated.View>
 </View>
 </Modal>

 {/* Confirmation Modal */}
 <ConfirmModal
 visible={showConfirmModal}
 title="Cancelar Reserva"
 message={`Deseja cancelar a reserva da vaga ${confirmSpot}?`}
 confirmText="Sim, Cancelar"
 cancelText="Não"
 onConfirm={executeCancelReservation}
 onCancel={() => {
 setShowConfirmModal(false);
 setConfirmSpot(null);
 }}
 theme={theme}
 isDanger={true}
 />
 </SafeAreaView>
 );
};

// Main App
export default function App() {
 const [user, setUser] = useState(null);
 const [loading, setLoading] = useState(true);
 const [showSplash, setShowSplash] = useState(true);
 const [isDarkMode, setIsDarkMode] = useState(false);
 const [biometricsEnabled, setBiometricsEnabled] = useState(false);
 const [settingsLoaded, setSettingsLoaded] = useState(false);

 // Get current theme
 const theme = isDarkMode ? darkColors : lightColors;
 colors = theme; // Update global colors for skeleton

 useEffect(() => {
 loadSettings();
 }, []);

 // Persist dark mode setting (only after initial load)
 useEffect(() => {
 if (settingsLoaded) {
 AsyncStorage.setItem('isDarkMode', JSON.stringify(isDarkMode));
 }
 }, [isDarkMode, settingsLoaded]);

 // Persist biometrics setting (only after initial load)
 useEffect(() => {
 if (settingsLoaded) {
 AsyncStorage.setItem('biometricsEnabled', JSON.stringify(biometricsEnabled));
 }
 }, [biometricsEnabled, settingsLoaded]);

 const loadSettings = async () => {
 try {
 // Load dark mode setting
 const darkModeSetting = await AsyncStorage.getItem('isDarkMode');
 if (darkModeSetting !== null) {
 setIsDarkMode(JSON.parse(darkModeSetting));
 }

 // Load biometrics setting
 const biometricsSetting = await AsyncStorage.getItem('biometricsEnabled');
 if (biometricsSetting !== null) {
 setBiometricsEnabled(JSON.parse(biometricsSetting));
 }
 } catch (e) {
 console.log('Settings load error:', e);
 } finally {
 setSettingsLoaded(true);
 }
 };

 const checkAuth = async () => {
 try {
 const storedUser = await AsyncStorage.getItem('user');
 const token = await AsyncStorage.getItem('token');

 if (storedUser && token) {
 // Check if biometrics is enabled
 const biometricsSetting = await AsyncStorage.getItem('biometricsEnabled');
 const biometricsOn = biometricsSetting ? JSON.parse(biometricsSetting) : false;

 if (biometricsOn) {
 // Check if device supports biometrics
 const compatible = await LocalAuthentication.hasHardwareAsync();
 const enrolled = await LocalAuthentication.isEnrolledAsync();

 if (compatible && enrolled) {
 const result = await LocalAuthentication.authenticateAsync({
 promptMessage: 'Autenticar com biometria',
 cancelLabel: 'Usar senha',
 fallbackLabel: 'Usar senha',
 disableDeviceFallback: false,
 });

 if (result.success) {
 setUser(JSON.parse(storedUser));
 showToast('success', 'Bem-vindo!', 'Autenticação biométrica bem-sucedida');
 } else {
 // Biometric failed, show login screen
 showToast('info', 'Biometria cancelada', 'Por favor, faça login manualmente');
 }
 } else {
 // No biometrics available, auto-login
 setUser(JSON.parse(storedUser));
 }
 } else {
 // Biometrics disabled, auto-login
 setUser(JSON.parse(storedUser));
 }
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
 showToast('info', 'Sessão terminada', 'Até breve!');
 };

 const handleSplashFinish = () => {
 setShowSplash(false);
 checkAuth();
 };

 // Esperar settings carregarem antes de mostrar splash com tema correto
 if (!settingsLoaded) {
 return (
 <View style={[styles.container, styles.centered, { backgroundColor: '#121212' }]}>
 <ActivityIndicator color="#97d700" size="small" />
 </View>
 );
 }

 // Show splash screen with correct theme
 if (showSplash || loading) {
 return <SplashScreen onFinish={handleSplashFinish} theme={theme} />;
 }

 return (
 <>
 {user ? (
 <HomeScreen
 user={user}
 onLogout={handleLogout}
 theme={theme}
 isDarkMode={isDarkMode}
 setIsDarkMode={setIsDarkMode}
 biometricsEnabled={biometricsEnabled}
 setBiometricsEnabled={setBiometricsEnabled}
 />
 ) : (
 <LoginScreen onLogin={setUser} theme={theme} />
 )}
 <Toast />
 </>
 );
}

const styles = StyleSheet.create({
 container: {
 flex: 1,
 backgroundColor: lightColors.background,
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
 color: lightColors.text,
 },
 subtitle: {
 fontSize: 16,
 color: lightColors.textSecondary,
 marginTop: 4,
 },
 card: {
 backgroundColor: lightColors.surface,
 borderRadius: 16,
 padding: 16,
 marginBottom: 12,
 borderWidth: 1,
 borderColor: lightColors.border,
 },
 cardTitle: {
 fontSize: 18,
 fontWeight: 'bold',
 color: lightColors.text,
 marginBottom: 4,
 },
 cardText: {
 fontSize: 14,
 color: lightColors.textSecondary,
 },
 label: {
 fontSize: 14,
 color: lightColors.textSecondary,
 marginBottom: 4,
 marginTop: 12,
 },
 input: {
 backgroundColor: lightColors.background,
 borderRadius: 12,
 padding: 16,
 fontSize: 16,
 color: lightColors.text,
 borderWidth: 1,
 borderColor: lightColors.border,
 },
 error: {
 color: lightColors.danger,
 fontSize: 14,
 marginTop: 12,
 textAlign: 'center',
 },
 button: {
 backgroundColor: lightColors.primary,
 borderRadius: 12,
 padding: 16,
 alignItems: 'center',
 marginTop: 24,
 },
 buttonDisabled: {
 opacity: 0.6,
 },
 buttonText: {
 color: lightColors.secondary,
 fontSize: 16,
 fontWeight: '600',
 },
 switchButton: {
 marginTop: 16,
 alignItems: 'center',
 },
 switchText: {
 color: lightColors.secondary,
 fontSize: 14,
 },
 homeHeader: {
 flexDirection: 'row',
 justifyContent: 'space-between',
 alignItems: 'center',
 padding: 16,
 paddingTop: 30,
 backgroundColor: lightColors.surface,
 },
 greeting: {
 fontSize: 20,
 fontWeight: 'bold',
 color: lightColors.text,
 },
 plate: {
 fontSize: 14,
 color: lightColors.primary,
 marginTop: 2,
 },
 logoutText: {
 color: lightColors.danger,
 fontSize: 14,
 },
 tabs: {
 flexDirection: 'row',
 backgroundColor: lightColors.surface,
 paddingHorizontal: 8,
 paddingBottom: 8,
 borderBottomWidth: 1,
 borderBottomColor: lightColors.border,
 },
 tab: {
 flex: 1,
 paddingVertical: 10,
 alignItems: 'center',
 borderRadius: 8,
 },
 tabActive: {
 backgroundColor: lightColors.primary,
 },
 tabText: {
 fontSize: 12,
 color: lightColors.textSecondary,
 },
 tabTextActive: {
 color: lightColors.text,
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
 backgroundColor: lightColors.surface,
 borderRadius: 12,
 padding: 16,
 alignItems: 'center',
 borderColor: lightColors.primary,
 borderWidth: 1,
 },
 statCardOccupied: {
 flex: 1,
 backgroundColor: lightColors.surface,
 borderRadius: 12,
 padding: 16,
 alignItems: 'center',
 borderColor: lightColors.danger,
 borderWidth: 1,
 },
 statNumber: {
 fontSize: 32,
 fontWeight: 'bold',
 color: lightColors.text,
 },
 statLabel: {
 fontSize: 12,
 color: lightColors.textSecondary,
 marginTop: 4,
 },
 section: {
 marginBottom: 16,
 },
 sectionTitle: {
 fontSize: 18,
 fontWeight: '600',
 color: lightColors.text,
 marginBottom: 12,
 },
 spotCard: {
 backgroundColor: lightColors.surface,
 borderRadius: 12,
 padding: 16,
 marginBottom: 8,
 flexDirection: 'row',
 justifyContent: 'space-between',
 alignItems: 'center',
 borderWidth: 1,
 borderColor: lightColors.border,
 },
 spotName: {
 fontSize: 18,
 fontWeight: 'bold',
 color: lightColors.text,
 },
 spotStatus: {
 fontSize: 14,
 marginTop: 4,
 },
 smallButton: {
 backgroundColor: lightColors.primary,
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
 color: lightColors.primary,
 marginTop: 8,
 },
 emptyText: {
 color: lightColors.textSecondary,
 textAlign: 'center',
 padding: 32,
 },
 loadingText: {
 color: lightColors.textSecondary,
 marginTop: 16,
 },
 // Reservation card
 reservationCard: {
 backgroundColor: lightColors.surface,
 borderRadius: 12,
 padding: 16,
 marginBottom: 8,
 flexDirection: 'row',
 justifyContent: 'space-between',
 alignItems: 'center',
 borderWidth: 1,
 borderColor: lightColors.warning,
 },
 cancelButton: {
 backgroundColor: lightColors.danger,
 borderRadius: 8,
 paddingVertical: 8,
 paddingHorizontal: 12,
 },
 cancelButtonText: {
 color: lightColors.textInverse,
 fontSize: 12,
 fontWeight: '600',
 },
 // Settings styles
 settingsCard: {
 backgroundColor: lightColors.surface,
 borderRadius: 12,
 padding: 16,
 marginBottom: 8,
 borderWidth: 1,
 borderColor: lightColors.border,
 },
 settingsLabel: {
 fontSize: 12,
 color: lightColors.textSecondary,
 marginBottom: 4,
 },
 settingsValue: {
 fontSize: 16,
 color: lightColors.text,
 fontWeight: '500',
 },
 settingsRow: {
 flexDirection: 'row',
 justifyContent: 'space-between',
 alignItems: 'center',
 },
 settingsRowLeft: {
 flexDirection: 'row',
 alignItems: 'center',
 flex: 1,
 },
 logoutButton: {
 backgroundColor: lightColors.danger,
 borderRadius: 12,
 padding: 16,
 alignItems: 'center',
 marginTop: 24,
 },
 logoutButtonText: {
 color: lightColors.textInverse,
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
 backgroundColor: lightColors.surface,
 borderTopLeftRadius: 24,
 borderTopRightRadius: 24,
 padding: 24,
 },
 modalTitle: {
 fontSize: 20,
 fontWeight: 'bold',
 color: lightColors.text,
 textAlign: 'center',
 },
 modalSubtitle: {
 fontSize: 14,
 color: lightColors.textSecondary,
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
 borderColor: lightColors.border,
 justifyContent: 'center',
 alignItems: 'center',
 backgroundColor: lightColors.background,
 },
 durationButtonActive: {
 borderColor: lightColors.primary,
 backgroundColor: lightColors.primary,
 },
 durationButtonText: {
 fontSize: 16,
 fontWeight: '600',
 color: lightColors.text,
 },
 durationButtonTextActive: {
 color: lightColors.secondary,
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
 backgroundColor: lightColors.background,
 borderWidth: 1,
 borderColor: lightColors.border,
 },
 modalCancelText: {
 color: lightColors.text,
 fontSize: 16,
 fontWeight: '600',
 },
 modalConfirmBtn: {
 flex: 1,
 padding: 16,
 borderRadius: 12,
 alignItems: 'center',
 backgroundColor: lightColors.primary,
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
 backgroundColor: lightColors.surface,
 borderWidth: 1,
 borderColor: lightColors.border,
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
 color: lightColors.text,
 },
 alertMessage: {
 fontSize: 12,
 color: lightColors.textSecondary,
 marginTop: 2,
 },
 // Timer styles
 activeSessionSection: {
 marginBottom: 16,
 },
 timerCard: {
 backgroundColor: lightColors.primary,
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
 color: lightColors.secondary,
 },
 timerBadge: {
 backgroundColor: lightColors.secondary,
 paddingHorizontal: 10,
 paddingVertical: 4,
 borderRadius: 12,
 },
 timerBadgeText: {
 color: lightColors.primary,
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
 color: lightColors.secondary,
 },
 timerCost: {
 fontSize: 24,
 fontWeight: '600',
 color: lightColors.secondary,
 },
 timerEntry: {
 fontSize: 12,
 color: lightColors.secondary,
 marginTop: 8,
 opacity: 0.7,
 },
 // Empty State styles
 emptyStateContainer: {
 alignItems: 'center',
 justifyContent: 'center',
 paddingVertical: 48,
 paddingHorizontal: 24,
 },
 emptyStateTitle: {
 fontSize: 18,
 fontWeight: '600',
 marginTop: 16,
 textAlign: 'center',
 },
 emptyStateSubtitle: {
 fontSize: 14,
 marginTop: 8,
 textAlign: 'center',
 },
 // Splash Screen styles
 splashContainer: {
 flex: 1,
 },
 splashGradient: {
 flex: 1,
 justifyContent: 'center',
 alignItems: 'center',
 },
 splashEmoji: {
 fontSize: 80,
 marginBottom: 16,
 },
 splashTitle: {
 fontSize: 48,
 fontWeight: 'bold',
 color: '#97d700',
 },
 splashSubtitle: {
 fontSize: 16,
 color: '#a0a0a0',
 marginTop: 8,
 },
 // Confirmation Modal styles
 confirmModalOverlay: {
 flex: 1,
 backgroundColor: 'rgba(0,0,0,0.6)',
 justifyContent: 'center',
 alignItems: 'center',
 padding: 24,
 },
 confirmModalContent: {
 width: '100%',
 borderRadius: 16,
 padding: 24,
 },
 confirmModalTitle: {
 fontSize: 20,
 fontWeight: 'bold',
 textAlign: 'center',
 marginBottom: 12,
 },
 confirmModalMessage: {
 fontSize: 16,
 textAlign: 'center',
 marginBottom: 24,
 },
 confirmModalButtons: {
 flexDirection: 'row',
 gap: 12,
 },
 confirmModalBtn: {
 flex: 1,
 padding: 14,
 borderRadius: 12,
 alignItems: 'center',
 },
 confirmModalBtnText: {
 fontSize: 16,
 fontWeight: '600',
 },
 // Vehicle and Card Form styles
 vehicleCard: {
 flexDirection: 'row',
 justifyContent: 'space-between',
 alignItems: 'center',
 backgroundColor: lightColors.surface,
 borderRadius: 12,
 padding: 16,
 marginBottom: 8,
 borderWidth: 1,
 borderColor: lightColors.border,
 },
 vehiclePlate: {
 fontSize: 16,
 fontWeight: '600',
 },
 formCard: {
 backgroundColor: lightColors.surface,
 borderRadius: 12,
 padding: 16,
 marginBottom: 12,
 borderWidth: 1,
 borderColor: lightColors.border,
 },
 formInput: {
 backgroundColor: lightColors.background,
 borderRadius: 10,
 padding: 12,
 fontSize: 14,
 marginBottom: 8,
 borderWidth: 1,
 borderColor: lightColors.border,
 },
 formButton: {
 borderRadius: 10,
 padding: 12,
 alignItems: 'center',
 justifyContent: 'center',
 },
 smallAddButton: {
 flexDirection: 'row',
 alignItems: 'center',
 borderRadius: 8,
 paddingVertical: 6,
 paddingHorizontal: 12,
 },
 deleteButton: {
 borderRadius: 8,
 paddingVertical: 8,
 paddingHorizontal: 12,
 },
 cardTypeButton: {
 borderRadius: 8,
 paddingVertical: 6,
 paddingHorizontal: 12,
 marginRight: 8,
 borderWidth: 1,
 },
 // Onboarding styles
 onboardingCard: {
 alignItems: 'center',
 justifyContent: 'center',
 padding: 32,
 borderRadius: 16,
 borderWidth: 1,
 marginTop: 20,
 },
 onboardingTitle: {
 fontSize: 20,
 fontWeight: 'bold',
 marginTop: 20,
 textAlign: 'center',
 },
 onboardingSubtitle: {
 fontSize: 14,
 marginTop: 8,
 textAlign: 'center',
 paddingHorizontal: 16,
 },
 onboardingButton: {
 flexDirection: 'row',
 alignItems: 'center',
 justifyContent: 'center',
 paddingVertical: 14,
 paddingHorizontal: 24,
 borderRadius: 12,
 marginTop: 24,
 minWidth: 200,
 },
 onboardingButtonText: {
 fontSize: 16,
 fontWeight: '600',
 marginLeft: 8,
 },
 onboardingVehiclePreview: {
 flexDirection: 'row',
 alignItems: 'center',
 paddingVertical: 12,
 paddingHorizontal: 16,
 borderRadius: 10,
 borderWidth: 1,
 marginTop: 16,
 width: '100%',
 },
 smallButton: {
 paddingVertical: 6,
 paddingHorizontal: 12,
 borderRadius: 6,
 },
});
