# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['map2.py'],  # Your main script
    pathex=['.'],  # Use current directory as the search path
    binaries=[],
    datas=[
        ('icons', 'icons'),  # Ensure icons directory is correctly included
        ('Palettes', 'Palettes'),  # Ensure Palettes directory is correctly included
    ],
    hiddenimports=[
        'SwPropertiesEdit',
        'ColorEdit',
        'ZoneViewer',
        'ProjectSaver',
        'Exporting',
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
    ],
    hookspath=[],
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
    exclude_binaries=True,
    name='YourAppName',  # Replace with your app name
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # Set to True if you want a console window
    icon='icons/ZoneAnalyzer.ico'  # Use a relative path to your icon, or remove this line if you don't have an icon
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='YourAppName'  # Replace with your app name
)
