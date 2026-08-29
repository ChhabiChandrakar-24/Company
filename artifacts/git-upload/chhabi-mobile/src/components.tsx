import React from 'react';
import {
  ActivityIndicator,
  Image,
  Pressable,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import {colors, shadow} from './theme';

const emoji: Record<string, string> = {
  home: '🏠', people: '👥', person: '👤', calendar: '📅', videocam: '📹',
  grid: '▦', fingerprint: '☝️', notifications: '🔔', document: '📄',
  wallet: '💳', recruitment: '🧑‍💼', asset: '📦', report: '📊',
  policy: '🛡️', business: '🏢', mail: '✉️', phone: '📞', id: '🪪',
  add: '＋', forward: '›', check: '✅', leave: '🏖️', warning: '⚠️',
  lock: '🔒', eye: '👁️', tray: '📭', settings: '⚙️', task: '☑️', help: '🎫',
};

export function AppIcon({name, size = 22}: {name: string; size?: number; color?: string}) {
  const key = Object.keys(emoji).find(item => name.toLowerCase().includes(item));
  return <Text style={{fontSize: size, lineHeight: size * 1.25}}>{emoji[key || 'grid']}</Text>;
}

export function LoadingScreen() {
  return <View style={styles.center}><ActivityIndicator size="large" color={colors.cyan} /></View>;
}

export function EmptyState({title = 'No records found'}: {title?: string}) {
  return <View style={styles.empty}><AppIcon name="tray" size={42} /><Text style={styles.emptyText}>{title}</Text></View>;
}

export function Avatar({uri, name, size = 48}: {uri?: string | null; name: string; size?: number}) {
  if (uri) return <Image source={{uri}} style={{width: size, height: size, borderRadius: size / 2}} />;
  return <View style={[styles.avatar, {width: size, height: size, borderRadius: size / 2}]}><Text style={[styles.avatarText, {fontSize: size * .35}]}>{name?.slice(0, 1).toUpperCase()}</Text></View>;
}

export function PrimaryButton({title, onPress, loading, danger}: {title: string; onPress: () => void; loading?: boolean; danger?: boolean}) {
  return <Pressable disabled={loading} onPress={onPress} style={({pressed}) => [styles.button, danger && {backgroundColor: colors.danger}, pressed && {opacity: .8}]}>{loading ? <ActivityIndicator color="white" /> : <Text style={styles.buttonText}>{title}</Text>}</Pressable>;
}

export function StatCard({label, value, icon, color = colors.blue}: {label: string; value: string | number; icon: string; color?: string}) {
  return <View style={styles.stat}><View style={[styles.iconBox, {backgroundColor: `${color}18`}]}><AppIcon name={icon} size={22} /></View><Text style={styles.statValue}>{value}</Text><Text style={styles.statLabel}>{label}</Text></View>;
}

const styles = StyleSheet.create({
  center: {flex: 1, alignItems: 'center', justifyContent: 'center', backgroundColor: colors.background},
  empty: {alignItems: 'center', padding: 40}, emptyText: {color: colors.muted, marginTop: 10},
  avatar: {backgroundColor: colors.blue, alignItems: 'center', justifyContent: 'center'}, avatarText: {color: 'white', fontWeight: '800'},
  button: {height: 50, borderRadius: 14, backgroundColor: colors.blue, alignItems: 'center', justifyContent: 'center', paddingHorizontal: 20},
  buttonText: {color: 'white', fontWeight: '800', fontSize: 15},
  stat: {width: '48%', padding: 16, borderRadius: 18, backgroundColor: colors.card, marginBottom: 12, ...shadow},
  iconBox: {width: 42, height: 42, borderRadius: 12, alignItems: 'center', justifyContent: 'center'},
  statValue: {fontSize: 25, fontWeight: '900', color: colors.navy, marginTop: 12}, statLabel: {fontSize: 12, color: colors.muted, marginTop: 3},
});
