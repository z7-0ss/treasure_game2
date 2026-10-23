#!/usr/bin/env bash
# 一键打网页包（手机浏览器可玩）
set -e
cd "$(dirname "$0")"

echo "==> 准备打包环境"
if [ ! -x .venv_web/bin/python ]; then
  python3 -m venv .venv_web
  .venv_web/bin/python -m pip install --quiet --upgrade pip
  .venv_web/bin/python -m pip install --quiet pygbag fonttools
fi

echo "==> 收集运行文件"
rm -rf build_web
mkdir -p build_web/assets
cp main.py art.py audio.py entities.py level.py settings.py save.py build_web/
cp assets/font.ttf build_web/assets/
[ -f preview/scene_title.png ] && cp preview/scene_title.png build_web/favicon.png || true

echo "==> 打包（pygbag）"
.venv_web/bin/python -m pygbag --build build_web

echo "==> 修正页面（标题 / 本地运行时 / 归档方式）"
python3 - <<'PY'
import pathlib
p = pathlib.Path("build_web/build/web/index.html")
t = p.read_text(encoding="utf-8")
t = t.replace("<title>build_web</title>", "<title>解密·四界征战</title>")
# 保持原始的 tar.gz 归档分支不动
# 运行时改成本地文件（离线包）
t = t.replace("https://pygame-web.github.io/cdn/0.9.3/", "./runtime/")
t = t.replace("./runtime//", "./runtime/")
# 自动开始，不等点击
t = t.replace("    ume_block : 1,", "    ume_block : 0,")
# 把运行时里所有对 CDN 的请求重定向到本地
SHIM = open("web_extra/cdn_shim.html", encoding="utf-8").read()
if "cdn_shim" not in t:
    t = t.replace('<html lang="en-us">', '<html lang="en-us">\n' + SHIM, 1)
t = t.replace('<html lang="en-us">', '<html lang="en-us"> <!-- cdn_shim -->', 1)
# Android WebView 上解 tar.gz 更容易卡住，统一改成读取 build_web.apk(zip)。
t = t.replace(
"""    if platform.window.location.host.find('.itch.zone')>0:
        import zipfile
        async with platform.fopen("build_web.apk", "rb") as archive:
            with zipfile.ZipFile(archive) as zip_ref:
                zip_ref.extractall(appdir.as_posix())
    else:
        import tarfile
        async with platform.fopen("build_web.tar.gz", "rb") as archive:
            tar = tarfile.open(fileobj=archive, mode="r:gz")
            tar.extractall(path=appdir.as_posix(), filter='tar')
            tar.close()
""",
"""    import zipfile
    async with platform.fopen("build_web.apk", "rb") as archive:
        with zipfile.ZipFile(archive) as zip_ref:
            zip_ref.extractall(appdir.as_posix())
""")
# 启动完成后打标记，避免误报“启动超时”。
t = t.replace(
"""    platform.window.infobox.style.display = "none"
    platform.window.config.gui_divider = 1
""",
"""    platform.window.infobox.style.display = "none"
    platform.window.__bootDone = true
    platform.window.config.gui_divider = 1
""")
p.write_text(t, encoding="utf-8")
print("cdn refs left:", t.count("pygame-web.github.io"))
PY

echo "==> 复制本地运行时"
rm -rf build_web/build/web/runtime
cp -R runtime build_web/build/web/runtime
# xterm 终端资源（vtx.js / vt/），离线也要
[ -d web_extra ] && cp -R web_extra/. build_web/build/web/
rm -f build_web/build/web/cdn_shim.html

echo "==> 压缩成可上传的 zip"
rm -f "解密四界征战_web.zip"
( cd build_web/build/web && zip -qr "../../../解密四界征战_web.zip" . )

echo
echo "完成：build_web/build/web"
echo "本地试玩：  python3 -m http.server 8000 -d build_web/build/web"
echo "手机访问：  http://<电脑局域网IP>:8000"
echo "上传部署：  把 build_web/build/web 里的文件传到任意静态托管"
