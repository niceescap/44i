import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';

import 'screens/home_screen.dart';
import 'theme.dart';

void main() => runApp(const RosaceApp());

class RosaceApp extends StatelessWidget {
  const RosaceApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      debugShowCheckedModeBanner: false,
      title: 'La Rosace',
      theme: rosaceTheme(),
      localizationsDelegates: const [
        GlobalMaterialLocalizations.delegate,
        GlobalWidgetsLocalizations.delegate,
        GlobalCupertinoLocalizations.delegate,
      ],
      supportedLocales: const [
        Locale('fr'),
        Locale('en'),
        Locale('es'),
        Locale('it'),
        Locale('de'),
        Locale('nl'),
        Locale('pt'),
        Locale('pl'),
        Locale('hu'),
        Locale('sr'),
        Locale('ru'),
        Locale('ar'),
        Locale('he'),
        Locale('zh'),
        Locale('th'),
        Locale('ja'),
        Locale('ko'),
        Locale('hi'),
        Locale('id'),
        Locale('tr'),
        Locale('vi'),
      ],
      home: const HomeScreen(),
    );
  }
}
