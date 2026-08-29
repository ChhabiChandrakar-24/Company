# Geeta Forgetech Mobile

Pure React Native CLI application (no Expo) for the Chhabi HR platform.
The application uses native React Native screens only; it does not embed the
web application or depend on WebView.

## Included modules

- JWT login, refresh and persistent session
- Role/permission based module visibility
- Dashboard and company profile
- Employee directory
- Clock-in, clock-out and attendance history
- Leave list and leave request creation
- Payroll/payslips
- Recruitment
- Assets
- Meetings, chat/captions/recordings API compatibility and meeting creation
- Reports, policies, documents and notifications
- Android/iOS camera, microphone and location permissions
- 60+ permission-aware native CRUD screens covering organization settings,
  onboarding, offboarding, help desk, projects and the full HR module catalog

## Development installation

Requirements: Node 22+, JDK 17, Android Studio SDK, and on macOS Xcode + CocoaPods.

```powershell
cd mobile
npm install
npm run typecheck
npm start
```

In another terminal:

```powershell
npm run android
```

The current Android development URL is `http://127.0.0.1:8000/api`. For a USB
device run `adb reverse tcp:8000 tcp:8000` and `adb reverse tcp:8081 tcp:8081`.
For Wi-Fi testing, replace it with the computer LAN address and start Django on
`0.0.0.0:8000`; both devices must share a network. For an Android emulator use
`http://10.0.2.2:8000/api`.

For iOS on macOS:

```bash
cd ios && pod install && cd ..
npm run ios
```

## Production backend

1. Host Django behind HTTPS (Nginx/IIS/Apache) with a real domain.
2. Set `DEBUG=False`, a strong `SECRET_KEY`, production `ALLOWED_HOSTS` and
   `CSRF_TRUSTED_ORIGINS` in the backend environment.
3. Change `API_BASE_URL` in `src/config.ts` to `https://your-domain/api`.
4. Re-run typecheck and release builds.

## Android deployment

Create a private upload key (never commit it):

```powershell
keytool -genkeypair -v -storetype PKCS12 -keystore geeta-upload-key.keystore -alias geeta-upload -keyalg RSA -keysize 2048 -validity 10000
```

Place the keystore outside source control, configure its path/password through
Gradle environment variables in `android/app/build.gradle`, then build:

```powershell
npm run build:android:release
```

Upload `android/app/build/outputs/bundle/release/app-release.aab` to Google Play
Console. Complete Data Safety declarations for camera, microphone, location,
employee records and recordings.

## iOS deployment

On macOS, open `ios/ChhabiMobile.xcworkspace`, set the Apple team and unique
bundle identifier, configure signing, select **Product > Archive**, then upload
through Xcode Organizer to App Store Connect. Complete privacy declarations for
camera, microphone, location, documents and employee data.

## Security checklist

- Only HTTPS is allowed in production.
- JWT is refreshed automatically; logout removes local tokens.
- Permissions still execute on the Django server; hiding a mobile menu is not
  treated as authorization.
- Keep signing keys, API secrets and provider credentials outside Git.
- Configure TURN for reliable external WebRTC calls and encrypted object storage
  for production meeting recordings.
