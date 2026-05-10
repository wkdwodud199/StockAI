import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import '../api/client.dart';
import '../api/models.dart';

class QuotePage extends StatefulWidget {
  final ApiClient client;
  const QuotePage({super.key, required this.client});

  @override
  State<QuotePage> createState() => _QuotePageState();
}

class _QuotePageState extends State<QuotePage> {
  final _tickerCtrl = TextEditingController(text: '005930');
  String _env = 'mock_domestic';
  Future<Quote>? _quoteFuture;
  Future<OrderBook>? _obFuture;
  Future<List<Candle>>? _candlesFuture;

  void _load() {
    final t = _tickerCtrl.text.trim();
    if (t.isEmpty) return;
    setState(() {
      _quoteFuture = _env.endsWith('_overseas')
          ? widget.client.quoteOverseas(t, env: _env)
          : widget.client.quoteDomestic(t, env: _env);
      _obFuture = _env.endsWith('_overseas') ? null : widget.client.orderbook(t, env: _env);
      _candlesFuture = _env.endsWith('_overseas') ? null : widget.client.candles(t, env: _env);
    });
  }

  @override
  Widget build(BuildContext context) {
    final fmt = NumberFormat('#,##0');
    final isUsd = _env.endsWith('_overseas');
    final sym = isUsd ? '\$' : '₩';

    return Scaffold(
      appBar: AppBar(title: const Text('시세')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          SegmentedButton<String>(
            segments: const [
              ButtonSegment(value: 'mock_domestic', label: Text('국내')),
              ButtonSegment(value: 'mock_overseas', label: Text('해외')),
            ],
            selected: {_env},
            onSelectionChanged: (s) => setState(() => _env = s.first),
          ),
          const SizedBox(height: 12),
          Row(
            children: [
              Expanded(
                child: TextField(
                  controller: _tickerCtrl,
                  decoration: InputDecoration(
                    labelText: isUsd ? '심볼 (예: NVDA)' : '종목코드 (6자리)',
                    border: const OutlineInputBorder(),
                  ),
                ),
              ),
              const SizedBox(width: 8),
              FilledButton(onPressed: _load, child: const Text('조회')),
            ],
          ),
          const SizedBox(height: 16),
          if (_quoteFuture != null)
            FutureBuilder<Quote>(
              future: _quoteFuture,
              builder: (ctx, snap) {
                if (snap.connectionState != ConnectionState.done) {
                  return const Center(child: CircularProgressIndicator());
                }
                if (snap.hasError) {
                  return Text('오류: ${snap.error}');
                }
                final q = snap.data!;
                final color = q.change > 0 ? Colors.redAccent : (q.change < 0 ? Colors.lightBlueAccent : null);
                return Card(
                  child: Padding(
                    padding: const EdgeInsets.all(16),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(q.ticker, style: Theme.of(context).textTheme.titleLarge),
                        const SizedBox(height: 8),
                        Text(
                          '$sym${fmt.format(q.price)}',
                          style: Theme.of(context).textTheme.headlineMedium?.copyWith(color: color),
                        ),
                        Text(
                          '${q.change >= 0 ? '+' : ''}${fmt.format(q.change)} (${q.changePct.toStringAsFixed(2)}%)',
                          style: TextStyle(color: color),
                        ),
                        const SizedBox(height: 8),
                        Wrap(
                          spacing: 16,
                          children: [
                            Text('고 ${q.high == null ? '—' : sym + fmt.format(q.high)}'),
                            Text('저 ${q.low == null ? '—' : sym + fmt.format(q.low)}'),
                            Text('거래량 ${fmt.format(q.volume)}'),
                          ],
                        ),
                      ],
                    ),
                  ),
                );
              },
            ),
          const SizedBox(height: 16),
          if (_candlesFuture != null) _buildChart(_candlesFuture!),
          const SizedBox(height: 16),
          if (_obFuture != null) _buildOrderbook(_obFuture!, fmt),
        ],
      ),
    );
  }

  Widget _buildChart(Future<List<Candle>> f) {
    return FutureBuilder<List<Candle>>(
      future: f,
      builder: (ctx, snap) {
        if (snap.connectionState != ConnectionState.done) return const SizedBox.shrink();
        if (snap.hasError || snap.data == null || snap.data!.isEmpty) {
          return const SizedBox.shrink();
        }
        final candles = snap.data!;
        final spots = <FlSpot>[
          for (int i = 0; i < candles.length; i++) FlSpot(i.toDouble(), candles[i].close)
        ];
        return SizedBox(
          height: 200,
          child: Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: LineChart(LineChartData(
                lineBarsData: [
                  LineChartBarData(spots: spots, isCurved: true, dotData: const FlDotData(show: false)),
                ],
                gridData: const FlGridData(show: false),
                titlesData: const FlTitlesData(show: false),
              )),
            ),
          ),
        );
      },
    );
  }

  Widget _buildOrderbook(Future<OrderBook> f, NumberFormat fmt) {
    return FutureBuilder<OrderBook>(
      future: f,
      builder: (ctx, snap) {
        if (snap.connectionState != ConnectionState.done) return const SizedBox.shrink();
        if (snap.hasError || snap.data == null) return const SizedBox.shrink();
        final ob = snap.data!;
        if (ob.bids.isEmpty && ob.asks.isEmpty) {
          return const Card(child: Padding(padding: EdgeInsets.all(16), child: Text('호가 데이터 없음')));
        }
        return Card(
          child: Padding(
            padding: const EdgeInsets.all(8),
            child: Table(
              columnWidths: const {
                0: FlexColumnWidth(2),
                1: FlexColumnWidth(2),
                2: FlexColumnWidth(2),
                3: FlexColumnWidth(2),
              },
              children: [
                const TableRow(children: [
                  Text('매도잔량', textAlign: TextAlign.right),
                  Text('매도호가', textAlign: TextAlign.right),
                  Text('매수호가', textAlign: TextAlign.right),
                  Text('매수잔량', textAlign: TextAlign.right),
                ]),
                for (int i = 0; i < 10; i++)
                  TableRow(children: [
                    Text(i < ob.asks.length ? fmt.format(ob.asks[i].qty) : '', textAlign: TextAlign.right),
                    Text(i < ob.asks.length ? fmt.format(ob.asks[i].price) : '',
                        textAlign: TextAlign.right, style: const TextStyle(color: Colors.lightBlueAccent)),
                    Text(i < ob.bids.length ? fmt.format(ob.bids[i].price) : '',
                        textAlign: TextAlign.right, style: const TextStyle(color: Colors.redAccent)),
                    Text(i < ob.bids.length ? fmt.format(ob.bids[i].qty) : '', textAlign: TextAlign.right),
                  ]),
              ],
            ),
          ),
        );
      },
    );
  }
}
