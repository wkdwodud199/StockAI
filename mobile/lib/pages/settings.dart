import 'package:flutter/material.dart';
import '../services/secure_settings.dart';
import '../api/client.dart';

class SettingsPage extends StatefulWidget {
  final SecureSettings settings;
  final VoidCallback onSaved;

  const SettingsPage({super.key, required this.settings, required this.onSaved});

  @override
  State<SettingsPage> createState() => _SettingsPageState();
}

class _SettingsPageState extends State<SettingsPage> {
  final _baseUrlCtrl = TextEditingController();
  final _tokenCtrl = TextEditingController();
  final _pinCtrl = TextEditingController();
  bool _testing = false;
  String? _testResult;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    _baseUrlCtrl.text = await widget.settings.baseUrl ?? '';
    _tokenCtrl.text = await widget.settings.apiToken ?? '';
    _pinCtrl.text = await widget.settings.realPin ?? '';
    if (mounted) setState(() {});
  }

  Future<void> _testConnection() async {
    setState(() {
      _testing = true;
      _testResult = null;
    });
    final url = _baseUrlCtrl.text.trim();
    final ok = await ApiClient(baseUrl: url, apiToken: _tokenCtrl.text.trim()).health();
    if (mounted) {
      setState(() {
        _testing = false;
        _testResult = ok ? '✅ 연결 성공' : '❌ 연결 실패';
      });
    }
  }

  Future<void> _save() async {
    await widget.settings.setBaseUrl(_baseUrlCtrl.text.trim());
    await widget.settings.setApiToken(_tokenCtrl.text.trim());
    if (_pinCtrl.text.trim().isNotEmpty) {
      await widget.settings.setRealPin(_pinCtrl.text.trim());
    }
    widget.onSaved();
    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('설정 저장됨')),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('설정')),
      body: Padding(
        padding: const EdgeInsets.all(16),
        child: ListView(
          children: [
            TextField(
              controller: _baseUrlCtrl,
              decoration: const InputDecoration(
                labelText: '백엔드 URL',
                hintText: 'https://your-tunnel.trycloudflare.com',
                border: OutlineInputBorder(),
              ),
              keyboardType: TextInputType.url,
              autocorrect: false,
            ),
            const SizedBox(height: 12),
            TextField(
              controller: _tokenCtrl,
              decoration: const InputDecoration(
                labelText: 'API 토큰 (.env MOBILE_API_TOKEN)',
                border: OutlineInputBorder(),
              ),
              obscureText: true,
              autocorrect: false,
            ),
            const SizedBox(height: 12),
            TextField(
              controller: _pinCtrl,
              decoration: const InputDecoration(
                labelText: '실전 PIN (.env REAL_MODE_PIN)',
                helperText: '실전 매수/매도 시 헤더에 자동 첨부',
                border: OutlineInputBorder(),
              ),
              obscureText: true,
              keyboardType: TextInputType.number,
              maxLength: 4,
            ),
            const SizedBox(height: 16),
            Row(
              children: [
                ElevatedButton.icon(
                  onPressed: _testing ? null : _testConnection,
                  icon: _testing
                      ? const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2))
                      : const Icon(Icons.network_check),
                  label: const Text('연결 테스트'),
                ),
                const SizedBox(width: 12),
                FilledButton.icon(
                  onPressed: _save,
                  icon: const Icon(Icons.save),
                  label: const Text('저장'),
                ),
              ],
            ),
            if (_testResult != null) Padding(
              padding: const EdgeInsets.only(top: 8),
              child: Text(_testResult!, style: Theme.of(context).textTheme.bodyLarge),
            ),
            const Divider(height: 32),
            Text('보안 안내', style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: 8),
            const Text(
              '• 토큰/PIN은 Android Keystore 기반 암호화 저장(flutter_secure_storage).\n'
              '• 실전 거래 시 PC .env 의 REAL_MODE_PIN 과 동일한 값 입력.\n'
              '• 백엔드는 PC에서 uvicorn app.api.main:app --port 8765 로 실행.\n'
              '• 외부 접속 시 Cloudflare Tunnel 또는 ngrok 권장.',
            ),
          ],
        ),
      ),
    );
  }
}
