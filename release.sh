#!/usr/bin/env bash
# 把 dist/treasure-game.apk 发布（或更新）到 GitHub Release
# 用法：./release.sh v1.2 "这次改了什么"
set -e
cd "$(dirname "$0")"

TAG="${1:-v$(date +%m%d)}"
NOTE="${2:-自动构建的离线 APK}"
APK="dist/treasure-game.apk"
[ -f "$APK" ] || { echo "缺少 $APK，先运行 ./build_web.sh 并打好 APK"; exit 1; }

TOKEN="${GH_TOKEN:-}"
if [ -z "$TOKEN" ] && [ -f "$HOME/.git-credentials" ]; then
  TOKEN=$(sed -n 's#https://[^:]*:\([^@]*\)@github\.com#\1#p' "$HOME/.git-credentials" | head -1)
fi
[ -n "$TOKEN" ] || { echo "缺少 GitHub token：设置 GH_TOKEN 或登录过 git 凭据"; exit 1; }

REMOTE=$(git remote get-url origin)
REPO=$(echo "$REMOTE" | sed -E 's#.*github\.com[:/]([^/]+/[^/.]+)(\.git)?#\1#')
echo "==> 仓库 $REPO，版本 $TAG"

RELEASE_ID=$(curl -s -H "Authorization: token $TOKEN" \
  "https://api.github.com/repos/$REPO/releases/tags/$TAG" | python3 -c "import json,sys;print(json.load(sys.stdin).get('id',''))")

if [ -z "$RELEASE_ID" ]; then
  RELEASE_ID=$(curl -s -X POST -H "Authorization: token $TOKEN" \
    -H "Content-Type: application/json" \
    -d "{\"tag_name\":\"$TAG\",\"name\":\"解密·四界征战 $TAG\",\"body\":\"$NOTE\"}" \
    "https://api.github.com/repos/$REPO/releases" | python3 -c "import json,sys;print(json.load(sys.stdin)['id'])")
  echo "==> 已创建 Release $TAG"
fi

curl -s -X DELETE -H "Authorization: token $TOKEN" \
  "https://api.github.com/repos/$REPO/releases/assets/$(curl -s -H "Authorization: token $TOKEN" \
  "https://api.github.com/repos/$REPO/releases/$RELEASE_ID/assets" | python3 -c "
import json,sys
for a in json.load(sys.stdin):
    if a['name']=='treasure-game.apk': print(a['id']); break
")" >/dev/null 2>&1 || true

URL=$(curl -s -X POST -H "Authorization: token $TOKEN" \
  -H "Content-Type: application/vnd.android.package-archive" \
  --data-binary @"$APK" \
  "https://uploads.github.com/repos/$REPO/releases/$RELEASE_ID/assets?name=treasure-game.apk" \
  | python3 -c "import json,sys;print(json.load(sys.stdin).get('browser_download_url',''))")

echo "==> 完成：https://github.com/$REPO/releases/tag/$TAG"
echo "==> 直链：$URL"
