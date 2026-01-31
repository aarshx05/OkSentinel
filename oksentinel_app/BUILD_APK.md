# Building OkSentinel APK for Android

## Option 1: Build APK with Flutter (Recommended)

### Step 1: Install Flutter

**Download Flutter SDK:**
1. Visit [flutter.dev/docs/get-started/install/windows](https://flutter.dev/docs/get-started/install/windows)
2. Download the latest Flutter SDK for Windows
3. Extract to `C:\src\flutter` (or your preferred location)

**Add Flutter to PATH:**
```powershell
# Run as Administrator
$env:Path += ";C:\src\flutter\bin"
[Environment]::SetEnvironmentVariable("Path", $env:Path, [EnvironmentVariableTarget]::User)
```

**Verify Installation:**
```powershell
flutter doctor
```

This will check for required dependencies (Android SDK, etc.).

### Step 2: Build the APK

Navigate to the app directory and build:

```powershell
cd "c:\Users\Aarsh\Documents\Aarsh - Personal\OkSentinel\oksentinel_app"

# Install dependencies
flutter pub get

# Build APK (release mode)
flutter build apk --release
```

**Build Output:**
The APK will be created at:
```
oksentinel_app\build\app\outputs\flutter-apk\app-release.apk
```

### Step 3: Install on Your Phone

**Option A: USB Transfer**
1. Connect phone via USB
2. Copy APK to phone's Downloads folder
3. On phone: Open Files app → Downloads → tap APK
4. Allow "Install from unknown sources" if prompted
5. Tap "Install"

**Option B: ADB Install (Fastest)**
```powershell
# Enable USB debugging on phone first
adb install build\app\outputs\flutter-apk\app-release.apk
```

---

## Option 2: Quick Build Script (If Flutter is Installed)

Save this as `build_apk.bat` in the `oksentinel_app` folder:

```batch
@echo off
echo Building OkSentinel APK...
echo.

cd /d "%~dp0"

echo [1/3] Getting dependencies...
call flutter pub get

echo.
echo [2/3] Building release APK...
call flutter build apk --release

echo.
echo [3/3] Done!
echo.
echo APK Location:
echo %cd%\build\app\outputs\flutter-apk\app-release.apk
echo.
echo Transfer this file to your phone and install it.
pause
```

Then just run:
```powershell
.\build_apk.bat
```

---

## Option 3: Build Directly from Android Studio (GUI Method)

1. **Install Android Studio** (if not installed)
2. Open Android Studio
3. Open the project: `oksentinel_app` folder
4. Wait for Gradle sync to complete
5. Go to **Build** → **Build Bundle(s) / APK(s)** → **Build APK(s)**
6. APK will be in `app/build/outputs/apk/release/`

---

## Alternative: Build APK Without Flutter Locally

If you don't want to install Flutter on your laptop, you can use:

### **GitHub Actions** (Free CI/CD)

I can create a GitHub Actions workflow that automatically builds the APK when you push to GitHub. The APK will be available as a downloadable artifact.

Would you like me to set that up?

---

## APK Size & Compatibility

- **Expected APK size:** ~40-60 MB (release build)
- **Minimum Android version:** Android 5.0 (API 21)
- **Target Android version:** Android 14 (API 34)

---

## Quick Start (TL;DR)

If you have Flutter installed:
```powershell
cd oksentinel_app
flutter pub get
flutter build apk --release
```

APK will be at: `build\app\outputs\flutter-apk\app-release.apk`

Transfer to phone and install! 📱

---

## Troubleshooting

**"Flutter command not found"**
- Flutter is not installed or not in PATH
- Follow Option 1 above to install Flutter

**"Gradle build failed"**
- Ensure Android SDK is installed
- Run `flutter doctor` to check dependencies

**"App not installed" on phone**
- Enable "Install from unknown sources" in phone settings
- Check if you have enough storage space
- Try uninstalling any previous version first

**Build takes too long**
- First build can take 5-10 minutes
- Subsequent builds are much faster (~1-2 minutes)

---

## Need Help?

If you encounter any issues or want me to create a GitHub Actions workflow for automated builds, let me know!
