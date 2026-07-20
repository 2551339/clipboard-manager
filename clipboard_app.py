#!/usr/bin/env python3
"""
剪切板历史管理器 — 主程序入口
macOS 菜单栏应用：剪贴板监控 + 历史面板 + 全局快捷键
"""
import os
import sys
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import rumps
from storage import load_clips, cleanup_expired
from clipboard_monitor import ClipboardMonitor
from ui_panel import ClipboardPanel


class ClipboardApp(rumps.App):
    """剪切板管理器"""

    def __init__(self):
        super().__init__(
            name="剪切板",
            title="📋",
            quit_button="退出",
        )

        # 延迟初始化面板（等 NSApplication 就绪）
        self._panel = None
        self._monitor = ClipboardMonitor()
        self._running = True

        # 构建菜单
        self._build_menu()

        # 启动剪贴板监控线程
        self._start_monitoring()

        # 启动时清理过期数据
        removed = cleanup_expired()
        if removed > 0:
            print(f"[启动] 清理了 {removed} 条过期记录")

        print("剪切板管理器已启动 ✅")
        print("  - 点击菜单栏 📋 查看历史")

    def _build_menu(self):
        """构建菜单"""
        self.menu.clear()
        self.menu.add(rumps.MenuItem("打开历史面板", callback=self._on_open))
        self.menu.add(rumps.separator)
        self.menu.add(rumps.MenuItem("共 0 条记录"))
        self.menu.add(rumps.separator)
        self.menu.add(rumps.MenuItem("设置", callback=self._on_settings))

    def _start_monitoring(self):
        """后台轮询剪贴板（500ms）"""
        def poll_loop():
            while self._running:
                try:
                    result = self._monitor.check()
                    if result:
                        self._monitor.on_new_clip(result)
                        self._update_menu_count()
                except Exception as e:
                    print(f"[监控错误] {e}")
                time.sleep(0.5)

        t = threading.Thread(target=poll_loop, daemon=True)
        t.start()

    def _update_menu_count(self):
        """更新菜单中显示的条目数"""
        try:
            count = len(load_clips())
            self.menu["共 0 条记录"].title = f"共 {count} 条记录"
        except Exception:
            pass

    def _ensure_panel(self):
        """延迟创建面板（确保在 AppKit runloop 就绪后）"""
        if self._panel is None:
            try:
                self._panel = ClipboardPanel(self)
            except Exception as e:
                print(f"[面板创建失败] {e}")
                self._panel = None

    def _on_open(self, sender):
        """打开/关闭面板"""
        self._ensure_panel()
        if self._panel:
            self._panel.toggle()

    def _on_settings(self, sender):
        """打开设置"""
        self._ensure_panel()
        if self._panel:
            self._panel.show()
            if self._panel.webview:
                self._panel.webview.evaluateJavaScript_completionHandler_(
                    "openSettings()", None
                )

    def send_clips_to_webview(self, clips):
        """将数据推送到 WebView"""
        if self._panel:
            self._panel.send_clips_to_webview(clips)
        self._update_menu_count()

    def paste_clip(self, clip_id):
        """粘贴"""
        if self._panel:
            self._panel.paste_clip(clip_id)


def main():
    app = ClipboardApp()
    app.run()


if __name__ == "__main__":
    main()
