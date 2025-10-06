import 'dart:convert';
import 'package:http/http.dart' as http;
import '../models/user_model.dart';
import '../../../core/constants/api_constants.dart';

// Waitlist exception - can be removed later when waitlist is disabled
class WaitlistException implements Exception {
  final String message;
  final String email;

  WaitlistException(this.message, this.email);

  @override
  String toString() => message;
}

class AuthApiService {
  final http.Client _client;

  AuthApiService({http.Client? client}) : _client = client ?? http.Client();

  // Register user with backend
  Future<UserModel> register({
    required String idToken,
    String? displayName,
    String? phoneNumber,
    String? householdRole,
  }) async {
    try {
      final requestBody = {
        'id_token': idToken,
        if (displayName != null) 'display_name': displayName,
        if (phoneNumber != null) 'phone_number': phoneNumber,
        if (householdRole != null) 'household_role': householdRole,
      };

      print('📤 POST ${ApiConstants.baseUrl}${ApiConstants.register}');
      print('📤 Request body: $requestBody');

      final response = await _client.post(
        Uri.parse('${ApiConstants.baseUrl}${ApiConstants.register}'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode(requestBody),
      );

      print('📥 Response status: ${response.statusCode}');
      print('📥 Response body: ${response.body}');

      if (response.statusCode == 201) {
        final data = jsonDecode(response.body);
        return UserModel.fromJson(data['user']);
      } else if (response.statusCode == 403) {
        // Waitlist error
        final error = jsonDecode(response.body);
        if (error['error'] == 'waitlist_required') {
          throw WaitlistException(
            error['message'] ?? 'You are not on the waitlist',
            error['email'] ?? '',
          );
        }
        throw Exception(error['error'] ?? 'Registration failed');
      } else {
        final error = jsonDecode(response.body);
        throw Exception(error['error'] ?? 'Registration failed');
      }
    } catch (e) {
      print('❌ Registration error: $e');
      rethrow;
    }
  }

  // Login user with backend
  Future<UserModel> login(String idToken) async {
    try {
      print('📤 POST ${ApiConstants.baseUrl}${ApiConstants.login}');
      final response = await _client.post(
        Uri.parse('${ApiConstants.baseUrl}${ApiConstants.login}'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({'id_token': idToken}),
      );

      print('📥 Response status: ${response.statusCode}');
      print('📥 Response body: ${response.body}');

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        return UserModel.fromJson(data['user']);
      } else if (response.statusCode == 403) {
        // Waitlist error
        final error = jsonDecode(response.body);
        if (error['error'] == 'waitlist_required') {
          throw WaitlistException(
            error['message'] ?? 'You are not on the waitlist',
            error['email'] ?? '',
          );
        }
        throw Exception(error['error'] ?? 'Login failed');
      } else {
        final error = jsonDecode(response.body);
        throw Exception(error['error'] ?? 'Login failed');
      }
    } catch (e) {
      print('❌ Login error: $e');
      rethrow;
    }
  }

  // Verify token with backend
  Future<UserModel> verifyToken(String idToken) async {
    try {
      final response = await _client.post(
        Uri.parse('${ApiConstants.baseUrl}${ApiConstants.verifyToken}'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({'id_token': idToken}),
      );

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        return UserModel.fromJson(data['user']);
      } else {
        final error = jsonDecode(response.body);
        throw Exception(error['error'] ?? 'Token verification failed');
      }
    } catch (e) {
      throw Exception('Token verification failed: ${e.toString()}');
    }
  }

  // Get user profile
  Future<UserModel> getUserProfile(String idToken) async {
    try {
      final response = await _client.get(
        Uri.parse('${ApiConstants.baseUrl}${ApiConstants.userProfile}'),
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer $idToken',
        },
      );

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        return UserModel.fromJson(data['user']);
      } else {
        final error = jsonDecode(response.body);
        throw Exception(error['error'] ?? 'Failed to get user profile');
      }
    } catch (e) {
      throw Exception('Failed to get user profile: ${e.toString()}');
    }
  }

  // Update user profile
  Future<UserModel> updateUserProfile({
    required String idToken,
    String? displayName,
    String? phoneNumber,
    String? profilePicture,
  }) async {
    try {
      final response = await _client.patch(
        Uri.parse('${ApiConstants.baseUrl}${ApiConstants.userProfile}'),
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer $idToken',
        },
        body: jsonEncode({
          if (displayName != null) 'display_name': displayName,
          if (phoneNumber != null) 'phone_number': phoneNumber,
          if (profilePicture != null) 'profile_picture': profilePicture,
        }),
      );

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        return UserModel.fromJson(data['user']);
      } else {
        final error = jsonDecode(response.body);
        throw Exception(error['error'] ?? 'Failed to update profile');
      }
    } catch (e) {
      throw Exception('Failed to update profile: ${e.toString()}');
    }
  }

  // Logout
  Future<void> logout(String idToken) async {
    try {
      final response = await _client.post(
        Uri.parse('${ApiConstants.baseUrl}${ApiConstants.logout}'),
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer $idToken',
        },
      );

      if (response.statusCode != 200) {
        final error = jsonDecode(response.body);
        throw Exception(error['error'] ?? 'Logout failed');
      }
    } catch (e) {
      throw Exception('Logout failed: ${e.toString()}');
    }
  }
}
