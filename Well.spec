# Map2.spec
from pathlib import Path
import os

# Get the root directory of your project
root_dir = os.path.dirname(os.path.abspath('Map2.py'))

a = Analysis(
    ['Map2.py'],  # Your main script
    pathex=[root_dir],
    binaries=[],
    datas=[
        # Correct paths for your data directories
        (os.path.join(root_dir, 'Icons'), 'Icons'),  # Fixed path to Icons
        (os.path.join(root_dir, 'Palettes'), 'Palettes'),  # Fixed path to Palettes
    ],
    hiddenimports=[
        # GUI
        'PySide6.QtCore',
        'PySide6.QtGui',
        'PySide6.QtWidgets',
        'PySide6.QtCharts',
        
        # Scientific packages
        'numpy',
        'pandas',
        'matplotlib',
        'matplotlib.backends.backend_qt5agg',
        'scipy',
        'seaborn',
        'segyio',
        'shapely',
        'sklearn',
        'plotly',
        
        # Your custom modules
        'CalculateCorrelationMatrix',
        'CalculateCorrelations',
        'CalculatePC',
        'CalculateWellComparisons',
        'Calculations',
        'ColorEdit',
        'ColumnSelectDialog',
        'ComboBoxDelegate',
        'CriteriaToZone',
        'CrossPlot',
        'DataLoadSegy',
        'DataLoadWellZone',
        'DataLoader',
        'DatabaseManager',
        'DateDelegate',
        'DecisionTreeDialog',
        'DeclineCurveAnalysis',
        'DefaultProperties',
        'DeleteZone',
        'DrawingArea',
        'EurNpv',
        'GunBarrel',
        'HighlightCriteriaDialog',
        'ImportExcel',
        'InZone',
        'LaunchCombinedCashflow',
        'LoadProductions',
        'ModelProperties',
        'Plot',
        'PlotTotals',
        'ProjectDialog',
        'ProjectOpen',
        'ProjectSaver',
        'PudWellSelector',
        'SaveDeclineCurveDialog',
        'ScenarioNameDialog',
        'SeisWare',
        'SeisWareConnect',
        'SwPropertiesEdit',
        'UiMain',
        'UiSetup',
        'WellProperties',
        'ZoneViewer',
        'numeric_table_widget_item',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='Map2',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # Set to False for a windowless application
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)