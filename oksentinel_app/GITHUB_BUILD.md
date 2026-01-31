# GitHub Actions - Automated APK Build

## What This Does

Automatically builds your OkSentinel APK in the cloud using GitHub Actions - **no local Flutter installation needed!**

## Setup Steps

### 1. Create a GitHub Repository

If you haven't already:

```powershell
cd "c:\Users\Aarsh\Documents\Aarsh - Personal\OkSentinel"

# Initialize git repo (if not already done)
git init

# Add all files
git add .
git commit -m "Initial commit: OkSentinel Flutter app"

# Create repo on GitHub.com, then:
git remote add origin https://github.com/YOUR_USERNAME/OkSentinel.git
git branch -M main
git push -u origin main
```

### 2. Trigger the Build

The workflow runs automatically when you:
- Push to `main` or `master` branch
- Create a pull request

**Or manually trigger it:**
1. Go to your GitHub repo
2. Click **Actions** tab
3. Select **Build Android APK** workflow
4. Click **Run workflow**

### 3. Download the APK

Once the build completes (~5 minutes):

1. Go to the **Actions** tab on GitHub
2. Click on the latest workflow run
3. Scroll down to **Artifacts**
4. Download `oksentinel-app-release` (ZIP file)
5. Extract the ZIP to get `app-release.apk`
6. Transfer to your phone and install!

## Build Status

After setting up, you'll see a badge showing build status:

![Build Status](https://github.com/YOUR_USERNAME/OkSentinel/workflows/Build%20Android%20APK/badge.svg)

## What Gets Built

- **Release APK** - Optimized for production
- **File size** - ~40-60 MB
- **Min Android** - Android 5.0 (API 21)
- **Target Android** - Android 14 (API 34)

## Troubleshooting

**Build fails on GitHub:**
- Check the Actions log for errors
- Ensure `pubspec.yaml` has correct dependencies
- Verify `android/app/build.gradle` is properly configured

**Can't find Actions tab:**
- Make sure the repository is public or you have GitHub Actions enabled
- Check if `.github/workflows/build-android.yml` was pushed

**APK not in artifacts:**
- Wait for the build to complete (green checkmark)
- Artifacts expire after 30 days (configurable)

## Alternative: Local Build

If you prefer to install Flutter locally:

1. Download Flutter: https://flutter.dev/docs/get-started/install/windows
2. Extract to `C:\src\flutter`
3. Add to PATH
4. Run `flutter pub get` and `flutter build apk --release`

## Benefits of GitHub Actions

✅ No local Flutter installation needed
✅ Consistent build environment
✅ Automatic builds on every commit
✅ APK available for download anytime
✅ Free for public repositories

## Next Steps

1. Push your code to GitHub
2. Wait for the build to complete
3. Download the APK
4. Install on your phone
5. Configure server settings and start using!
