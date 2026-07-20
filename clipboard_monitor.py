"""
剪贴板监控模块
- 通过 NSPasteboard 监控系统剪贴板变化
- 支持文字和图片类型
- 哈希比对去重
- 隐私过滤
"""
import hashlib
from AppKit import NSPasteboard, NSPasteboardTypeString, NSPasteboardTypePNG, NSPasteboardTypeTIFF
from storage import add_clip, get_source_app, is_excluded_app


def _hash_content(data):
    """对内容做哈希用于去重比对"""
    if isinstance(data, str):
        return hashlib.md5(data.encode("utf-8")).hexdigest()
    return hashlib.md5(data).hexdigest()


class ClipboardMonitor:
    """剪贴板监控器"""

    def __init__(self):
        self._pasteboard = NSPasteboard.generalPasteboard()
        self._last_text_hash = None
        self._last_image_hash = None
        self._change_count = self._pasteboard.changeCount()

    def check(self):
        """
        检查剪贴板是否有新内容。
        返回 None 表示无变化，返回 dict 表示有新内容。
        """
        current_change = self._pasteboard.changeCount()
        if current_change == self._change_count:
            return None
        self._change_count = current_change

        # 获取来源应用，隐私检查
        source_app = get_source_app()
        if is_excluded_app(source_app):
            return None

        # 检查文字内容
        text = self._pasteboard.stringForType_(NSPasteboardTypeString)
        if text:
            text_hash = _hash_content(text)
            if text_hash != self._last_text_hash:
                self._last_text_hash = text_hash
                return {
                    "type": "text",
                    "content": text,
                    "source_app": source_app,
                }

        # 检查图片内容
        png_data = self._pasteboard.dataForType_(NSPasteboardTypePNG)
        if not png_data:
            # 尝试 TIFF 格式（某些应用使用）
            tiff_data = self._pasteboard.dataForType_(NSPasteboardTypeTIFF)
            if tiff_data:
                png_data = tiff_data

        if png_data:
            img_bytes = png_data.bytes().tobytes()
            img_hash = _hash_content(img_bytes)
            if img_hash != self._last_image_hash:
                self._last_image_hash = img_hash
                return {
                    "type": "image",
                    "content": "",
                    "image_data": img_bytes,
                    "source_app": source_app,
                }

        return None

    def on_new_clip(self, clip_data):
        """处理新剪贴板内容：存入存储"""
        add_clip(
            clip_type=clip_data["type"],
            content=clip_data.get("content", ""),
            source_app=clip_data.get("source_app", ""),
            image_data=clip_data.get("image_data"),
        )


if __name__ == "__main__":
    # 简单测试
    import time
    monitor = ClipboardMonitor()
    print("监控剪贴板中... 复制一些文字或图片试试 (Ctrl+C 退出)")
    try:
        while True:
            result = monitor.check()
            if result:
                print(f"[新内容] 类型: {result['type']}, 来源: {result['source_app']}")
                if result["type"] == "text":
                    print(f"  内容: {result['content'][:80]}...")
                monitor.on_new_clip(result)
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("停止监控")
