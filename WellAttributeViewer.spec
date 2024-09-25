# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['map2.py'],  # Your main script
    pathex=['C:\\Users\\jerem\\source\\repos\\Well Attribute Viewer'],
    binaries=[
        ('C:/Users/jerem/AppData/Local/Programs/Python/Python37/Lib/site-packages/qt5_applications/Qt/plugins/platforms/qwindows.dll', 'platforms/'),
    ],
    datas=[
        ('icons', 'icons'),  # Ensure icons directory is correctly included
        ('Palettes', 'Palettes'),  # Ensure Palettes directory is correctly included
    ],
    hiddenimports=[
        'SwPropertiesEdit',
        'ColorEdit',
        'ZoneViewer',
        'ProjectSaver',
        'Plot',
        'DrawingArea',
        'HighlightCriteriaDialog',
        'DataLoadWellZone',
        'UiSetup',
        'Calculations',
        'GunBarrel',
        'InZone',
        'ColumnSelectDialog',
        'ProjectOpen',
        'DataLoader',
        'FilterHeaderView',
        'CrossPlot'
    ],
    hookspath=[],  # Paths to any custom hooks (if any)
    runtime_hooks=[],  # Hooks to be run at runtime (if any)
    excludes=['qdirect2d'],  # Exclude problematic DLLs here
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
    name='map2',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['icons\\ZoneAnalyzer.ico'],
)

