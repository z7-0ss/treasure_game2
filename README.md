# 解密·四界征战

一款用 Python + pygame-ce 写的横版冒险游戏：4 大关卡 × 4 小关，森林 / 海底 / 天空 / 火山四套主题，
Boss 数量逐关增加，跟宠、装备套装、神话隐藏属性、多存档、天气与负面状态一应俱全。

## 电脑上运行

```bash
pip install pygame-ce numpy
python main.py
```

操作：`WASD/方向键` 移动，`J` 攻击，`K/L/U` 技能，`Space` 跳跃，`1-4` 道具，`I` 角色，`M` 地图，`P` 跟宠，`F11` 全屏。

## 手机上玩（安卓）

**直接下载安装包**：打开仓库的 [Releases](../../releases) 页面，下载最新的 `app-release.apk`。

APK 已内置完整运行环境（Python / pygame / 终端资源），**完全离线**，首次启动约 30~60 秒。

## 打包 APK

```bash
./build_web.sh            # 1. 把游戏打成网页包（pygbag）
./sync_android_assets.sh  # 2. 同步进 Android 工程
cd android && gradle assembleRelease
# 产物：android/app/build/outputs/apk/release/app-release.apk
```

Android 工程在 `android/`（WebView 壳），也可以用 Android Studio 打开直接 Build。

## 发布新版本（两种方式）

### 方式一：打 tag，GitHub Actions 自动出包

```bash
git add -A && git commit -m "更新说明" && git push
git tag v1.3 && git push origin v1.3
```

推送 tag 后，Actions 会自动构建 APK 并挂到对应的 Release，手机上直接下载。

### 方式二：本地出包后一键发布

```bash
./build_web.sh && ./sync_android_assets.sh
cd android && gradle assembleRelease && cd ..
cp android/app/build/outputs/apk/release/app-release.apk dist/treasure-game.apk
./release.sh v1.3 "更新说明"
```

`release.sh` 会自动创建/更新 Release 并上传 APK，最后打印下载直链。

## 目录

| 路径 | 说明 |
|---|---|
| `main.py` | 入口：菜单、存档、角色面板、循环 |
| `entities.py` | 玩家、敌人、Boss、跟宠、特效 |
| `level.py` | 地图生成、关卡逻辑、掉落、Boss 技能 |
| `art.py` | 像素美术（全部代码绘制）与字体 |
| `audio.py` | 代码合成的 7 段 BGM + 21 种音效 |
| `settings.py` | 全部数值与配置 |
| `save.py` | 3 个角色存档槽 + 偏好设置 |
| `android/` | WebView 安卓工程（含签名密钥） |
| `runtime/` `web_extra/` | 离线网页运行环境（打包用） |

## 说明

- 存档：桌面写 `savegame.json` / `prefs.json`，网页版写浏览器 localStorage
- 签名密钥在 `android/keystore/`，升级请沿用同一个密钥，否则需要先卸载旧版
