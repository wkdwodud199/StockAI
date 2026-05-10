import 'package:flutter_secure_storage/flutter_secure_storage.dart';

/// 백엔드 URL, API 토큰, 실전 PIN 등 민감 설정을 안전하게 저장.
class SecureSettings {
  static const _storage = FlutterSecureStorage(
    aOptions: AndroidOptions(encryptedSharedPreferences: true),
  );

  static const _kBaseUrl = 'baseUrl';
  static const _kApiToken = 'apiToken';
  static const _kRealPin = 'realPin';

  Future<String?> get baseUrl => _storage.read(key: _kBaseUrl);
  Future<void> setBaseUrl(String v) => _storage.write(key: _kBaseUrl, value: v);

  Future<String?> get apiToken => _storage.read(key: _kApiToken);
  Future<void> setApiToken(String v) => _storage.write(key: _kApiToken, value: v);

  Future<String?> get realPin => _storage.read(key: _kRealPin);
  Future<void> setRealPin(String v) => _storage.write(key: _kRealPin, value: v);

  Future<bool> get isConfigured async {
    final b = await baseUrl;
    final t = await apiToken;
    return b != null && b.isNotEmpty && t != null && t.isNotEmpty;
  }
}
