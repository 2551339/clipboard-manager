"""
剪切板历史面板 — NSWindow + WKWebView
渲染 HTML/CSS 卡片界面，处理搜索、置顶、删除、粘贴等交互
"""
import os
import sys
import json
import subprocess
from AppKit import (
    NSWindow, NSBackingStoreBuffered,
    NSScreen, NSApplication, NSApp,
)
from WebKit import WKWebView, WKWebViewConfiguration, WKUserContentController
from Foundation import NSURL, NSObject, NSMakeRect, NSBundle
from storage import load_clips, toggle_pin, delete_clip, search_clips, load_settings, save_settings, clear_all_unpinned
from Cocoa import NSPasteboard, NSPasteboardTypeString, NSPasteboardTypePNG
import objc


def _find_panel_html():
    """查找 panel.html，兼容源码运行和 .app 打包两种模式"""
    # 1. 先尝试当前目录（源码运行）
    here = os.path.join(os.path.dirname(os.path.abspath(__file__)), "panel.html")
    if os.path.exists(here):
        return here

    # 2. 尝试 .app bundle 的 Resources 目录
    bundle = NSBundle.mainBundle()
    if bundle:
        resource_path = bundle.pathForResource_ofType_("panel", "html")
        if resource_path:
            return resource_path

    # 3. 尝试相对于可执行文件的路径
    exec_dir = os.path.dirname(sys.executable)
    nearby = os.path.join(exec_dir, "..", "Resources", "panel.html")
    if os.path.exists(nearby):
        return os.path.abspath(nearby)

    # 4. 回退到当前目录
    return here


PANEL_HTML = _find_panel_html()


class ScriptHandler(NSObject):
    """处理 WebView 中的 JS 调用"""

    def initWithApp_(self, app):
        self = objc.super(ScriptHandler, self).init()
        if self:
            self._app = app
        return self

    def userContentController_didReceiveScriptMessage_(self, controller, message):
        body = message.body()
        if body is None:
            return
        action = body.get("action")

        if action == "getClips":
            query = body.get("query", "")
            if query.strip():
                clips = search_clips(query)
            else:
                clips = load_clips()
            self._app.send_clips_to_webview(clips)

        elif action == "pin":
            clip_id = body.get("id")
            clips = toggle_pin(clip_id)
            self._app.send_clips_to_webview(clips)

        elif action == "delete":
            clip_id = body.get("id")
            clips = delete_clip(clip_id)
            self._app.send_clips_to_webview(clips)

        elif action == "paste":
            clip_id = body.get("id")
            self._app.paste_clip(clip_id)

        elif action == "copy":
            clip_id = body.get("id")
            self._app.copy_clip(clip_id)
            self._app.webview.evaluateJavaScript_completionHandler_(
                "window.showToast('已复制')", None
            )

        elif action == "getSettings":
            settings = load_settings()
            self._app.webview.evaluateJavaScript_completionHandler_(
                f"window.receiveSettings({json.dumps(settings)})", None
            )

        elif action == "saveSettings":
            settings = body.get("settings", {})
            save_settings(settings)
            self._app.webview.evaluateJavaScript_completionHandler_(
                "window.showToast('设置已保存')", None
            )

        elif action == "clearAll":
            removed = clear_all_unpinned()
            clips = load_clips()
            self._app.send_clips_to_webview(clips)
            self._app.webview.evaluateJavaScript_completionHandler_(
                f"window.showToast('已清空 {removed} 条记录')", None
            )


class NavDelegate(NSObject):
    """页面加载完成时推送数据"""
    def initWithPanel_(self, panel):
        self = objc.super(NavDelegate, self).init()
        if self:
            self._panel = panel
        return self

    def webView_didFinishNavigation_(self, webview, navigation):
        """页面加载完成 → 推送剪切板数据"""
        try:
            clips = load_clips()
            self._panel.send_clips_to_webview(clips)
        except Exception:
            pass


class ClipboardPanel:
    """剪切板历史面板窗口"""

    def __init__(self, app):
        self._app = app
        self._window = None
        self._webview = None
        self._handler = None  # 强引用防止 GC 回收导致崩溃
        self._create_window()

    def _create_window(self):
        """创建 NSWindow + WKWebView"""
        # 窗口大小
        width, height = 400, 560

        # 计算在屏幕右下角显示
        screen = NSScreen.mainScreen()
        screen_frame = screen.visibleFrame()
        x = screen_frame.size.width - width - 20
        y = screen_frame.size.height - height - 40

        rect = NSMakeRect(x, y, width, height)

        # 窗口样式：有标题栏(1) + 可关闭(2) + 可最小化(4) + 可调整大小(8)
        style = 1 | 2 | 4 | 8

        self._window = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
            rect, style, NSBackingStoreBuffered, False
        )
        self._window.setTitle_("剪切板历史")
        self._window.setLevel_(3)  # 浮动窗口
        self._window.setMinSize_((340, 400))
        self._window.setReleasedWhenClosed_(False)  # 关闭时不释放窗口

        # 设置半透明淡蓝色背景
        self._window.setBackgroundColor_(
            NSApp.keyWindow().backgroundColor() if NSApp.keyWindow() else None
        )
        self._window.setOpaque_(True)

        # WKWebView
        config = WKWebViewConfiguration.alloc().init()
        controller = WKUserContentController.alloc().init()

        # 注册 JS 消息处理器（保存为实例属性防止 GC 回收导致崩溃）
        self._handler = ScriptHandler.alloc().initWithApp_(self)
        controller.addScriptMessageHandler_name_(self._handler, "clipboardBridge")

        config.setUserContentController_(controller)

        # WebView 填满窗口
        webview_rect = NSMakeRect(0, 0, width, height)
        self._webview = WKWebView.alloc().initWithFrame_configuration_(webview_rect, config)
        self._webview.setAutoresizingMask_(3)  # 宽度+高度自适应

        # 设置导航代理：页面加载完成后自动推送数据
        self._nav_delegate = NavDelegate.alloc().initWithPanel_(self)
        self._webview.setNavigationDelegate_(self._nav_delegate)

        self._window.contentView().addSubview_(self._webview)

        # 加载 HTML
        if os.path.exists(PANEL_HTML):
            url = NSURL.fileURLWithPath_(PANEL_HTML)
            self._webview.loadFileURL_allowingReadAccessToURL_(url, url)
        else:
            self._webview.loadHTMLString_baseURL_(
                "<h2>panel.html 未找到</h2>", None
            )

    def show(self):
        """显示窗口"""
        try:
            if self._window is None:
                self._create_window()
            self._window.makeKeyAndOrderFront_(None)
            # 刷新数据
            self.send_clips_to_webview(load_clips())
        except Exception:
            # 窗口对象损坏，重建
            self._create_window()
            self._window.makeKeyAndOrderFront_(None)
            self.send_clips_to_webview(load_clips())

    def hide(self):
        """隐藏窗口（不销毁）"""
        if self._window:
            try:
                self._window.orderOut_(None)
            except Exception:
                pass

    def toggle(self):
        """切换显示/隐藏"""
        try:
            if self._window and self._window.isVisible():
                self.hide()
            else:
                self.show()
        except Exception:
            # 如果窗口已损坏，重建并显示
            self.show()

    def send_clips_to_webview(self, clips):
        """将剪切板数据发送到 WebView"""
        if not self._webview:
            return
        clips_json = json.dumps(clips, ensure_ascii=False)
        js = f"window.receiveClips({clips_json})"
        self._webview.evaluateJavaScript_completionHandler_(js, None)

    def paste_clip(self, clip_id):
        """粘贴某条内容到剪贴板并模拟 Cmd+V"""
        clips = load_clips()
        clip = next((c for c in clips if c["id"] == clip_id), None)
        if not clip:
            return

        self._write_to_clipboard(clip)

        # 隐藏面板
        self.hide()

        # 模拟 Cmd+V 粘贴
        subprocess.Popen([
            "osascript", "-e",
            'tell application "System Events" to keystroke "v" using command down'
        ])

    def copy_clip(self, clip_id):
        """仅复制到剪贴板，不粘贴"""
        clips = load_clips()
        clip = next((c for c in clips if c["id"] == clip_id), None)
        if clip:
            self._write_to_clipboard(clip)

    def _write_to_clipboard(self, clip):
        """将内容写入系统剪贴板"""
        pb = NSPasteboard.generalPasteboard()
        pb.clearContents()
        if clip["type"] == "text":
            pb.setString_forType_(clip["content"], NSPasteboardTypeString)
        elif clip["type"] == "image" and clip.get("image_path"):
            if os.path.exists(clip["image_path"]):
                from Foundation import NSData
                data = NSData.dataWithContentsOfFile_(clip["image_path"])
                if data:
                    pb.setData_forType_(data, NSPasteboardTypePNG)

    @property
    def webview(self):
        return self._webview

    @property
    def window(self):
        return self._window
