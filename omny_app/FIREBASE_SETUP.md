# Firebase Setup Instructions

## Prerequisites
1. Install Firebase CLI: `npm install -g firebase-tools`
2. Install FlutterFire CLI: `dart pub global activate flutterfire_cli`

## Setup Steps

### 1. Login to Firebase
```bash
firebase login
```

### 2. Configure Firebase for your Flutter app
```bash
cd omny_app
flutterfire configure
```

This will:
- Create a new Firebase project (or select existing one)
- Register your iOS and Android apps
- Download configuration files automatically
- Generate `lib/firebase_options.dart` with platform-specific config

### 3. Update main.dart to use generated options

After running `flutterfire configure`, update the Firebase initialization in `lib/main.dart`:

```dart
import 'firebase_options.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();

  // Initialize Firebase with generated options
  await Firebase.initializeApp(
    options: DefaultFirebaseOptions.currentPlatform,
  );

  runApp(const OmnyApp());
}
```

### 4. Enable Firebase Authentication

In Firebase Console (https://console.firebase.google.com):
1. Go to your project
2. Navigate to **Authentication** → **Sign-in method**
3. Enable **Email/Password** provider
4. Click **Save**

### 5. Update API Constants

Update `lib/core/constants/api_constants.dart` with your backend URL:

```dart
static const String baseUrl = 'http://your-backend-url:8000';

// For local development:
// iOS Simulator: 'http://localhost:8000'
// Android Emulator: 'http://10.0.2.2:8000'
// Physical Device: 'http://YOUR_MACHINE_IP:8000'
```

### 6. Install Dependencies
```bash
flutter pub get
```

### 7. Platform-specific setup (if needed)

#### iOS
```bash
cd ios
pod install
cd ..
```

### 8. Run the app
```bash
flutter run
```

## Platform Requirements

### Android
- Minimum SDK version: 21 (automatically set by FlutterFire)
- `google-services.json` is auto-added to `android/app/`

### iOS
- Minimum iOS version: 13.0
- `GoogleService-Info.plist` is auto-added to `ios/Runner/`
- CocoaPods will be updated automatically

## Connecting to Django Backend

Your Django backend expects Firebase ID tokens. The flow works like this:

1. **User signs up/in** → Flutter app uses Firebase Auth
2. **Get ID token** → `await FirebaseAuth.instance.currentUser?.getIdToken()`
3. **Send to Django** → POST to `/api/auth/register/` or `/api/auth/login/`
4. **Django verifies token** → Returns user data from your database

Make sure your Django backend is running and accessible from your device/emulator.

## Testing Authentication

1. Run the Django backend:
   ```bash
   cd omny_be
   python manage.py runserver 0.0.0.0:8000
   ```

2. Run the Flutter app:
   ```bash
   cd omny_app
   flutter run
   ```

3. Test the flow:
   - App opens → Sign In screen
   - Tap "Sign Up" → Fill form → Creates Firebase user + syncs with Django
   - Sign in → Verifies with Firebase + Django → Shows home screen
   - Sign out → Returns to sign in screen

