import AsyncStorage from '@react-native-async-storage/async-storage';
import axios from 'axios';
import {API_BASE_URL} from './config';

export const STORAGE_KEYS = {
  access: 'chhabi.access',
  refresh: 'chhabi.refresh',
  session: 'chhabi.session',
};

export const api = axios.create({baseURL: API_BASE_URL, timeout: 25000});

api.interceptors.request.use(async config => {
  const token = await AsyncStorage.getItem(STORAGE_KEYS.access);
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

let refreshPromise: Promise<string> | null = null;

api.interceptors.response.use(
  response => response,
  async error => {
    const original = error.config;
    if (error.response?.status !== 401 || original?._retry) throw error;
    original._retry = true;
    refreshPromise ??= (async () => {
      const refresh = await AsyncStorage.getItem(STORAGE_KEYS.refresh);
      if (!refresh) throw error;
      const response = await axios.post(`${API_BASE_URL}/auth/refresh/`, {refresh});
      await AsyncStorage.setItem(STORAGE_KEYS.access, response.data.access);
      return response.data.access as string;
    })().finally(() => (refreshPromise = null));
    const access = await refreshPromise;
    original.headers.Authorization = `Bearer ${access}`;
    return api(original);
  },
);

export function rowsOf(data: any): any[] {
  if (Array.isArray(data)) return data;
  if (Array.isArray(data?.results)) return data.results;
  if (Array.isArray(data?.data)) return data.data;
  return data && typeof data === 'object' ? [data] : [];
}

export function errorMessage(error: any): string {
  const data = error?.response?.data;
  if (typeof data === 'string') return data;
  if (data?.detail) return data.detail;
  if (data?.error) return data.error;
  if (data && typeof data === 'object') {
    const first = Object.values(data)[0];
    if (Array.isArray(first)) return String(first[0]);
    if (first) return String(first);
  }
  return error?.message || 'Something went wrong. Please try again.';
}
