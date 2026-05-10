/// FastAPI 응답 모델 (app/api/main.py 의 *Out 모델과 동일 스키마).
class TickerInfo {
  final String code;
  final String name;
  final String market;
  TickerInfo({required this.code, required this.name, required this.market});
  factory TickerInfo.fromJson(Map<String, dynamic> j) => TickerInfo(
        code: j['code'] as String,
        name: j['name'] as String,
        market: j['market'] as String? ?? '',
      );
  String get displayLabel => '$code · $name';
}

class Quote {
  final String ticker;
  final double price;
  final double change;
  final double changePct;
  final int volume;
  final double? high;
  final double? low;
  final double? open;
  final double? prevClose;

  Quote({
    required this.ticker,
    required this.price,
    this.change = 0,
    this.changePct = 0,
    this.volume = 0,
    this.high,
    this.low,
    this.open,
    this.prevClose,
  });

  factory Quote.fromJson(Map<String, dynamic> j) => Quote(
        ticker: j['ticker'] as String,
        price: (j['price'] as num).toDouble(),
        change: (j['change'] as num? ?? 0).toDouble(),
        changePct: (j['change_pct'] as num? ?? 0).toDouble(),
        volume: (j['volume'] as num? ?? 0).toInt(),
        high: (j['high'] as num?)?.toDouble(),
        low: (j['low'] as num?)?.toDouble(),
        open: (j['open'] as num?)?.toDouble(),
        prevClose: (j['prev_close'] as num?)?.toDouble(),
      );
}

class OrderBookLevel {
  final double price;
  final int qty;
  OrderBookLevel({required this.price, required this.qty});
  factory OrderBookLevel.fromJson(Map<String, dynamic> j) =>
      OrderBookLevel(price: (j['price'] as num).toDouble(), qty: (j['qty'] as num).toInt());
}

class OrderBook {
  final String ticker;
  final List<OrderBookLevel> bids;
  final List<OrderBookLevel> asks;
  OrderBook({required this.ticker, required this.bids, required this.asks});
  factory OrderBook.fromJson(Map<String, dynamic> j) => OrderBook(
        ticker: j['ticker'] as String,
        bids: (j['bids'] as List).map((e) => OrderBookLevel.fromJson(e)).toList(),
        asks: (j['asks'] as List).map((e) => OrderBookLevel.fromJson(e)).toList(),
      );
}

class Candle {
  final DateTime date;
  final double open;
  final double high;
  final double low;
  final double close;
  final int volume;
  Candle({
    required this.date,
    required this.open,
    required this.high,
    required this.low,
    required this.close,
    required this.volume,
  });
  factory Candle.fromJson(Map<String, dynamic> j) => Candle(
        date: DateTime.parse(j['date'] as String),
        open: (j['open'] as num).toDouble(),
        high: (j['high'] as num).toDouble(),
        low: (j['low'] as num).toDouble(),
        close: (j['close'] as num).toDouble(),
        volume: (j['volume'] as num).toInt(),
      );
}

class Holding {
  final String ticker;
  final String name;
  final int qty;
  final double avgPrice;
  final double currentPrice;
  final double evalAmt;
  final double pnl;
  final double pnlPct;
  Holding({
    required this.ticker,
    required this.name,
    required this.qty,
    required this.avgPrice,
    required this.currentPrice,
    required this.evalAmt,
    required this.pnl,
    required this.pnlPct,
  });
  factory Holding.fromJson(Map<String, dynamic> j) => Holding(
        ticker: j['ticker'] as String,
        name: j['name'] as String? ?? '',
        qty: (j['qty'] as num).toInt(),
        avgPrice: (j['avg_price'] as num).toDouble(),
        currentPrice: (j['current_price'] as num? ?? 0).toDouble(),
        evalAmt: (j['eval_amt'] as num? ?? 0).toDouble(),
        pnl: (j['pnl'] as num? ?? 0).toDouble(),
        pnlPct: (j['pnl_pct'] as num? ?? 0).toDouble(),
      );
}

class Balance {
  final double deposit;
  final double evalTotal;
  final double pnlTotal;
  final List<Holding> holdings;
  Balance({
    required this.deposit,
    required this.evalTotal,
    required this.pnlTotal,
    required this.holdings,
  });
  factory Balance.fromJson(Map<String, dynamic> j) => Balance(
        deposit: (j['deposit'] as num? ?? 0).toDouble(),
        evalTotal: (j['eval_total'] as num? ?? 0).toDouble(),
        pnlTotal: (j['pnl_total'] as num? ?? 0).toDouble(),
        holdings: (j['holdings'] as List? ?? [])
            .map((e) => Holding.fromJson(e))
            .toList(),
      );
}

class OrderResult {
  final bool success;
  final String? orderNo;
  final String msgCd;
  final String msg;
  OrderResult({
    required this.success,
    this.orderNo,
    this.msgCd = '',
    this.msg = '',
  });
  factory OrderResult.fromJson(Map<String, dynamic> j) => OrderResult(
        success: j['success'] as bool? ?? false,
        orderNo: j['order_no'] as String?,
        msgCd: j['msg_cd'] as String? ?? '',
        msg: j['msg'] as String? ?? '',
      );
}

class AnalysisResult {
  final String ticker;
  final String tradeDate;
  final String signal;
  final String finalDecision;
  final String marketReport;
  final String newsReport;
  final String fundamentalsReport;
  final String sentimentReport;
  final String investmentPlan;
  final String traderPlan;

  AnalysisResult({
    required this.ticker,
    required this.tradeDate,
    required this.signal,
    required this.finalDecision,
    this.marketReport = '',
    this.newsReport = '',
    this.fundamentalsReport = '',
    this.sentimentReport = '',
    this.investmentPlan = '',
    this.traderPlan = '',
  });

  factory AnalysisResult.fromJson(Map<String, dynamic> j) => AnalysisResult(
        ticker: j['ticker'] as String,
        tradeDate: j['trade_date'] as String,
        signal: j['signal'] as String? ?? '',
        finalDecision: j['final_decision'] as String? ?? '',
        marketReport: j['market_report'] as String? ?? '',
        newsReport: j['news_report'] as String? ?? '',
        fundamentalsReport: j['fundamentals_report'] as String? ?? '',
        sentimentReport: j['sentiment_report'] as String? ?? '',
        investmentPlan: j['investment_plan'] as String? ?? '',
        traderPlan: j['trader_plan'] as String? ?? '',
      );
}
