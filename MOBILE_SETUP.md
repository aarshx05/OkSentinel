# OkSentinel Mobile API - Quick Start Guide

## Starting the Mobile Backend Server

The mobile app requires a special API server with CORS support. Follow these steps:

### 1. Install Dependencies (First Time Only)

```powershell
pip install flask-cors
```

### 2. Start the Mobile API Server

```powershell
python webapp\api_server.py
```

You should see:
```
🔐 OkSentinel Mobile API Server
==================================================
Starting server at: http://0.0.0.0:5000
API endpoints available at: /api/*
Press Ctrl+C to stop
==================================================
```

### 3. Find Your Local IP Address

Run this command:
```powershell
ipconfig
```

Look for "IPv4 Address" under your active WiFi adapter. It will look like:
```
IPv4 Address. . . . . . . . . . . : 192.168.1.100
```

### 4. Configure the Mobile App

On your Android device:
1. Open OkSentinel app
2. Tap "Server Settings" on login screen
3. Enter: `http://192.168.1.100:5000/api` (use your actual IP)
4. Tap "Test Connection"
5. If successful, tap "Save"

## Troubleshooting

**Cannot connect from phone:**
- Ensure both devices are on the same WiFi network
- Check Windows Firewall settings
- Try temporarily disabling firewall to test

**Allow through Windows Firewall:**
```powershell
netsh advfirewall firewall add rule name="OkSentinel API" dir=in action=allow protocol=TCP localport=5000
```

**Check if server is running:**
Open browser on your laptop and visit:
```
http://localhost:5000/api/health
```

You should see: `{"status":"healthy","version":"1.0.0","timestamp":...}`

## API Endpoints

- `POST /api/auth/login` - Login/Register
- `GET /api/dashboard` - Get files and stats
- `GET /api/users` - List all users
- `POST /api/send` - Send encrypted file
- `GET /api/stream/<file_id>` - Stream file with range support

## Notes

- Server must be running whenever you want to use the mobile app
- Both laptop and phone must be on same WiFi network
- For public internet access, consider using ngrok or Cloudflare Tunnel (advanced)
