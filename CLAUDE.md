# CLAUDE.md — 剪切板历史管理器

## 项目概述

macOS 菜单栏剪切板管理工具。自动记录文字和图片复制历史，支持搜索、置顶、删除，以卡片形式按时间降序展示。

## 技术栈

- **框架**: Python 3.9 + rumps 0.4（菜单栏）+ PyObjC 10.3（系统桥接）
- **UI**: NSWindow + WKWebView 渲染 HTML/CSS 卡片界面
- **存储**: JSON 文件（`~/Library/Application Support/ClipboardManager/`）
- **打包**: py2app
- **平台**: macOS (arm64)

## 开发原则

1. **分阶段推进**：每阶段验证通过后再进入下一阶段
2. **小步提交**：每个功能点完成后立即验证
3. **安全第一**：涉及文件系统写入、系统剪贴板操作需充分测试
4. **用户友好**：所有文案使用中文

## 目录结构

```
clipboard-manager/
├── clipboard_app.py       # 主程序入口（rumps App）
├── clipboard_monitor.py   # 剪贴板监控（NSPasteboard 轮询）
├── storage.py             # 数据存储（JSON + 图片文件）
├── ui_panel.py            # NSWindow + WKWebView 面板
├── panel.html             # 面板 HTML/CSS/JS 界面
├── assets/
│   └── icon.png           # 菜单栏图标
├── requirements.txt       # Python 依赖
├── dev-logs/              # 开发者日志
│   ├── TEMPLATE.md
│   └── 2026-07-20.md
└── CLAUDE.md
```

## 关键文件说明

### clipboard_app.py — 主程序
- rumps.App 菜单栏应用
- 菜单项：打开面板、记录数、设置、退出
- 启动后台线程轮询剪贴板（500ms）
- 启动时自动清理过期数据

### clipboard_monitor.py — 剪贴板监控
- 使用 NSPasteboard.changeCount 检测变化
- 支持 NSPasteboardTypeString（文字）和 NSPasteboardTypePNG/TIFF（图片）
- MD5 哈希去重
- 隐私过滤（排除密码应用）

### storage.py — 数据存储
- clips.json 存储元数据
- images/ 存储图片文件
- settings.json 存储设置
- 自动清理过期条目（基于 retention_days）

### ui_panel.py — 面板窗口
- NSWindow + WKWebView
- JS-Native 桥接（via WKScriptMessageHandler 协议）
- 粘贴时写 NSPasteboard + 模拟 Cmd+V（osascript）

### panel.html — UI 界面
- 搜索栏（实时过滤）
- 卡片列表（置顶优先、时间降序）
- 置顶/删除按钮
- 设置面板（保留天数、排除应用）
- Toast 反馈

## 运行方式

```bash
# 安装依赖
pip3 install --user -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt

# 启动
python3 clipboard_app.py
```

## 存储路径

```
~/Library/Application Support/ClipboardManager/
├── clips.json     # 元数据
├── settings.json  # 设置
└── images/        # 图片文件
```

## 开发者日志

- 每次开发会话后更新 `dev-logs/YYYY-MM-DD.md`
- 模板：`dev-logs/TEMPLATE.md`
