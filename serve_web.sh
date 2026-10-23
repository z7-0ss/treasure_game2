#!/usr/bin/env bash
# 本地起一个服务器，方便手机在同一个 WiFi 下测试
cd "$(dirname "$0")"
PORT="${1:-8000}"
IP=$(ipconfig getifaddr en0 2>/dev/null || hostname -I 2>/dev/null | awk '{print $1}')
echo "电脑：  http://127.0.0.1:$PORT"
[ -n "$IP" ] && echo "手机：  http://$IP:$PORT  （需同一 WiFi）"
python3 -m http.server "$PORT" -d build_web/build/web
