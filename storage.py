"""
数据存储模块
- JSON 文件存储元数据
- 图片文件存储
- 设置管理
- 自动清理过期条目
"""
import json
import os
import uuid
import time
import shutil
import hashlib
from datetime import datetime, timedelta

# 存储路径
BASE_DIR = os.path.expanduser("~/Library/Application Support/ClipboardManager")
CLIPS_FILE = os.path.join(BASE_DIR, "clips.json")
IMAGES_DIR = os.path.join(BASE_DIR, "images")
SETTINGS_FILE = os.path.join(BASE_DIR, "settings.json")

# 默认设置
DEFAULT_SETTINGS = {
    "retention_days": 7,      # 保留天数：1/3/7/30/0(永久)
    "excluded_apps": [         # 排除的密码管理应用
        "1Password",
        "Bitwarden",
        "KeePassXC",
        "Strongbox",
        "Secrets",
        "Keychain Access",
    ],
    "shortcut": "cmd+shift+v",
}


def ensure_dirs():
    """确保存储目录存在"""
    os.makedirs(BASE_DIR, exist_ok=True)
    os.makedirs(IMAGES_DIR, exist_ok=True)


def load_clips():
    """加载所有剪切板条目，按时间降序返回（置顶优先）"""
    ensure_dirs()
    if not os.path.exists(CLIPS_FILE):
        return []
    try:
        with open(CLIPS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        # 排序：置顶优先，同组内时间降序
        data.sort(key=lambda x: (not x.get("pinned", False), -x.get("timestamp", 0)))
        return data
    except (json.JSONDecodeError, Exception):
        return []


def save_clips(clips):
    """保存所有条目到 JSON 文件"""
    ensure_dirs()
    with open(CLIPS_FILE, "w", encoding="utf-8") as f:
        json.dump(clips, f, ensure_ascii=False, indent=2)


def add_clip(clip_type, content, source_app="", image_data=None):
    """
    添加一条剪切板记录
    - 如果内容已存在，则更新时间戳（去重）
    - 如果不存在，新建条目
    返回条目的 id
    """
    clips = load_clips()
    now = int(time.time() * 1000)

    if clip_type == "text":
        content = content.strip()
        # 检查是否已存在相同文字内容
        for c in clips:
            if c["type"] == "text" and c.get("content") == content:
                c["timestamp"] = now
                c["source_app"] = source_app
                save_clips(clips)
                return c["id"]

        clip_id = str(uuid.uuid4())[:8]
        entry = {
            "id": clip_id,
            "type": "text",
            "timestamp": now,
            "pinned": False,
            "source_app": source_app,
            "content": content,
            "preview": content[:100],
        }

    elif clip_type == "image" and image_data:
        # 图片：通过数据哈希去重
        img_hash = hashlib.md5(image_data).hexdigest()
        for c in clips:
            if c["type"] == "image" and c.get("img_hash") == img_hash:
                c["timestamp"] = now
                c["source_app"] = source_app
                save_clips(clips)
                return c["id"]

        clip_id = str(uuid.uuid4())[:8]
        img_filename = f"{clip_id}.png"
        img_path = os.path.join(IMAGES_DIR, img_filename)
        with open(img_path, "wb") as f:
            f.write(image_data)
        entry = {
            "id": clip_id,
            "type": "image",
            "timestamp": now,
            "pinned": False,
            "source_app": source_app,
            "image_path": img_path,
            "preview": "[图片]",
            "img_hash": img_hash,
        }
    else:
        return None

    # 插入到列表开头（置顶项保持在前）
    pinned = [c for c in clips if c.get("pinned")]
    unpinned = [c for c in clips if not c.get("pinned")]
    unpinned.insert(0, entry)
    save_clips(pinned + unpinned)
    return entry["id"]


def toggle_pin(clip_id):
    """切换置顶状态"""
    clips = load_clips()
    for c in clips:
        if c["id"] == clip_id:
            c["pinned"] = not c.get("pinned", False)
            break
    save_clips(clips)
    return clips


def delete_clip(clip_id):
    """删除单条记录（含关联图片）"""
    clips = load_clips()
    for c in clips:
        if c["id"] == clip_id:
            if c.get("image_path") and os.path.exists(c["image_path"]):
                os.remove(c["image_path"])
            clips.remove(c)
            break
    save_clips(clips)
    return clips


def clear_all_unpinned():
    """一键清空所有未置顶的内容"""
    clips = load_clips()
    unpinned = [c for c in clips if not c.get("pinned")]
    pinned = [c for c in clips if c.get("pinned")]
    for c in unpinned:
        if c.get("image_path") and os.path.exists(c["image_path"]):
            os.remove(c["image_path"])
    save_clips(pinned)
    return len(unpinned)
    return clips


def search_clips(query):
    """搜索文字内容"""
    if not query.strip():
        return load_clips()
    query_lower = query.lower()
    all_clips = load_clips()
    return [
        c for c in all_clips
        if c["type"] == "text" and query_lower in c.get("content", "").lower()
    ]


def load_settings():
    """加载设置"""
    ensure_dirs()
    if not os.path.exists(SETTINGS_FILE):
        save_settings(DEFAULT_SETTINGS)
        return DEFAULT_SETTINGS.copy()
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            settings = json.load(f)
        # 补全缺失的默认值
        for k, v in DEFAULT_SETTINGS.items():
            if k not in settings:
                settings[k] = v
        return settings
    except Exception:
        return DEFAULT_SETTINGS.copy()


def save_settings(settings):
    """保存设置"""
    ensure_dirs()
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(settings, f, ensure_ascii=False, indent=2)


def cleanup_expired():
    """清理过期条目（保留天数 > 0 时生效，pinned 条目不清理）"""
    settings = load_settings()
    retention_days = settings.get("retention_days", 7)
    if retention_days <= 0:
        return 0  # 永久保留

    cutoff = int((datetime.now() - timedelta(days=retention_days)).timestamp() * 1000)
    clips = load_clips()
    expired = [
        c for c in clips
        if not c.get("pinned") and c.get("timestamp", 0) < cutoff
    ]
    for c in expired:
        if c.get("image_path") and os.path.exists(c["image_path"]):
            os.remove(c["image_path"])
    remaining = [c for c in clips if c not in expired]
    save_clips(remaining)
    return len(expired)


def get_source_app():
    """获取当前最前端的应用名称（用于隐私过滤）"""
    try:
        from AppKit import NSWorkspace
        workspace = NSWorkspace.sharedWorkspace()
        app = workspace.frontmostApplication()
        return app.localizedName()
    except Exception:
        return ""


def is_excluded_app(app_name):
    """检查应用是否在排除列表中"""
    settings = load_settings()
    excluded = settings.get("excluded_apps", [])
    return app_name in excluded


if __name__ == "__main__":
    # 简单测试
    ensure_dirs()
    print("存储目录:", BASE_DIR)
    add_clip("text", "Hello World 测试文字", source_app="Safari")
    clips = load_clips()
    print(f"当前条目数: {len(clips)}")
    for c in clips:
        print(f"  - [{c['type']}] {c.get('preview', '')[:50]} (pinned={c['pinned']})")
