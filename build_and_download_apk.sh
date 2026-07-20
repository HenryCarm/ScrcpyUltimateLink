#!/usr/bin/env bash
# Run these commands to trigger APK build and download to Desktop

# 1. Commit and push cross-platform + thedjchi Shizuku fork updates
cd /home/henry/Documents/Projects/Python/ScrcpyUltimateLink
git add .
git commit -m "feat: cross-platform support and thedjchi shizuku fork compatibility"
git push origin master

# 2. Wait for GitHub Actions to complete (check at https://github.com/HenryCarm/ScrcpyUltimateLink/actions)
# 3. Download the APK artifact directly to Desktop
gh run download --name scrcpy-heartbeat-apk --dir ~/Desktop/ScrcpyAPK/

# Or if you know the run ID:
# gh run download <RUN_ID> --name scrcpy-heartbeat-apk --dir ~/Desktop/ScrcpyAPK/