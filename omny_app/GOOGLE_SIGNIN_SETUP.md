# Google Sign-In Setup Instructions

## Firebase Console Setup

### 1. Enable Google Sign-In Provider

1. Go to [Firebase Console](https://console.firebase.google.com)
2. Select your project
3. Navigate to **Authentication** → **Sign-in method**
4. Click on **Google** provider
5. Toggle **Enable**
6. Add a **Project support email**
7. Click **Save**

### 2. Get Web Client ID (For Web/Chrome)

1. In Firebase Console, go to **Project Settings** (⚙️ icon)
2. Scroll to **Your apps** section
3. Find your **Web app** (or create one if it doesn't exist)
4. Copy the **Web client ID** (looks like: `xxxxx.apps.googleusercontent.com`)

### 3. Update Firebase Auth Service

Update `lib/features/auth/services/firebase_auth_service.dart`:

```dart
late final GoogleSignIn _googleSignIn = GoogleSignIn(
  clientId: kIsWeb ? 'YOUR_WEB_CLIENT_ID.apps.googleusercontent.com' : null,
);
```

Replace `YOUR_WEB_CLIENT_ID.apps.googleusercontent.com` with the actual Web Client ID from step 2.

## Platform-Specific Setup

### Android

No additional setup needed! Google Sign-In works automatically after:
1. Running `flutterfire configure`
2. Adding SHA-1 fingerprint to Firebase Console (already done)

### iOS

1. Open `ios/Runner/Info.plist`
2. Add your **Reversed Client ID** (from Firebase Console):

```xml
<key>CFBundleURLTypes</key>
<array>
  <dict>
    <key>CFBundleTypeRole</key>
    <string>Editor</string>
    <key>CFBundleURLSchemes</key>
    <array>
      <!-- Replace with your REVERSED_CLIENT_ID from GoogleService-Info.plist -->
      <string>com.googleusercontent.apps.YOUR-REVERSED-CLIENT-ID</string>
    </array>
  </dict>
</array>
```

**To find the Reversed Client ID:**
- Open `ios/Runner/GoogleService-Info.plist`
- Look for `REVERSED_CLIENT_ID` key
- Copy the value (looks like: `com.googleusercontent.apps.xxxxx`)

### Web

The Web Client ID is already configured in the Firebase Auth Service (step 3 above).

## Testing

1. **Install dependencies:**
   ```bash
   flutter pub get
   ```

2. **Run the app:**
   ```bash
   flutter run
   ```

3. **Test Google Sign-In:**
   - Click "Continue with Google" button
   - Select your Google account
   - App will authenticate with Firebase
   - Backend will automatically register/login the user

## Troubleshooting

### "ClientID not set" error (Web)
- Make sure you've added the Web Client ID in `firebase_auth_service.dart`
- Verify the client ID is correct (from Firebase Console)

### "DEVELOPER_ERROR" (Android)
- Ensure SHA-1 fingerprint is added to Firebase Console
- Run `cd android && ./gradlew signingReport` to get SHA-1
- Add the SHA-1 in Firebase Console → Project Settings → Your apps → Android app

### iOS build errors
- Make sure `REVERSED_CLIENT_ID` is added to `Info.plist`
- Run `cd ios && pod install`

### "Google Sign-In cancelled"
- This is normal when user closes the Google Sign-In popup
- Not an error, just means user cancelled the flow

## Backend Integration

The Django backend automatically handles Google Sign-In:

1. **First-time Google Sign-In:**
   - User signs in with Google
   - Firebase creates user
   - Flutter app gets ID token
   - Backend creates new user record (via `/api/auth/register/`)

2. **Existing Google User:**
   - User signs in with Google
   - Firebase authenticates
   - Flutter app gets ID token
   - Backend logs in user (via `/api/auth/login/`)

No additional backend changes needed!
