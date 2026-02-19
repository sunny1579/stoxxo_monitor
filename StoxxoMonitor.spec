# -*- mode: python ; coding: utf-8 -*-
#
# PyInstaller spec file for Stoxxo User Quantity Monitoring Tool
#
# HOW TO BUILD:
#   1. Open terminal/cmd in your stoxxo_monitor folder
#   2. Run:  pyinstaller StoxxoMonitor.spec
#   3. Your exe will be in:  dist\StoxxoMonitor\StoxxoMonitor.exe
#

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        # QSS stylesheet — MUST be included or app has no theme
        ('ui\\styles\\dark_theme.qss',  'ui\\styles'),
        ('styles\\dark_theme.qss',      'styles'),
    ],
    hiddenimports=[
        # PyQt6 modules that PyInstaller sometimes misses
        'PyQt6.QtCore',
        'PyQt6.QtGui',
        'PyQt6.QtWidgets',
        'PyQt6.sip',
        # Your project packages
        'core',
        'models',
        'services',
        'ui',
        'ui.tabs',
        'ui.widgets',
        'utils',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Things we definitely don't need — keeps exe smaller
        'matplotlib',
        'numpy',
        'pandas',
        'scipy',
        'PIL',
        'tkinter',
        'unittest',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='StoxxoMonitor',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,          # False = no black console window behind the app
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # icon='icon.ico',      # Uncomment and add an .ico file if you have one
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='StoxxoMonitor',
)
