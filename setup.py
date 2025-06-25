"""
Ltorrent 토렌트 클라이언트 macOS 앱 빌드 설정
"""
from setuptools import setup

APP = ['main.py']
DATA_FILES = []
OPTIONS = {
    'argv_emulation': False,  # Carbon 프레임워크 오류 방지
    'plist': {
        'CFBundleDisplayName': 'Ltorrent',
        'CFBundleName': 'Ltorrent',
        'CFBundleIdentifier': 'com.erossx.ltorrent',
        'CFBundleVersion': '1.0.0',
        'CFBundleShortVersionString': '1.0.0',
        'NSHighResolutionCapable': True,
        'NSRequiresAquaSystemAppearance': False,
        'LSUIElement': False,
        'CFBundleDocumentTypes': [
            {
                'CFBundleTypeName': 'Torrent File',
                'CFBundleTypeRole': 'Editor',
                'CFBundleTypeExtensions': ['torrent'],
                'CFBundleTypeIconFile': 'torrent.icns',
            }
        ]
    },
          'packages': ['PySide6'],
      'includes': ['torrent_client'],
      'excludes': ['tkinter', 'matplotlib', 'IPython', 'pkg_resources', 'setuptools'],
    'iconfile': 'icon.icns',
    'strip': False,  # 디버깅을 위해 심볼 유지
}

setup(
    app=APP,
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
    name='Ltorrent',
    version='1.0.0',
    description='토렌트 클라이언트',
    author='erossx',
) 