#!/usr/bin/env bash
# 把最新网页包同步进安卓工程
set -e
cd "$(dirname "$0")"
[ -d build_web/build/web ] || ./build_web.sh
rm -rf android/app/src/main/assets/www
mkdir -p android/app/src/main/assets/www
cp -R build_web/build/web/. android/app/src/main/assets/www/
echo "已同步 $(du -sh android/app/src/main/assets/www | cut -f1) 到 android/app/src/main/assets/www"
