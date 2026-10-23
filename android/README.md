# 打包成安卓 APK

这个目录是一个最小的 **WebView 壳**，把 `build_web/build/web` 的网页版装进 APK，
安装后点图标即可全屏横屏玩，存档在 App 内部（localStorage）。

当前工程已经配置好正式签名，推荐优先产出 **release APK** 给手机安装。

## 方式一：GitHub Actions（不用装 Android Studio，几分钟出包）

1. 把整个项目推到 GitHub：
   ```bash
   git init && git add . && git commit -m "解密·四界征战"
   git remote add origin https://github.com/<你的账号>/<仓库>.git
   git push -u origin main
   ```
2. 打开仓库的 **Actions** → 选 **build-apk** → **Run workflow**
3. 等 3~5 分钟，进入这次运行，下载 **解密四界征战-apk**（里面是 `app-release.apk`）
4. 传到手机安装（需允许「安装未知来源应用」）

## 方式二：本地 Android Studio

1. Android Studio → Open → 选择本目录 `android/`
2. 等 Gradle 同步完成（需要联网下载依赖）
3. 菜单 **Build → Build App Bundle(s) / APK(s) → Build APK(s)**
4. 产物：`android/app/build/outputs/apk/release/app-release.apk`

## 方式三：命令行（需要 JDK 17 + Android SDK）

```bash
cd android
gradle assembleRelease
```

## 说明

- 游戏文件在 `app/src/main/assets/www/`，重新打包网页版后需要同步一次：
  ```bash
  ./build_web.sh
  rm -rf android/app/src/main/assets/www/*
  cp build_web/build/web/* android/app/src/main/assets/www/
  ```
- 用 `WebViewAssetLoader` 以 `https://appassets.androidplatform.net` 提供本地文件，
  localStorage、fetch wasm 都能正常工作。
- 当前 APK 已内置运行时资源，安装后可离线启动。
- 图标：`res/mipmap-*/ic_launcher.png`，512 尺寸在 `android/icon-512.png`。
- 若手机里装过旧包，升级时要保持同一个 keystore；否则先卸载旧版再装新版。
- 若在微信、QQ 等内置浏览器里点 APK 没反应，改用系统浏览器或 Chrome 下载。
