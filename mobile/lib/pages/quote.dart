import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:k_chart_plus/k_chart_plus.dart';
import '../api/client.dart';
import '../api/models.dart';

class QuotePage extends StatefulWidget {
  final ApiClient client;
  const QuotePage({super.key, required this.client});

  @override
  State<QuotePage> createState() => _QuotePageState();
}

class _QuotePageState extends State<QuotePage> {
  String _env = 'mock_domestic';
  TickerInfo? _selected;
  final _searchCtrl = TextEditingController();

  Future<Quote>? _quoteFuture;
  Future<OrderBook>? _obFuture;
  Future<List<Candle>>? _candlesFuture;

  // 차트 옵션
  bool _showVolume = true;
  final Set<MainState> _mainStateLi = {MainState.MA};
  final Set<SecondaryState> _secondary = {SecondaryState.MACD};
  final ChartStyle _chartStyle = ChartStyle();
  final ChartColors _chartColors = ChartColors();

  @override
  void initState() {
    super.initState();
    // 디폴트 종목 (삼성전자) 미리 로드
    _selectByCode('005930');
  }

  Future<void> _selectByCode(String code) async {
    if (_env.endsWith('_overseas')) {
      setState(() {
        _selected = TickerInfo(code: code.toUpperCase(), name: '', market: 'NAS');
        _quoteFuture = widget.client.quoteOverseas(code, env: _env);
        _obFuture = null;
        _candlesFuture = null;
      });
      return;
    }
    final info = await widget.client.tickerLookup(code).catchError((_) => null);
    setState(() {
      _selected = info ?? TickerInfo(code: code, name: '', market: 'KOSPI');
      _quoteFuture = widget.client.quoteDomestic(code, env: _env);
      _obFuture = widget.client.orderbook(code, env: _env);
      _candlesFuture = widget.client.candles(code, days: 180, env: _env);
    });
  }

  Future<List<TickerInfo>> _suggest(String query) async {
    if (_env.endsWith('_overseas')) return [];
    if (query.trim().isEmpty) return [];
    return widget.client.searchTickers(query, limit: 10);
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
            onSelectionChanged: (s) {
              setState(() => _env = s.first);
            },
          ),
          const SizedBox(height: 12),
          // 종목명/코드 자동완성 검색
          if (!isUsd)
            Autocomplete<TickerInfo>(
              optionsBuilder: (TextEditingValue tv) async => await _suggest(tv.text),
              displayStringForOption: (t) => t.displayLabel,
              fieldViewBuilder: (ctx, ctrl, fn, onSubmit) {
                _searchCtrl.value = ctrl.value;
                return TextField(
                  controller: ctrl,
                  focusNode: fn,
                  onSubmitted: (s) {
                    onSubmit();
                    if (RegExp(r'^\d{6}$').hasMatch(s.trim())) {
                      _selectByCode(s.trim());
                    }
                  },
                  decoration: const InputDecoration(
                    labelText: '종목명 또는 코드 (예: 삼성전자, 005930, 카카오)',
                    prefixIcon: Icon(Icons.search),
                    border: OutlineInputBorder(),
                  ),
                );
              },
              onSelected: (t) => _selectByCode(t.code),
              optionsViewBuilder: (ctx, onSelect, options) => Align(
                alignment: Alignment.topLeft,
                child: Material(
                  elevation: 4,
                  child: ConstrainedBox(
                    constraints: const BoxConstraints(maxHeight: 280, maxWidth: 360),
                    child: ListView(
                      shrinkWrap: true,
                      padding: EdgeInsets.zero,
                      children: options
                          .map((t) => ListTile(
                                dense: true,
                                title: Text(t.name),
                                subtitle: Text('${t.code} · ${t.market}'),
                                onTap: () => onSelect(t),
                              ))
                          .toList(),
                    ),
                  ),
                ),
              ),
            )
          else
            Row(
              children: [
                Expanded(
                  child: TextField(
                    controller: _searchCtrl,
                    decoration: const InputDecoration(
                      labelText: '심볼 (예: NVDA, AAPL)',
                      border: OutlineInputBorder(),
                    ),
                  ),
                ),
                const SizedBox(width: 8),
                FilledButton(
                  onPressed: () => _selectByCode(_searchCtrl.text.trim()),
                  child: const Text('조회'),
                ),
              ],
            ),
          if (_selected != null) ...[
            const SizedBox(height: 16),
            _buildHeader(),
            const SizedBox(height: 16),
            if (_quoteFuture != null) _buildQuoteCard(fmt, sym),
            const SizedBox(height: 16),
            if (_candlesFuture != null) _buildAdvancedChart(),
            if (_candlesFuture != null) _buildChartControls(),
            const SizedBox(height: 16),
            if (_obFuture != null) _buildOrderbook(_obFuture!, fmt),
          ],
        ],
      ),
    );
  }

  Widget _buildHeader() {
    if (_selected == null) return const SizedBox.shrink();
    return Row(
      crossAxisAlignment: CrossAxisAlignment.center,
      children: [
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                _selected!.name.isEmpty ? _selected!.code : _selected!.name,
                style: Theme.of(context).textTheme.titleLarge,
              ),
              Text(
                '${_selected!.code} · ${_selected!.market}',
                style: Theme.of(context).textTheme.bodySmall,
              ),
            ],
          ),
        ),
        IconButton(
          tooltip: '새로고침',
          icon: const Icon(Icons.refresh),
          onPressed: () => _selectByCode(_selected!.code),
        ),
      ],
    );
  }

  Widget _buildQuoteCard(NumberFormat fmt, String sym) {
    return FutureBuilder<Quote>(
      future: _quoteFuture,
      builder: (ctx, snap) {
        if (snap.connectionState != ConnectionState.done) {
          return const Center(child: Padding(padding: EdgeInsets.all(16), child: CircularProgressIndicator()));
        }
        if (snap.hasError) return Text('오류: ${snap.error}');
        final q = snap.data!;
        final color = q.change > 0
            ? Colors.redAccent
            : (q.change < 0 ? Colors.lightBlueAccent : null);
        return Card(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
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
                  runSpacing: 4,
                  children: [
                    Text('고 ${q.high == null ? '—' : sym + fmt.format(q.high)}'),
                    Text('저 ${q.low == null ? '—' : sym + fmt.format(q.low)}'),
                    Text('시 ${q.open == null ? '—' : sym + fmt.format(q.open)}'),
                    Text('전일 ${q.prevClose == null ? '—' : sym + fmt.format(q.prevClose)}'),
                    Text('거래량 ${fmt.format(q.volume)}'),
                  ],
                ),
              ],
            ),
          ),
        );
      },
    );
  }

  Widget _buildAdvancedChart() {
    return FutureBuilder<List<Candle>>(
      future: _candlesFuture,
      builder: (ctx, snap) {
        if (snap.connectionState != ConnectionState.done) {
          return const SizedBox(height: 350, child: Center(child: CircularProgressIndicator()));
        }
        if (snap.hasError || snap.data == null || snap.data!.isEmpty) {
          return const Card(
            child: Padding(padding: EdgeInsets.all(16), child: Text('차트 데이터 없음')),
          );
        }
        final candles = snap.data!;
        final entities = candles
            .map((c) => KLineEntity.fromCustom(
                  time: c.date.millisecondsSinceEpoch,
                  open: c.open,
                  high: c.high,
                  low: c.low,
                  close: c.close,
                  vol: c.volume.toDouble(),
                  amount: c.volume * c.close,
                ))
            .toList();
        DataUtil.calculate(entities);
        return SizedBox(
          height: 480,
          child: KChartWidget(
            entities,
            _chartStyle,
            _chartColors,
            mainStateLi: _mainStateLi,
            volHidden: !_showVolume,
            secondaryStateLi: _secondary,
            isTrendLine: false,
            fixedLength: 0,
            xFrontPadding: 24,
            timeFormat: TimeFormat.YEAR_MONTH_DAY,
          ),
        );
      },
    );
  }

  Widget _buildChartControls() {
    return Padding(
      padding: const EdgeInsets.only(top: 8),
      child: Wrap(
        spacing: 8,
        runSpacing: 8,
        crossAxisAlignment: WrapCrossAlignment.center,
        children: [
          const Text('주지표:'),
          for (final m in [
            (MainState.MA, 'MA'),
            (MainState.BOLL, '볼린저'),
            (MainState.SAR, 'SAR'),
          ])
            FilterChip(
              label: Text(m.$2),
              selected: _mainStateLi.contains(m.$1),
              onSelected: (sel) => setState(() {
                if (sel) {
                  _mainStateLi.add(m.$1);
                } else {
                  _mainStateLi.remove(m.$1);
                }
              }),
            ),
          const SizedBox(width: 8),
          const Text('보조:'),
          for (final s in [
            (SecondaryState.MACD, 'MACD'),
            (SecondaryState.KDJ, 'KDJ'),
            (SecondaryState.RSI, 'RSI'),
            (SecondaryState.WR, 'WR'),
            (SecondaryState.CCI, 'CCI'),
          ])
            FilterChip(
              label: Text(s.$2),
              selected: _secondary.contains(s.$1),
              onSelected: (sel) => setState(() {
                if (sel) {
                  _secondary.add(s.$1);
                } else {
                  _secondary.remove(s.$1);
                }
              }),
            ),
          const SizedBox(width: 8),
          FilterChip(
            label: const Text('거래량'),
            selected: _showVolume,
            onSelected: (sel) => setState(() => _showVolume = sel),
          ),
        ],
      ),
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
