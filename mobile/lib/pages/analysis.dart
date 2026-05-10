import 'package:flutter/material.dart';
import '../api/client.dart';
import '../api/models.dart';

class AnalysisPage extends StatefulWidget {
  final ApiClient client;
  const AnalysisPage({super.key, required this.client});

  @override
  State<AnalysisPage> createState() => _AnalysisPageState();
}

class _AnalysisPageState extends State<AnalysisPage> {
  final _tickerCtrl = TextEditingController(text: '005930');
  DateTime _date = DateTime.now();
  Future<AnalysisResult>? _resultFuture;

  Future<void> _pickDate() async {
    final picked = await showDatePicker(
      context: context,
      initialDate: _date,
      firstDate: DateTime(2020),
      lastDate: DateTime.now(),
    );
    if (picked != null) setState(() => _date = picked);
  }

  void _run() {
    final t = _tickerCtrl.text.trim();
    if (t.isEmpty) return;
    setState(() {
      _resultFuture = widget.client.runAnalysis(t, _date);
    });
  }

  @override
  Widget build(BuildContext context) {
    final dateStr = '${_date.year}-${_date.month.toString().padLeft(2, "0")}-${_date.day.toString().padLeft(2, "0")}';
    return Scaffold(
      appBar: AppBar(title: const Text('AI 분석 (TradingAgents)')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: Theme.of(context).colorScheme.tertiaryContainer,
              borderRadius: BorderRadius.circular(8),
            ),
            child: const Text(
              '⚠️ 1회 분석은 LLM 토큰을 다량 사용 (\$0.10~\$1.00). 같은 종목·날짜는 1시간 캐시.',
            ),
          ),
          const SizedBox(height: 16),
          TextField(
            controller: _tickerCtrl,
            decoration: const InputDecoration(
              labelText: '종목코드 (예: 005930 또는 NVDA)',
              border: OutlineInputBorder(),
            ),
          ),
          const SizedBox(height: 12),
          Row(
            children: [
              Expanded(child: Text('분석 기준일: $dateStr')),
              TextButton.icon(
                onPressed: _pickDate,
                icon: const Icon(Icons.calendar_month),
                label: const Text('변경'),
              ),
            ],
          ),
          const SizedBox(height: 16),
          FilledButton.icon(
            onPressed: _run,
            icon: const Icon(Icons.psychology),
            label: const Text('▶ 분석 시작'),
          ),
          const SizedBox(height: 16),
          if (_resultFuture != null)
            FutureBuilder<AnalysisResult>(
              future: _resultFuture,
              builder: (ctx, snap) {
                if (snap.connectionState != ConnectionState.done) {
                  return const Padding(
                    padding: EdgeInsets.all(32),
                    child: Center(child: CircularProgressIndicator()),
                  );
                }
                if (snap.hasError) {
                  return Card(
                    color: Theme.of(context).colorScheme.errorContainer,
                    child: Padding(
                      padding: const EdgeInsets.all(16),
                      child: Text('오류: ${snap.error}'),
                    ),
                  );
                }
                final r = snap.data!;
                return Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    Card(
                      child: Padding(
                        padding: const EdgeInsets.all(16),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(r.ticker, style: Theme.of(context).textTheme.titleLarge),
                            const SizedBox(height: 4),
                            Text('기준일: ${r.tradeDate}'),
                            const Divider(),
                            const Text('Signal', style: TextStyle(fontWeight: FontWeight.bold)),
                            Text(r.signal),
                            const SizedBox(height: 8),
                            const Text('Final Decision', style: TextStyle(fontWeight: FontWeight.bold)),
                            Text(r.finalDecision),
                          ],
                        ),
                      ),
                    ),
                    _section('📊 시장 분석', r.marketReport),
                    _section('📰 뉴스', r.newsReport),
                    _section('💼 펀더멘털', r.fundamentalsReport),
                    _section('💬 센티먼트', r.sentimentReport),
                    _section('📋 투자 계획', r.investmentPlan),
                    _section('👤 트레이더', r.traderPlan),
                  ],
                );
              },
            ),
        ],
      ),
    );
  }

  Widget _section(String title, String body) {
    if (body.trim().isEmpty) return const SizedBox.shrink();
    return ExpansionTile(
      title: Text(title),
      children: [
        Padding(
          padding: const EdgeInsets.all(16),
          child: Text(body),
        ),
      ],
    );
  }
}
