import 'package:flutter/material.dart';
import 'pages/shell.dart';

void main() {
  runApp(const StockMtsApp());
}

class StockMtsApp extends StatelessWidget {
  const StockMtsApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Stock MTS',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: Colors.indigo, brightness: Brightness.dark),
        useMaterial3: true,
      ),
      home: const HomeShell(),
    );
  }
}
