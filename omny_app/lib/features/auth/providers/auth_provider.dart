import 'package:flutter/foundation.dart';
import '../models/user_model.dart';
import '../services/firebase_auth_service.dart';
import '../services/auth_api_service.dart';

// Export WaitlistException for use in UI
export '../services/auth_api_service.dart' show WaitlistException;

class AuthProvider with ChangeNotifier {
  final FirebaseAuthService _firebaseAuthService;
  final AuthApiService _authApiService;

  UserModel? _user;
  bool _isLoading = false;
  String? _errorMessage;
  bool _isWaitlisted = false;
  String? _waitlistedEmail;

  AuthProvider({
    FirebaseAuthService? firebaseAuthService,
    AuthApiService? authApiService,
  })  : _firebaseAuthService = firebaseAuthService ?? FirebaseAuthService(),
        _authApiService = authApiService ?? AuthApiService() {
    _initializeAuth();
  }

  // Getters
  UserModel? get user => _user;
  bool get isLoading => _isLoading;
  String? get errorMessage => _errorMessage;
  bool get isAuthenticated => _user != null;
  bool get isWaitlisted => _isWaitlisted;
  String? get waitlistedEmail => _waitlistedEmail;

  // Initialize auth state
  void _initializeAuth() {
    _firebaseAuthService.authStateChanges.listen((firebaseUser) async {
      if (firebaseUser != null) {
        // User is signed in, sync with backend
        try {
          final idToken = await _firebaseAuthService.getIdToken();
          if (idToken != null) {
            _user = await _authApiService.verifyToken(idToken);
            notifyListeners();
          }
        } catch (e) {
          debugPrint('Error syncing user: $e');
        }
      } else {
        // User is signed out
        _user = null;
        notifyListeners();
      }
    });
  }

  // Sign in with email and password
  Future<bool> signIn(String email, String password) async {
    try {
      _setLoading(true);
      _clearError();

      // Sign in with Firebase
      final idToken = await _firebaseAuthService.signInWithEmail(email, password);

      // Sync with backend
      _user = await _authApiService.login(idToken);

      _setLoading(false);
      return true;
    } catch (e) {
      _setError(e.toString());
      _setLoading(false);
      return false;
    }
  }

  // Sign up with email and password
  Future<bool> signUp({
    required String email,
    required String password,
    required String displayName,
    required String phoneNumber,
    String householdRole = 'caregiver',
  }) async {
    try {
      _setLoading(true);
      _clearError();

      // Create Firebase user
      final idToken = await _firebaseAuthService.signUpWithEmail(email, password);

      // Update display name in Firebase
      await _firebaseAuthService.updateDisplayName(displayName);

      // Register with backend
      _user = await _authApiService.register(
        idToken: idToken,
        displayName: displayName,
        phoneNumber: phoneNumber,
        householdRole: householdRole,
      );

      _setLoading(false);
      return true;
    } catch (e) {
      _setError(e.toString());
      _setLoading(false);

      // Clean up Firebase user if backend registration fails
      try {
        await _firebaseAuthService.signOut();
      } catch (signOutError) {
        debugPrint('Error cleaning up Firebase user: $signOutError');
      }

      return false;
    }
  }

  // Sign in with Google
  Future<bool> signInWithGoogle() async {
    try {
      _setLoading(true);
      _clearError();

      // Sign in with Google via Firebase
      debugPrint('🔵 Starting Google Sign-In...');
      final idToken = await _firebaseAuthService.signInWithGoogle();
      debugPrint('✅ Got Firebase ID token');

      // Try to login with backend (user might already exist)
      try {
        debugPrint('🔵 Attempting login with backend...');
        _user = await _authApiService.login(idToken);
        debugPrint('✅ Login successful: ${_user?.email}');
      } catch (loginError) {
        // If it's a waitlist error, re-throw it to be caught by outer catch
        if (loginError is WaitlistException) {
          debugPrint('⚠️ User is waitlisted: ${loginError.email}');
          rethrow;
        }

        debugPrint('⚠️ Login failed, attempting registration: $loginError');
        // If user doesn't exist in backend, register them
        // Get user info from Firebase
        final firebaseUser = _firebaseAuthService.currentUser;
        debugPrint('🔵 Registering new user: ${firebaseUser?.email}');
        _user = await _authApiService.register(
          idToken: idToken,
          displayName: firebaseUser?.displayName ?? '',
          phoneNumber: firebaseUser?.phoneNumber ?? '',
          householdRole: 'caregiver',
        );
        debugPrint('✅ Registration successful: ${_user?.email}');
      }

      _setLoading(false);
      notifyListeners();
      return true;
    } catch (e) {
      debugPrint('❌ Google Sign-In failed: $e');

      // Check if it's a waitlist error
      if (e is WaitlistException) {
        _isWaitlisted = true;
        _waitlistedEmail = e.email;
        _setError(e.message);

        // Sign out from Firebase since user is waitlisted
        try {
          await _firebaseAuthService.signOut();
        } catch (signOutError) {
          debugPrint('Error signing out from Firebase: $signOutError');
        }
      } else {
        _setError(e.toString());
      }

      _setLoading(false);
      return false;
    }
  }

  // Sign out
  Future<void> signOut() async {
    try {
      _setLoading(true);
      _clearError();

      // Get ID token before signing out
      final idToken = await _firebaseAuthService.getIdToken();

      // Logout from backend
      if (idToken != null) {
        await _authApiService.logout(idToken);
      }

      // Sign out from Firebase
      await _firebaseAuthService.signOut();

      _user = null;
      _setLoading(false);
    } catch (e) {
      _setError(e.toString());
      _setLoading(false);
      // Still sign out from Firebase even if backend logout fails
      await _firebaseAuthService.signOut();
      _user = null;
    }
  }

  // Send password reset email
  Future<bool> sendPasswordResetEmail(String email) async {
    try {
      _setLoading(true);
      _clearError();

      await _firebaseAuthService.sendPasswordResetEmail(email);

      _setLoading(false);
      return true;
    } catch (e) {
      _setError(e.toString());
      _setLoading(false);
      return false;
    }
  }

  // Refresh user data
  Future<void> refreshUser() async {
    try {
      final idToken = await _firebaseAuthService.getIdToken(forceRefresh: true);
      if (idToken != null) {
        _user = await _authApiService.getUserProfile(idToken);
        notifyListeners();
      }
    } catch (e) {
      debugPrint('Error refreshing user: $e');
    }
  }

  // Update user profile
  Future<bool> updateProfile({
    String? displayName,
    String? phoneNumber,
    String? profilePicture,
  }) async {
    try {
      _setLoading(true);
      _clearError();

      final idToken = await _firebaseAuthService.getIdToken();
      if (idToken == null) {
        throw Exception('Not authenticated');
      }

      // Update display name in Firebase if provided
      if (displayName != null) {
        await _firebaseAuthService.updateDisplayName(displayName);
      }

      // Update profile in backend
      _user = await _authApiService.updateUserProfile(
        idToken: idToken,
        displayName: displayName,
        phoneNumber: phoneNumber,
        profilePicture: profilePicture,
      );

      _setLoading(false);
      return true;
    } catch (e) {
      _setError(e.toString());
      _setLoading(false);
      return false;
    }
  }

  // Helper methods
  void _setLoading(bool value) {
    _isLoading = value;
    notifyListeners();
  }

  void _setError(String message) {
    _errorMessage = message;
    notifyListeners();
  }

  void _clearError() {
    _errorMessage = null;
    _isWaitlisted = false;
    _waitlistedEmail = null;
    notifyListeners();
  }

  void clearError() {
    _clearError();
  }
}
