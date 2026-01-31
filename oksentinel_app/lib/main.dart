import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'services/auth_provider.dart';
import 'screens/login_screen.dart';
import 'screens/dashboard_screen.dart';
import 'screens/send_file_screen.dart';
import 'screens/file_viewer_screen.dart';
import 'screens/users_screen.dart';
import 'screens/settings_screen.dart';
import 'models/models.dart';

void main() {
  runApp(const OkSentinelApp());
}

class OkSentinelApp extends StatelessWidget {
  const OkSentinelApp({super.key});

  @override
  Widget build(BuildContext context) {
    return ChangeNotifierProvider(
      create: (_) => AuthProvider(),
      child: MaterialApp(
        title: 'OkSentinel',
        debugShowCheckedModeBanner: false,
        theme: ThemeData(
          colorScheme: ColorScheme.fromSeed(
            seedColor: Colors.blue,
            brightness: Brightness.light,
          ),
          useMaterial3: true,
          cardTheme: CardTheme(
            elevation: 2,
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(12),
            ),
          ),
          elevatedButtonTheme: ElevatedButtonThemeData(
            style: ElevatedButton.styleFrom(
              elevation: 2,
              padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
            ),
          ),
        ),
        darkTheme: ThemeData(
          colorScheme: ColorScheme.fromSeed(
            seedColor: Colors.blue,
            brightness: Brightness.dark,
          ),
          useMaterial3: true,
          cardTheme: CardTheme(
            elevation: 2,
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(12),
            ),
          ),
        ),
        themeMode: ThemeMode.system,
        initialRoute: '/login',
        onGenerateRoute: (settings) {
          switch (settings.name) {
            case '/login':
              return MaterialPageRoute(
                builder: (_) => const LoginScreen(),
              );
            case '/dashboard':
              return MaterialPageRoute(
                builder: (_) => const DashboardScreen(),
              );
            case '/send':
              return MaterialPageRoute(
                builder: (_) => const SendFileScreen(),
              );
            case '/view':
              final file = settings.arguments as AssetFile;
              return MaterialPageRoute(
                builder: (_) => FileViewerScreen(file: file),
              );
            case '/users':
              return MaterialPageRoute(
                builder: (_) => const UsersScreen(),
              );
            case '/settings':
              return MaterialPageRoute(
                builder: (_) => const SettingsScreen(),
              );
            default:
              return MaterialPageRoute(
                builder: (_) => const LoginScreen(),
              );
          }
        },
      ),
    );
  }
}
