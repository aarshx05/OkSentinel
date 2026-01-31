import 'package:flutter/foundation.dart';
import '../services/api_service.dart';
import '../models/models.dart';

class AuthProvider with ChangeNotifier {
  final ApiService _apiService = ApiService();
  
  bool _isLoggedIn = false;
  String? _username;
  String? _userId;
  String? _errorMessage;
  bool _isLoading = false;

  bool get isLoggedIn => _isLoggedIn;
  String? get username => _username;
  String? get userId => _userId;
  String? get errorMessage => _errorMessage;
  bool get isLoading => _isLoading;

  AuthProvider() {
    _checkLoginStatus();
  }

  Future<void> _checkLoginStatus() async {
    await _apiService.loadSettings();
    _isLoggedIn = _apiService.isLoggedIn;
    notifyListeners();
  }

  Future<bool> login(String username, String pin) async {
    _isLoading = true;
    _errorMessage = null;
    notifyListeners();

    final response = await _apiService.login(username, pin);

    _isLoading = false;

    if (response.success && response.data != null) {
      _isLoggedIn = true;
      _username = response.data!['username'];
      _userId = response.data!['user_id'];
      _errorMessage = null;
      notifyListeners();
      return true;
    } else {
      _errorMessage = response.error ?? 'Login failed';
      notifyListeners();
      return false;
    }
  }

  Future<void> logout() async {
    await _apiService.logout();
    _isLoggedIn = false;
    _username = null;
    _userId = null;
    _errorMessage = null;
    notifyListeners();
  }

  void clearError() {
    _errorMessage = null;
    notifyListeners();
  }
}
