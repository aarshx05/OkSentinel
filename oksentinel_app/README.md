# OkSentinel Mobile App

Flutter Android app for secure file sharing via OkSentinel backend.

## Features

✅ **Authentication** - Login/Register with PIN-based security
✅ **Dashboard** - View received files with stats
✅ **Send Files** - Encrypt and send files to other users
✅ **File Viewing** - Progressive streaming for images and videos
✅ **Users List** - Browse all available recipients
✅ **Settings** - Configure server URL for local WiFi

## Requirements

- Flutter SDK (3.0.0 or higher)
- Android device or emulator
- OkSentinel backend server running on your network

## Setup Instructions

### 1. Install Dependencies

```bash
cd oksentinel_app
flutter pub get
```

### 2. Start the Backend Server

In a separate terminal, start the mobile API server:

```bash
cd ..
python webapp/api_server.py
```

The server will start on `http://0.0.0.0:5000`.

### 3. Find Your Server IP Address

**On Windows:**
```powershell
ipconfig
```

Look for "IPv4 Address" under your WiFi adapter (e.g., `192.168.1.100`).

**On Mac/Linux:**
```bash
ifconfig
```

Look for your local IP address.

### 4. Configure the App

**Option A: Using the App**
1. Launch the app
2. Tap "Server Settings" on the login screen
3. Enter your server URL: `http://YOUR_IP:5000/api`
4. Tap "Test Connection" to verify
5. Tap "Save"

**Option B: Edit Code**
Edit `lib/services/api_service.dart` and change the default URL:

```dart
String _baseUrl = 'http://192.168.1.100:5000/api'; // Your server IP
```

### 5. Run the App

**On Android Device (via USB):**
```bash
flutter run
```

**On Android Emulator:**
```bash
# Start emulator first, then:
flutter run
```

> **Note:** If using Android emulator, use `http://10.0.2.2:5000/api` as the server URL (this maps to localhost on your computer).

## Usage Guide

### First Time Setup

1. **Create Account**
   - Enter a username
   - Create a 4-8 digit PIN
   - Tap "Login / Register"

2. **Configure Server**
   - Go to Settings
   - Enter your laptop's local IP address
   - Test connection

### Sending Files

1. Tap the "Send File" button (floating action button)
2. Select a file from your device
3. Choose a recipient
4. Set expiration time (1 hour to 1 week)
5. Tap "Send Encrypted File"

### Viewing Files

1. From the dashboard, tap any received file
2. Images display with pinch-to-zoom
3. Videos play with controls for play/pause and seeking
4. All streaming happens progressively (no full download required)

## Architecture

```
oksentinel_app/
├── lib/
│   ├── main.dart                 # App entry point
│   ├── models/
│   │   └── models.dart           # Data models  
│   ├── services/
│   │   ├── api_service.dart      # HTTP client
│   │   └── auth_provider.dart    # State management
│   ├── screens/
│   │   ├── login_screen.dart
│   │   ├── dashboard_screen.dart
│   │   ├── send_file_screen.dart
│   │   ├── file_viewer_screen.dart
│   │   ├── users_screen.dart
│   │   └── settings_screen.dart
│   └── widgets/                  # Reusable widgets
└── pubspec.yaml                  # Dependencies
```

## WiFi Network Requirements

- Both your laptop (server) and Android device must be on the **same WiFi network**
- Firewall on your laptop should allow incoming connections on port 5000
- Some corporate/university networks may block peer-to-peer connections

### Testing Connection

Use the built-in connection tester in Settings:
1. Go to Settings screen
2. Enter server URL
3. Tap "Test Connection"
4. You should see "Connected successfully!"

## Troubleshooting

### "Connection failed" in settings
- Verify your laptop and phone are on the same WiFi
- Check that the backend server is running (`python webapp/api_server.py`)
- Verify the IP address is correct
- Try disabling firewall temporarily

### "Network error" when logging in
- Check server URL in settings
- Ensure backend server is running
- Verify port 5000 is accessible

### Video won't play
- Check video format (MP4, WebM supported)
- Ensure file was encrypted correctly
- Try smaller video files first

### Images don't load
- Verify internet permission in AndroidManifest.xml
- Check server logs for errors
- Ensure chunks are decrypting correctly

## Security Features

🔒 **End-to-End Encryption** - RSA-4096 + AES-256-CTR
🔒 **Zero-Leak Architecture** - Decrypted content only in memory
🔒 **PIN-Based Authentication** - Secure user verification
🔒 **Automatic Expiry** - Time-bound file access
🔒 **Chunk Integrity** - Hash verification per chunk

## Known Limitations

- PDF viewing in external app only (in-app viewer coming soon)
- No background download support yet
- Maximum file size: 500MB
- Requires active WiFi connection

## Future Enhancements

- [ ] Push notifications for new files
- [ ] In-app PDF viewer
- [ ] File download for offline access
- [ ] Dark mode toggle
- [ ] biometric authentication
- [ ] Cloud deployment support

## License

Copyright © 2026 OkynusTech. All rights reserved.

## Support

For issues or questions, contact the OkSentinel team.
