import 'package:flutter/material.dart';
import '../api/client.dart';
import '../services/secure_settings.dart';
import 'home.dart';
import 'quote.dart';
import 'order.dart';
import 'analysis.dart';
import 'settings.dart';

class HomeShell extends StatefulWidget {
  const HomeShell({super.key});

  @override
  State<HomeShell> createState() => _HomeShellState();
}

class _HomeShellState extends State<HomeShell> {
  final _settings = SecureSettings();
  ApiClient? _client;
  int _idx = 0;
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _bootstrap();
  }

  Future<void> _bootstrap() async {
    setState(() => _loading = true);
    if (await _settings.isConfigured) {
      _client = ApiClient(
        baseUrl: (await _settings.baseUrl)!,
        apiToken: (await _settings.apiToken)!,
        realPin: await _settings.realPin,
      );
    }
    if (mounted) setState(() => _loading = false);
  }

  @override
  Widget build(BuildContext context) {
    if (_loading) {
      return const Scaffold(body: Center(child: CircularProgressIndicator()));
    }
    if (_client == null) {
      return SettingsPage(
        settings: _settings,
        onSaved: _bootstrap,
      );
    }

    final pages = <Widget>[
      HomePage(client: _client!),
      QuotePage(client: _client!),
      OrderPage(client: _client!),
      AnalysisPage(client: _client!),
      SettingsPage(settings: _settings, onSaved: _bootstrap),
    ];

    return Scaffold(
      body: pages[_idx],
      bottomNavigationBar: NavigationBar(
        selectedIndex: _idx,
        onDestinationSelected: (i) => setState(() => _idx = i),
        destinations: const [
          NavigationDestination(icon: Icon(Icons.home), label: '홈'),
          NavigationDestination(icon: Icon(Icons.show_chart), label: '시세'),
          NavigationDestination(icon: Icon(Icons.shopping_cart), label: '주문'),
          NavigationDestination(icon: Icon(Icons.psychology), label: 'AI'),
          NavigationDestination(icon: Icon(Icons.settings), label: '설정'),
        ],
      ),
    );
  }
}
