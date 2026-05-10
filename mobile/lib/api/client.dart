import 'dart:convert';
import 'package:http/http.dart' as http;
import 'models.dart';

class ApiException implements Exception {
  final int statusCode;
  final String message;
  ApiException(this.statusCode, this.message);
  @override
  String toString() => 'ApiException($statusCode): $message';
}

class ApiClient {
  final String baseUrl; // 예: https://stock-mts.example.com 또는 http://192.168.0.10:8765
  final String apiToken;
  final String? realPin; // 실전 주문에 사용

  ApiClient({required this.baseUrl, required this.apiToken, this.realPin});

  Map<String, String> get _baseHeaders => {
        'X-API-Token': apiToken,
        'Content-Type': 'application/json',
      };

  Uri _u(String path, [Map<String, dynamic>? query]) =>
      Uri.parse('$baseUrl$path').replace(
        queryParameters: query?.map((k, v) => MapEntry(k, v.toString())),
      );

  Future<dynamic> _get(String path, {Map<String, dynamic>? query}) async {
    final resp = await http.get(_u(path, query), headers: _baseHeaders).timeout(const Duration(seconds: 30));
    if (resp.statusCode != 200) {
      throw ApiException(resp.statusCode, resp.body);
    }
    return jsonDecode(utf8.decode(resp.bodyBytes));
  }

  Future<dynamic> _post(String path, Map<String, dynamic> body, {Map<String, String>? extraHeaders}) async {
    final headers = {..._baseHeaders, if (extraHeaders != null) ...extraHeaders};
    final resp = await http
        .post(_u(path), headers: headers, body: jsonEncode(body))
        .timeout(const Duration(minutes: 10)); // AI 분석은 시간이 걸림
    if (resp.statusCode != 200) {
      throw ApiException(resp.statusCode, resp.body);
    }
    return jsonDecode(utf8.decode(resp.bodyBytes));
  }

  Future<List<TickerInfo>> searchTickers(String query, {int limit = 20}) async {
    if (query.trim().isEmpty) return [];
    final data = await _get('/search', query: {'q': query, 'limit': limit}) as List;
    return data.map((e) => TickerInfo.fromJson(e as Map<String, dynamic>)).toList();
  }

  Future<TickerInfo?> tickerLookup(String code) async {
    try {
      final data = await _get('/ticker/$code');
      return TickerInfo.fromJson(data as Map<String, dynamic>);
    } on ApiException catch (e) {
      if (e.statusCode == 404) return null;
      rethrow;
    }
  }

  Future<bool> health() async {
    try {
      final resp = await http.get(Uri.parse('$baseUrl/health')).timeout(const Duration(seconds: 5));
      return resp.statusCode == 200;
    } catch (_) {
      return false;
    }
  }

  Future<Quote> quoteDomestic(String ticker, {String env = 'mock_domestic'}) async {
    final data = await _get('/quote/domestic/$ticker', query: {'env': env});
    return Quote.fromJson(data);
  }

  Future<Quote> quoteOverseas(String symbol, {String exchange = 'NAS', String env = 'mock_overseas'}) async {
    final data = await _get('/quote/overseas/$symbol', query: {'exchange': exchange, 'env': env});
    return Quote.fromJson(data);
  }

  Future<Quote> futuresQuote(String code) async {
    final data = await _get('/futures/quote/$code');
    return Quote.fromJson(data);
  }

  Future<OrderBook> orderbook(String ticker, {String env = 'mock_domestic'}) async {
    final data = await _get('/orderbook/domestic/$ticker', query: {'env': env});
    return OrderBook.fromJson(data);
  }

  Future<List<Candle>> candles(String ticker, {int days = 30, String env = 'mock_domestic'}) async {
    final data = await _get('/candles/domestic/$ticker', query: {'days': days, 'env': env}) as List;
    return data.map((e) => Candle.fromJson(e)).toList();
  }

  Future<Balance> balance({String env = 'mock_domestic'}) async {
    final data = await _get('/balance', query: {'env': env});
    return Balance.fromJson(data);
  }

  Future<OrderResult> orderBuy({
    required String env,
    required String ticker,
    required int qty,
    double? price,
    String orderType = 'limit',
    String? exchange,
  }) async {
    final headers = <String, String>{};
    if (env.startsWith('real_') && realPin != null) {
      headers['X-Real-PIN'] = realPin!;
    }
    final data = await _post(
      '/order/buy',
      {
        'env': env,
        'ticker': ticker,
        'qty': qty,
        if (price != null) 'price': price,
        'order_type': orderType,
        if (exchange != null) 'exchange': exchange,
      },
      extraHeaders: headers,
    );
    return OrderResult.fromJson(data);
  }

  Future<OrderResult> orderSell({
    required String env,
    required String ticker,
    required int qty,
    double? price,
    String orderType = 'limit',
    String? exchange,
  }) async {
    final headers = <String, String>{};
    if (env.startsWith('real_') && realPin != null) {
      headers['X-Real-PIN'] = realPin!;
    }
    final data = await _post(
      '/order/sell',
      {
        'env': env,
        'ticker': ticker,
        'qty': qty,
        if (price != null) 'price': price,
        'order_type': orderType,
        if (exchange != null) 'exchange': exchange,
      },
      extraHeaders: headers,
    );
    return OrderResult.fromJson(data);
  }

  Future<AnalysisResult> runAnalysis(String ticker, DateTime tradeDate) async {
    final data = await _post('/analysis', {
      'ticker': ticker,
      'trade_date': tradeDate.toIso8601String().substring(0, 10),
    });
    return AnalysisResult.fromJson(data);
  }
}
