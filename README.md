# 剪切板管理器

macOS 菜单栏剪切板管理工具。自动记录文字和图片复制历史，支持搜索、置顶、删除，以卡片形式按时间降序展示。

## 功能

- 🔍 **实时监控** — 自动捕获文字和图片复制内容
- 🔎 **搜索过滤** — 快速查找历史记录
- 📌 **置顶管理** — 重要内容一键置顶
- 🗑️ **删除清理** — 支持单条删除和自动过期清理
- 🔒 **隐私保护** — 自动过滤密码类应用的复制内容
- 🖼️ **图片支持** — 文字和图片剪贴板内容都支持

## 安装与运行

```bash
# 1. 安装依赖
pip3 install --user -r requirements.txt

# 2. 启动
python3 clipboard_app.py
```

启动后在菜单栏会出现图标，点击即可打开管理面板。

## 打包为 .app

```bash
python3 setup.py py2app
```

生成的 `.app` 位于 `dist/` 目录，可直接拖入应用程序文件夹。

## 技术栈

| 技术 | 用途 |
|------|------|
| Python 3.9 | 主语言 |
| rumps 0.4 | 菜单栏应用框架 |
| PyObjC 10.3 | macOS 系统桥接 |
| WKWebView | 面板 UI 渲染 |
| JSON | 本地数据存储 |

## 目录结构

```
clipboard-manager/
├── clipboard_app.py       # 主程序入口
├── clipboard_monitor.py   # 剪贴板监控
├── storage.py             # 数据存储（JSON + 图片）
├── ui_panel.py            # NSWindow + WKWebView 面板
├── panel.html             # 面板界面（HTML/CSS/JS）
├── assets/icon.png        # 菜单栏图标
├── requirements.txt       # Python 依赖
├── setup.py               # py2app 打包配置
└── dev-logs/              # 开发日志
```

## 存储路径

```
~/Library/Application Support/ClipboardManager/
├── clips.json     # 元数据
├── settings.json  # 用户设置
└── images/        # 图片文件
```
