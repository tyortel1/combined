# Map2.spec
from pathlib import Path
import os
root_dir = os.path.dirname(os.path.abspath('Map2.py'))
a = Analysis(
    ['Map2.py'],
    pathex=[root_dir],
    binaries=[
        ('_seisware_sdk_312.pyd', '.'),  # SeisWare SDK binary
    ],
    datas=[
        (os.path.join(root_dir, 'Icons'), 'Icons'),
        (os.path.join(root_dir, 'Palettes'), 'Palettes'),
        # Add matplotlib data files
        (os.path.join(os.path.dirname(os.__file__), 'site-packages/matplotlib/mpl-data'), 'matplotlib/mpl-data'),
        # Add SeisWare and system DLLs
        ('libzmq-mt-4_3_0.dll', '.'),
        ('mfc140u.dll', '.'),
        ('msvcp140.dll', '.'),
        ('SWSDKCore.dll', '.'),
        ('vcruntime140.dll', '.'),
        ('seisware_sdk_312.py', '.'),
        ('__init__.py', '.'),
    ],
    hiddenimports=[
        'seisware_sdk_312',  # Add SeisWare SDK import
        # Core Scientific Stack
        'numpy',
        'pandas',
        'matplotlib',
        'seaborn',
        'scipy',
        'sklearn',
        'plotly',
        
        # Matplotlib backends
        'matplotlib.backends.backend_qt5agg',
        'matplotlib.backends.backend_qt5cairo',
        'matplotlib.backends.backend_qtagg',
        
        # PySide6 components
        'PySide6.QtCore',
        'PySide6.QtGui',
        'PySide6.QtWidgets',
        'PySide6.QtCharts',
        'PySide6.QtPrintSupport',
        'PySide6.QtSvg',
        
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
    noarchive=False
)
pyz = PYZ(a.pure, a.zipped_data)
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
    console=True,  # Set to True temporarily for debugging
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)