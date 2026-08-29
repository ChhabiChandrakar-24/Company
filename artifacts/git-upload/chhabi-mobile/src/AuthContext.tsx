import AsyncStorage from '@react-native-async-storage/async-storage';
import React, {createContext, useContext, useEffect, useState} from 'react';
import {api, STORAGE_KEYS} from './api';
import {Session} from './types';

type AuthValue = {
  session: Session | null;
  loading: boolean;
  signIn: (username: string, password: string) => Promise<void>;
  signOut: () => Promise<void>;
  reloadProfile: () => Promise<void>;
};

const AuthContext = createContext<AuthValue>({} as AuthValue);

export function AuthProvider({children}: React.PropsWithChildren) {
  const [session, setSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    AsyncStorage.getItem(STORAGE_KEYS.session)
      .then(value => value && setSession(JSON.parse(value)))
      .finally(() => setLoading(false));
  }, []);

  const persist = async (next: Session | null) => {
    setSession(next);
    if (next) {
      await Promise.all([
        AsyncStorage.setItem(STORAGE_KEYS.access, next.access),
        AsyncStorage.setItem(STORAGE_KEYS.refresh, next.refresh),
        AsyncStorage.setItem(STORAGE_KEYS.session, JSON.stringify(next)),
      ]);
    } else {
      await Promise.all(Object.values(STORAGE_KEYS).map(key => AsyncStorage.removeItem(key)));
    }
  };

  const signIn = async (username: string, password: string) => {
    const {data} = await api.post('/auth/login/', {username, password});
    await Promise.all([
      AsyncStorage.setItem(STORAGE_KEYS.access, data.access),
      AsyncStorage.setItem(STORAGE_KEYS.refresh, data.refresh),
    ]);
    const bootstrap = await api.get('/mobile/bootstrap/');
    await persist({
      access: data.access,
      refresh: data.refresh,
      profile: bootstrap.data.profile,
      permissions: bootstrap.data.permissions,
      modules: bootstrap.data.modules,
    });
  };

  const signOut = () => persist(null);
  const reloadProfile = async () => {
    if (!session) return;
    const {data} = await api.get('/mobile/bootstrap/');
    await persist({...session, ...data});
  };

  const value = {session, loading, signIn, signOut, reloadProfile};
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export const useAuth = () => useContext(AuthContext);
