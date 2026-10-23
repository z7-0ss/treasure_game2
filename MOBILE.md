# 手机上玩《解密·四界征战》

## 已经打好的安装包（推荐）

**`解密四界征战.apk`（12MB，正式签名，完整离线：Python 运行时 + pygame + 终端资源全部内置）** —— 直接传到手机安装即可：

1. 把 APK 发到手机（微信文件传输 / 数据线 / 网盘）
2. 手机上点开，允许「安装未知来源应用」
3. 桌面出现游戏图标，点开即玩（横屏全屏）

> 完整离线：Python 解释器、pygame wasm 轮子、终端资源全部在 APK 内，**任何网络环境下都能启动**。
> 首次打开需要 20~60 秒（解压 + 安装 pygame），之后每次 5~15 秒；期间屏幕会显示 Loading，属正常。
> 存档在 App 内部，卸载才会清空。
>
> **正式签名**：APK 用 `android/keystore/treasure.jks` 签名（密码 `treasure2024`，别名 `treasure`）。
> 以后升级版本请务必用同一个 keystore，否则手机会要求先卸载旧版（存档会丢）。

### 手机上直接下载 APK

如果你想让安卓手机在同一 WiFi 下直接下载安装包，不用先发微信/网盘：

```bash
./serve_apk.sh          # 默认 8899 端口
```

脚本会打印两个地址：
- 电脑：`http://127.0.0.1:8899`
- 手机：`http://<电脑局域网IP>:8899`

手机用 **系统浏览器或 Chrome** 打开第二个地址，点「下载 APK」即可。

> 微信、QQ 这类内置浏览器经常会拦截或不响应 APK 下载按钮，遇到这种情况请点右上角改用系统浏览器打开。
> 如果已经下载完成但安装失败，去手机设置里给当前浏览器打开「安装未知应用」权限。
> 该 APK 最低要求 **Android 6.0**（`minSdk 23`）。

网页版也一并打好了：**`build_web/build/web/`**，压缩包 **`解密四界征战_web.zip`**。

---

## 一、网页版：同一 WiFi 下用手机试玩

```bash
./serve_web.sh          # 默认 8000 端口
```

脚本会打印两个地址：
- 电脑：`http://127.0.0.1:8000`
- 手机：`http://<电脑局域网IP>:8000`（手机和电脑连同一个 WiFi）

手机浏览器打开第二个地址 → 点一下画面激活声音 → **横屏**玩。

> 首次加载要下载 WebAssembly 版 Python（约 10~20 秒），之后浏览器会缓存。

---

## 二、正式发布：传到静态托管

把 `build_web/build/web/` 里的**全部文件**上传即可（Vercel / Netlify / GitHub Pages / 自己的 Nginx）：

- Netlify：把 `解密四界征战_web.zip` 直接拖进 netlify.com 的部署框
- GitHub Pages：把 web 目录内容推到 `gh-pages` 分支
- 自己的服务器：`scp build_web/build/web/* user@host:/var/www/game/`

必须是 **HTTPS**（或 localhost），否则浏览器不会启用部分能力。

---

## 三、重新打包

```bash
./build_web.sh
```
会自动：建虚拟环境 → 装 pygbag → 收集运行文件 → 打网页包 → 生成 `解密四界征战_web.zip`。

需要联网（首次会下载 pygbag 和 Python 运行时模板）。

---

## 四、重新打 APK

`android/` 是一个 WebView 壳工程，已内置当前网页包。三种方式：

**A. GitHub Actions（不用装 Android Studio）**
1. 推到 GitHub → Actions → **build-apk** → Run workflow
2. 下载 `解密四界征战-apk` 里的 `app-release.apk`

**B. Android Studio**：打开 `android/` → Build → Build APK(s)

**C. 命令行（JDK 17 + Android SDK）**
```bash
cd android
gradle assembleRelease     # 正式签名包
# 产物：app/build/outputs/apk/release/app-release.apk
```

升级版本时改 `android/app/build.gradle` 里的 `versionCode`（+1）和 `versionName`。

**重新打包网页版后同步进 APK：**
```bash
./build_web.sh && ./sync_android_assets.sh
```

## 五、打包成 Android APK（用 buildozer，可选）

网页版已经能在 Android 浏览器玩；若想要安装包，用 buildozer（需要 Linux 或 macOS + Android SDK/NDK）：

```bash
pip install buildozer cython
buildozer init
# 编辑 buildozer.spec：
#   title = 解密·四界征战
#   package.name = treasuregame
#   requirements = python3,pygame-ce
#   orientation = landscape
#   fullscreen = 1
#   source.include_exts = py,png,ttf,json,md
buildozer -v android debug
```

`assets/font.ttf` 已经随包（中文不会变方块）。

---

## 五、操作

| 位置 | 功能 |
|---|---|
| 左下虚拟摇杆 | 拖动移动 |
| 右下「攻」 | 普通攻击 |
| 三个技能按钮（K/L/U） | 职业技能，独立冷却 |
| 「跳」 | 跳跃 / 二段跳 / 上平台 |
| 底部 4 格 | 药水、炸弹 |
| 右上「宠 / 图 / 包 / 菜单」 | 跟宠面板、地图、角色背包、返回菜单 |
| 角色页 | 点装备穿戴；开「丢弃模式」后点装备丢弃；鼠标悬停看属性（手机长按不支持） |

**支持多点触控**：左手推摇杆的同时右手可以攻击/放技能。

---

## 六、已做的移动端适配

- **画面**：逻辑分辨率 960×540，浏览器/手机等比缩放并留黑边，横竖屏都不变形
- **字体**：打包了 675KB 的中文字体 `assets/font.ttf`，网页和安卓都不会变方块
- **触摸**：`FINGER` 事件驱动摇杆与所有按钮，菜单/面板自动转成点击
- **存档**：网页版自动存浏览器 `localStorage`（3 个角色存档槽、音乐/音效开关都会记住）
- **音频**：浏览器要求先点击一次才允许播放；音频失败会自动静默，不影响游戏
- **全屏**：网页版用手机浏览器自带全屏；桌面按 F11
- **菜单「重新开始」**：网页版会刷新页面重新进入（桌面版是退出游戏）

---

## 七、常见问题

**手机上字是方块？** 说明 `assets/font.ttf` 没上传，检查该文件是否在 web 目录里。

**卡在加载页？** 首次要下载运行时，等 10~20 秒；确认网络能访问 `pygame-web.github.io`。

**没有声音？** 先点一下画面（浏览器策略），并确认手机没静音；菜单左下角会显示音频状态。

**存档会丢吗？** 网页版存在浏览器里，清缓存/换浏览器会丢；想长期保存建议固定用同一个浏览器。
