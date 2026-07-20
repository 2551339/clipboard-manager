"""
py2app 打包配置
生成剪切板管理器 .app 应用
"""
from setuptools import setup

APP = ['clipboard_app.py']
DATA_FILES = [
    ('', ['panel.html']),
    ('assets', ['assets/icon.png']),
]
OPTIONS = {
    'argv_emulation': False,
    'packages': [
        'rumps',
        'objc',
        'Cocoa',
        'AppKit',
        'WebKit',
        'Foundation',
        'Quartz',
    ],
    'includes': [
        'clipboard_monitor',
        'storage',
        'ui_panel',
    ],
    'plist': {
        'CFBundleName': '剪切板管理器',
        'CFBundleDisplayName': '剪切板管理器',
        'CFBundleIdentifier': 'com.clipboard.manager',
        'CFBundleVersion': '1.0.0',
        'CFBundleShortVersionString': '1.0.0',
        'LSUIElement': True,  # 菜单栏应用，不在 Dock 显示
        'NSHighResolutionCapable': True,
    },
}

setup(
    name='剪切板管理器',
    app=APP,
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)
