import 'package:flutter_test/flutter_test.dart';
import 'package:flutter/material.dart';
import 'package:camera/camera.dart';
import 'package:frontend/main.dart';

void main() {
  testWidgets('App loads correctly', (WidgetTester tester) async {
    final List<CameraDescription> cameras = []; // Mock camera list

    await tester.pumpWidget(MyApp(cameras: cameras)); // ✅ Pass mock cameras

    expect(find.text('Capture'), findsOneWidget);
  });
}
