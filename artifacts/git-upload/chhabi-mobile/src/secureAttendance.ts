import {PermissionsAndroid, Platform} from 'react-native';
import Geolocation from 'react-native-geolocation-service';
import {launchCamera} from 'react-native-image-picker';
import ReactNativeBiometrics from 'react-native-biometrics';

async function requestDevicePermissions() {
  if (Platform.OS !== 'android') return;
  const result = await PermissionsAndroid.requestMultiple([
    PermissionsAndroid.PERMISSIONS.ACCESS_FINE_LOCATION,
    PermissionsAndroid.PERMISSIONS.CAMERA,
  ]);
  if (result[PermissionsAndroid.PERMISSIONS.ACCESS_FINE_LOCATION] !== PermissionsAndroid.RESULTS.GRANTED ||
      result[PermissionsAndroid.PERMISSIONS.CAMERA] !== PermissionsAndroid.RESULTS.GRANTED) {
    throw new Error('Camera and precise location permissions are required.');
  }
}

function currentPosition(): Promise<any> {
  return new Promise((resolve, reject) => Geolocation.getCurrentPosition(
    resolve, reject, {enableHighAccuracy: true, timeout: 20000, maximumAge: 0},
  ));
}

export async function collectAttendanceEvidence() {
  await requestDevicePermissions();
  const biometrics = new ReactNativeBiometrics({allowDeviceCredentials: true});
  const available = await biometrics.isSensorAvailable();
  if (!available.available) throw new Error('Fingerprint/Face ID is not configured on this phone.');
  const verified = await biometrics.simplePrompt({promptMessage: 'Verify workplace attendance'});
  if (!verified.success) throw new Error('Biometric verification was cancelled.');
  const position = await currentPosition();
  const camera = await launchCamera({mediaType: 'photo', cameraType: 'front', includeBase64: true, quality: 0.7});
  if (camera.didCancel || !camera.assets?.[0]?.base64) throw new Error('A live front-camera selfie is required.');
  return {
    biometric_verified: true,
    latitude: position.coords.latitude,
    longitude: position.coords.longitude,
    accuracy: position.coords.accuracy,
    selfie: `data:${camera.assets[0].type || 'image/jpeg'};base64,${camera.assets[0].base64}`,
  };
}
