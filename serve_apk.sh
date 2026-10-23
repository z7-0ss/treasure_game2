#!/usr/bin/env bash
# 本地起一个 APK 下载页，方便安卓手机在同一 WiFi 下直接下载
cd "$(dirname "$0")"
PORT="${1:-8899}"
IP=$(ipconfig getifaddr en0 2>/dev/null || hostname -I 2>/dev/null | awk '{print $1}')
echo "电脑：  http://127.0.0.1:$PORT"
[ -n "$IP" ] && echo "手机：  http://$IP:$PORT  （需同一 WiFi，建议用系统浏览器打开）"
python3 serve_apk.py "$PORT"
