class ApiConstants {
  // Base URL - Update this with your actual backend URL
  static const String baseUrl = 'http://localhost:8000';

  // Auth endpoints
  static const String register = '/api/auth/register/';
  static const String login = '/api/auth/login/';
  static const String verifyToken = '/api/auth/verify-token/';
  static const String userProfile = '/api/auth/profile/';
  static const String logout = '/api/auth/logout/';
}
