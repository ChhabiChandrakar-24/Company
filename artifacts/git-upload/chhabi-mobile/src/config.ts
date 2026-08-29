import {Platform} from 'react-native';

// Android emulator reaches the Windows host through 10.0.2.2.
// Replace this with your HTTPS production domain before release builds.
export const API_BASE_URL = Platform.select({
  android: 'http://10.0.2.2:8000/api',
  ios: 'http://localhost:8000/api',
  default: 'http://localhost:8000/api',
}) as string;

export const WEB_BASE_URL = API_BASE_URL.replace(/\/api\/?$/, '');
