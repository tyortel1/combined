# -*- mode: python ; coding: utf-8 -*-

import os
from PyInstaller.utils.hooks import collect_submodules

block_cipher = None

# Get the current directory
current_dir = os.path.dirname(os.path.abspath('__file__'))

# Full path to the icon file
icon_path = r'C:\Users\jerem\source\repos\Zone Analyzer\Icons\ZoneAnalyzer.ico'

a = Analysis(
    ['Map2.py'],
    pathex=[current_dir],
    binaries=[],
    datas=[
        (os.path.join(current_dir, 'Exporting.py'), '.'),
        (os.path.join(current_dir, 'DataLoader.py'), '.'),
        (os.path.join(current_dir, 'SwPropertiesEdit.py'), '.'),
        (os.path.join(current_dir, 'GunBarrel.py'), '.'),
        (os.path.join(current_dir, 'Plot.py'), '.'),
        (icon_path, 'Icons')
    ],
    hiddenimports=[
        'Exporting', 
        'DataLoader', 
        'SwPropertiesEdit', 
        'GunBarrel', 
        'Plot', 
        'SeisWare',
        'numpy',
        'pandas',
        'scipy',
        'PySide2',
        'shapely',
        'pystray',
        'matplotlib',
        *collect_submodules('shapely'),
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='ZoneAnalyzer',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=[icon_path],
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='ZoneAnalyzer'
)
