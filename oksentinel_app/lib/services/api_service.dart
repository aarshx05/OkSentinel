import 'dart:convert';
import 'dart:io';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';
import '../models/models.dart';

class ApiService {
  // Default local WiFi settings
  String _baseUrl = 'http://192.168.1.100:5000/api';
  String? _sessionToken;

  // Singleton pattern
  static final ApiService _instance = ApiService._internal();
  factory ApiService() => _instance;
  ApiService._internal();

  /// Get current base URL
  String get baseUrl => _baseUrl;

  /// Set base URL (for settings)
  Future<void> setBaseUrl(String url) async {
    _baseUrl = url.replaceAll(RegExp(r'/+$'), ''); // Remove trailing slashes
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('api_base_url', _baseUrl);
  }

  /// Load saved settings
  Future<void> loadSettings() async {
    final prefs = await SharedPreferences.getInstance();
    _baseUrl = prefs.getString('api_base_url') ?? _baseUrl;
    _sessionToken = prefs.getString('session_token');
  }

  /// Save session token
  Future<void> _saveToken(String token) async {
    _sessionToken = token;
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('session_token', token);
  }

  /// Clear session
  Future<void> clearSession() async {
    _sessionToken = null;
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove('session_token');
  }

  /// Check if user is logged in
  bool get isLoggedIn => _sessionToken != null;

  /// Get headers with auth token
  Map<String, String> get _headers {
    final headers = {
      'Content-Type': 'application/json',
    };
    if (_sessionToken != null) {
      headers['X-Session-Token'] = _sessionToken!;
    }
    return headers;
  }

  /// Health check
  Future<bool> healthCheck() async {
    try {
      final response = await http
          .get(Uri.parse('$_baseUrl/health'))
          .timeout(const Duration(seconds: 5));
      return response.statusCode == 200;
    } catch (e) {
      return false;
    }
  }

  /// Login or register
  Future<ApiResponse<Map<String, dynamic>>> login(
    String username,
    String pin,
  ) async {
    try {
      final response = await http.post(
        Uri.parse('$_baseUrl/auth/login'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({'username': username, 'pin': pin}),
      );

      final data = jsonDecode(response.body);

      if (response.statusCode == 200 || response.statusCode == 201) {
        // Save token
        await _saveToken(data['token']);
        return ApiResponse(success: true, data: data);
      } else {
        return ApiResponse(
          success: false,
          error: data['error'] ?? 'Login failed',
          code: data['code'],
        );
      }
    } catch (e) {
      return ApiResponse(
        success: false,
        error: 'Network error: ${e.toString()}',
        code: 'NETWORK_ERROR',
      );
    }
  }

  /// Logout
  Future<void> logout() async {
    try {
      await http.post(
        Uri.parse('$_baseUrl/auth/logout'),
        headers: _headers,
      );
    } catch (e) {
      // Ignore errors, just clear local session
    }
    await clearSession();
  }

  /// Get dashboard data
  Future<ApiResponse<DashboardData>> getDashboard() async {
    try {
      final response = await http.get(
        Uri.parse('$_baseUrl/dashboard'),
        headers: _headers,
      );

      final data = jsonDecode(response.body);

      if (response.statusCode == 200) {
        return ApiResponse(
          success: true,
          data: DashboardData.fromJson(data),
        );
      } else {
        return ApiResponse(
          success: false,
          error: data['error'] ?? 'Failed to load dashboard',
          code: data['code'],
        );
      }
    } catch (e) {
      return ApiResponse(
        success: false,
        error: 'Network error: ${e.toString()}',
        code: 'NETWORK_ERROR',
      );
    }
  }

  /// Get users list
  Future<ApiResponse<List<User>>> getUsers() async {
    try {
      final response = await http.get(
        Uri.parse('$_baseUrl/users'),
        headers: _headers,
      );

      final data = jsonDecode(response.body);

      if (response.statusCode == 200) {
        final users = (data['users'] as List)
            .map((u) => User.fromJson(u))
            .toList();
        return ApiResponse(success: true, data: users);
      } else {
        return ApiResponse(
          success: false,
          error: data['error'] ?? 'Failed to load users',
          code: data['code'],
        );
      }
    } catch (e) {
      return ApiResponse(
        success: false,
        error: 'Network error: ${e.toString()}',
        code: 'NETWORK_ERROR',
      );
    }
  }

  /// Send file
  Future<ApiResponse<Map<String, dynamic>>> sendFile(
    File file,
    String recipientId,
    double expiryHours,
    Function(double)? onProgress,
  ) async {
    try {
      final uri = Uri.parse('$_baseUrl/send');
      final request = http.MultipartRequest('POST', uri);

      // Add headers
      if (_sessionToken != null) {
        request.headers['X-Session-Token'] = _sessionToken!;
      }

      // Add file
      final fileStream = http.ByteStream(file.openRead());
      final fileLength = await file.length();

      request.files.add(http.MultipartFile(
        'file',
        fileStream,
        fileLength,
        filename: file.path.split(Platform.pathSeparator).last,
      ));

      // Add fields
      request.fields['recipient_id'] = recipientId;
      request.fields['expiry_hours'] = expiryHours.toString();

      // Send with progress tracking
      final streamedResponse = await request.send();
      final response = await http.Response.fromStream(streamedResponse);

      final data = jsonDecode(response.body);

      if (response.statusCode == 201) {
        return ApiResponse(success: true, data: data);
      } else {
        return ApiResponse(
          success: false,
          error: data['error'] ?? 'Failed to send file',
          code: data['code'],
        );
      }
    } catch (e) {
      return ApiResponse(
        success: false,
        error: 'Network error: ${e.toString()}',
        code: 'NETWORK_ERROR',
      );
    }
  }

  /// Get file info
  Future<ApiResponse<FileInfo>> getFileInfo(String fileId) async {
    try {
      final response = await http.get(
        Uri.parse('$_baseUrl/file/$fileId/info'),
        headers: _headers,
      );

      final data = jsonDecode(response.body);

      if (response.statusCode == 200) {
        return ApiResponse(
          success: true,
          data: FileInfo.fromJson(data),
        );
      } else {
        return ApiResponse(
          success: false,
          error: data['error'] ?? 'Failed to load file info',
          code: data['code'],
        );
      }
    } catch (e) {
      return ApiResponse(
        success: false,
        error: 'Network error: ${e.toString()}',
        code: 'NETWORK_ERROR',
      );
    }
  }

  /// Get stream URL for file
  String getStreamUrl(String fileId) {
    return '$_baseUrl/stream/$fileId';
  }

  /// Get headers for streaming requests
  Map<String, String> get streamHeaders {
    return {
      if (_sessionToken != null) 'X-Session-Token': _sessionToken!,
    };
  }
}
