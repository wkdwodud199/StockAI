import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import '../api/client.dart';
import '../api/models.dart';

class HomePage extends StatefulWidget {
  final ApiClient client;
  const HomePage({super.key, required this.client});

  @override
  State<HomePage> createState() => _HomePageState();
}

class _HomePageState extends State<HomePage> {
  String _env = 'mock_domestic';
  Future<Balance>? _balanceFuture;

  @override
  void initState() {
    super.initState();
    _refresh();
  }

  void _refresh() {
    setState(() {
      _balanceFuture = widget.client.balance(env: _env);
    });
  }

  @override
  Widget build(BuildContext context) {
    final fmt = NumberFormat('#,##0');
    return Scaffold(
      appBar: AppBar(
        title: const Text('홈'),
        actions: [
          IconButton(icon: const Icon(Icons.refresh), onPressed: _refresh),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: () async => _refresh(),
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            SegmentedButton<String>(
              segments: const [
                ButtonSegment(value: 'mock_domestic', label: Text('🟢 모의 국내')),
                ButtonSegment(value: 'mock_overseas', label: Text('🟢 모의 해외')),
                ButtonSegment(value: 'real_domestic', label: Text('🔴 실전 국내')),
              ],
              selected: {_env},
              onSelectionChanged: (s) {
                setState(() => _env = s.first);
                _refresh();
              },
            ),
            const SizedBox(height: 16),
            FutureBuilder<Balance>(
              future: _balanceFuture,
              builder: (ctx, snap) {
                if (snap.connectionState != ConnectionState.done) {
                  return const Center(child: Padding(padding: EdgeInsets.all(32), child: CircularProgressIndicator()));
                }
                if (snap.hasError) {
                  return Card(
                    color: Theme.of(context).colorScheme.errorContainer,
                    child: Padding(
                      padding: const EdgeInsets.all(16),
                      child: Text('오류: ${snap.error}', style: TextStyle(color: Theme.of(context).colorScheme.onErrorContainer)),
                    ),
                  );
                }
                final b = snap.data!;
                final isUsd = _env.endsWith('_overseas');
                final sym = isUsd ? '\$' : '₩';
                return Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    Card(
                      child: Padding(
                        padding: const EdgeInsets.all(16),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            const Text('계좌 요약'),
                            const SizedBox(height: 8),
                            _row('예수금', '$sym${fmt.format(b.deposit)}'),
                            _row('평가총액', '$sym${fmt.format(b.evalTotal)}'),
                            _row(
                              '평가손익',
                              '$sym${fmt.format(b.pnlTotal)}',
                              color: b.pnlTotal >= 0 ? Colors.redAccent : Colors.lightBlueAccent,
                            ),
                          ],
                        ),
                      ),
                    ),
                    const SizedBox(height: 16),
                    Text('보유 종목 (${b.holdings.length})', style: Theme.of(context).textTheme.titleMedium),
                    const SizedBox(height: 8),
                    if (b.holdings.isEmpty)
                      const Padding(padding: EdgeInsets.all(16), child: Text('보유 종목 없음'))
                    else ...b.holdings.map((h) => Card(
                          child: ListTile(
                            title: Text('${h.ticker} ${h.name}'),
                            subtitle: Text('${h.qty}주 · 평단 $sym${fmt.format(h.avgPrice)}'),
                            trailing: Column(
                              mainAxisAlignment: MainAxisAlignment.center,
                              crossAxisAlignment: CrossAxisAlignment.end,
                              children: [
                                Text('$sym${fmt.format(h.evalAmt)}'),
                                Text(
                                  '${h.pnl >= 0 ? '+' : ''}${fmt.format(h.pnl)} (${h.pnlPct.toStringAsFixed(2)}%)',
                                  style: TextStyle(color: h.pnl >= 0 ? Colors.redAccent : Colors.lightBlueAccent),
                                ),
                              ],
                            ),
                          ),
                        )),
                  ],
                );
              },
            ),
          ],
        ),
      ),
    );
  }

  Widget _row(String label, String value, {Color? color}) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(label),
          Text(value, style: TextStyle(fontWeight: FontWeight.bold, color: color)),
        ],
      ),
    );
  }
}
