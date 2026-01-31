@echo off
echo ========================================
echo   OkSentinel APK Builder
echo ========================================
echo.

cd /d "%~dp0"

echo [1/3] Installing dependencies...
call flutter pub get
if errorlevel 1 (
    echo Error: Failed to get dependencies
    echo Make sure Flutter is installed and in PATH
    pause
    exit /b 1
)

echo.
echo [2/3] Building release APK...
call flutter build apk --release
if errorlevel 1 (
    echo Error: Build failed
    echo Check the error messages above
    pause
    exit /b 1
)

echo.
echo [3/3] Build successful!
echo ========================================
echo.
echo APK created at:
echo %cd%\build\app\outputs\flutter-apk\app-release.apk
echo.
echo File size:
for %%A in (build\app\outputs\flutter-apk\app-release.apk) do echo %%~zA bytes (%%~zAKB)
echo.
echo Next steps:
echo 1. Copy this APK to your phone
echo 2. Enable "Install from unknown sources"
echo 3. Tap the APK to install
echo.
echo ========================================
pause
