import 'package:flutter/material.dart';
import 'package:local_auth/local_auth.dart';
import '../api/client.dart';
import '../api/models.dart';

class OrderPage extends StatefulWidget {
  final ApiClient client;
  const OrderPage({super.key, required this.client});

  @override
  State<OrderPage> createState() => _OrderPageState();
}

class _OrderPageState extends State<OrderPage> {
  String _env = 'mock_domestic';
  String _side = 'buy';
  final _tickerCtrl = TextEditingController(text: '005930');
  final _qtyCtrl = TextEditingController(text: '1');
  final _priceCtrl = TextEditingController();
  bool _isMarket = false;
  bool _isSubmitting = false;

  bool get _isReal => _env.startsWith('real_');
  bool get _isOverseas => _env.endsWith('_overseas');

  Future<void> _submit() async {
    final ticker = _tickerCtrl.text.trim();
    final qty = int.tryParse(_qtyCtrl.text.trim()) ?? 0;
    final priceStr = _priceCtrl.text.trim();
    final price = priceStr.isEmpty ? null : double.tryParse(priceStr);

    if (ticker.isEmpty || qty <= 0) {
      _snack('종목코드/수량 확인'); return;
    }
    if (!_isMarket && price == null) {
      _snack('지정가 가격을 입력하세요'); return;
    }
    if (_isOverseas && price == null) {
      _snack('해외 주문은 가격 필수'); return;
    }

    // 실전 → 생체인증 + 다이얼로그 확인
    if (_isReal) {
      final ok = await _biometricThenConfirm();
      if (!ok) return;
    }

    setState(() => _isSubmitting = true);
    try {
      final fn = _side == 'buy' ? widget.client.orderBuy : widget.client.orderSell;
      final result = await fn(
        env: _env,
        ticker: ticker,
        qty: qty,
        price: _isMarket ? null : price,
        orderType: _isMarket ? 'market' : 'limit',
        exchange: _isOverseas ? 'NAS' : null,
      );
      _showResult(result);
    } catch (e) {
      _snack('오류: $e');
    } finally {
      if (mounted) setState(() => _isSubmitting = false);
    }
  }

  Future<bool> _biometricThenConfirm() async {
    // 1) 생체 인증 (가능한 경우)
    final auth = LocalAuthentication();
    try {
      final canCheck = await auth.canCheckBiometrics;
      if (canCheck) {
        final ok = await auth.authenticate(
          localizedReason: '실전 거래를 진행하려면 생체 인증이 필요합니다',
          options: const AuthenticationOptions(biometricOnly: false, stickyAuth: true),
        );
        if (!ok) {
          _snack('생체 인증 실패'); return false;
        }
      }
    } catch (_) {/* 인증 미지원 → 다이얼로그만 */}

    // 2) 명시 다이얼로그
    if (!mounted) return false;
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: Theme.of(ctx).colorScheme.errorContainer,
        title: const Text('🔴 실전 주문 확인'),
        content: Text(
          '${_side == "buy" ? "매수" : "매도"} ${_tickerCtrl.text} '
          '${_qtyCtrl.text}주를 실거래로 즉시 체결합니다. 진행하시겠습니까?',
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('취소')),
          FilledButton(
            style: FilledButton.styleFrom(backgroundColor: Colors.red),
            onPressed: () => Navigator.pop(ctx, true),
            child: const Text('확인'),
          ),
        ],
      ),
    );
    return confirmed ?? false;
  }

  void _snack(String msg) {
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(msg)));
  }

  void _showResult(OrderResult r) {
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text(r.success ? '✅ 주문 접수' : '⚠ 주문 응답'),
        content: Text('주문번호: ${r.orderNo ?? "—"}\n메시지: ${r.msg}'),
        actions: [TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('확인'))],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('주문')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          SegmentedButton<String>(
            segments: const [
              ButtonSegment(value: 'mock_domestic', label: Text('🟢 모의 국내')),
              ButtonSegment(value: 'mock_overseas', label: Text('🟢 모의 해외')),
              ButtonSegment(value: 'real_domestic', label: Text('🔴 실전 국내')),
              ButtonSegment(value: 'real_overseas', label: Text('🔴 실전 해외')),
            ],
            selected: {_env},
            onSelectionChanged: (s) => setState(() => _env = s.first),
          ),
          if (_isReal)
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 8),
              child: Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: Theme.of(context).colorScheme.errorContainer,
                  borderRadius: BorderRadius.circular(8),
                ),
                child: const Text(
                  '⚠️ 실전 모드 — 실제 자금 즉시 체결. 생체 인증 + 확인 다이얼로그 + 서버 PIN 검증.',
                ),
              ),
            ),
          const SizedBox(height: 12),
          SegmentedButton<String>(
            segments: const [
              ButtonSegment(value: 'buy', label: Text('매수')),
              ButtonSegment(value: 'sell', label: Text('매도')),
            ],
            selected: {_side},
            onSelectionChanged: (s) => setState(() => _side = s.first),
          ),
          const SizedBox(height: 12),
          TextField(
            controller: _tickerCtrl,
            decoration: InputDecoration(
              labelText: _isOverseas ? '심볼' : '종목코드',
              border: const OutlineInputBorder(),
            ),
          ),
          const SizedBox(height: 12),
          TextField(
            controller: _qtyCtrl,
            keyboardType: TextInputType.number,
            decoration: const InputDecoration(labelText: '수량', border: OutlineInputBorder()),
          ),
          const SizedBox(height: 12),
          SwitchListTile(
            value: _isMarket,
            title: const Text('시장가'),
            subtitle: Text(_isOverseas ? '해외는 시장가 미지원' : '체크 시 가격 무시'),
            onChanged: _isOverseas ? null : (v) => setState(() => _isMarket = v),
          ),
          if (!_isMarket)
            TextField(
              controller: _priceCtrl,
              keyboardType: const TextInputType.numberWithOptions(decimal: true),
              decoration: InputDecoration(
                labelText: '가격${_isOverseas ? " (USD)" : ""}',
                border: const OutlineInputBorder(),
              ),
            ),
          const SizedBox(height: 24),
          SizedBox(
            width: double.infinity,
            height: 56,
            child: FilledButton(
              style: FilledButton.styleFrom(
                backgroundColor: _isReal ? Colors.red : null,
              ),
              onPressed: _isSubmitting ? null : _submit,
              child: _isSubmitting
                  ? const CircularProgressIndicator(color: Colors.white)
                  : Text(
                      '${_isReal ? "🔴 " : ""}${_side == "buy" ? "매수" : "매도"} 실행',
                      style: const TextStyle(fontSize: 18),
                    ),
            ),
          ),
        ],
      ),
    );
  }
}
