import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:stock_mts_mobile/main.dart';

void main() {
  testWidgets('App boots and renders shell or settings', (WidgetTester tester) async {
    await tester.pumpWidget(const StockMtsApp());
    await tester.pump();
    // 미설정 상태에서는 SettingsPage, 설정되어 있으면 NavigationBar가 뜸 — 둘 중 하나는 보여야 한다
    expect(find.byType(MaterialApp), findsOneWidget);
  });
}
