import os
import site
import glob
from PyInstaller.utils.hooks import collect_submodules, collect_dynamic_libs, collect_data_files

# Get the root directory of your project
root_dir = os.path.abspath(".")
site_packages = site.getsitepackages()[0]

# Path to the SeisWare SDK folder
seisware_path = r"C:\Users\jerem\AppData\Local\Programs\Python\Python312\Lib\site-packages\SeisWare"


# List of specific SeisWare binaries to include
seisware_binaries = [
    (os.path.join(seisware_path, "libzmq-mt-4_3_0.dll"), "."),
    (os.path.join(seisware_path, "SWSDKCore.dll"), "."),
    (os.path.join(seisware_path, "msvcp140.dll"), "."),
    (os.path.join(seisware_path, "vcruntime140.dll"), "."),
    (os.path.join(seisware_path, "mfc140u.dll"), "."),
    (os.path.join(seisware_path, "_seisware_sdk_312.pyd"), "."),
]

# Collect SeisWare data files
seisware_datas = collect_data_files("SeisWare")

# Auto-collect all installed Python packages and their dynamic libraries
all_binaries = (
    collect_dynamic_libs("numpy") + 
    collect_dynamic_libs("pandas") + 
    collect_dynamic_libs("matplotlib") + 
    collect_dynamic_libs("scipy") + 
    collect_dynamic_libs("SeisWare") + 
    seisware_binaries
)

# Auto-collect all necessary data files from installed packages
all_datas = (
    collect_data_files("numpy") +
    collect_data_files("pandas") +
    collect_data_files("SeisWare") +
    seisware_datas
)

# Auto-collect all installed modules (ensures nothing is missing)
hidden_imports = collect_submodules("SeisWare") + collect_submodules("PySide6")

# Add your custom modules manually (ensures they are included)
hidden_imports += [
    "CalculateCorrelationMatrix",
    "CalculateCorrelations",
    "CalculatePC",
    "CalculateWellComparisons",
    "CalculateZoneAttributes",
    "Calculations",
    "ColorEdit",
    "ColumnSelectDialog",
    "ComboBoxDelegate",
    "CriteriaToZone",
    "CrossPlot",
    "DataLoadSegy",
    "DataLoadWellZone",
    "DataLoader",
    "DatabaseManager",
    "DateDelegate",
    "DecisionTreeDialog",
    "DeclineCurveAnalysis",
    "DefaultProperties",
    "DeleteZone",
    "DrawingArea",
    "EurNpv",
    "GunBarrel",
    "HighlightCriteriaDialog",
    "ImportExcel",
    "InZone",
    "LaunchCombinedCashflow",
    "LoadProductions",
    "ModelProperties",
    "Plot",
    "PlotTotals",
    "ProjectDialog",
    "ProjectOpen",
    "ProjectSaver",
    "PudWellSelector",
    "SaveDeclineCurveDialog",
    "ScenarioNameDialog",
    "SeisWareConnect",
    "SwPropertiesEdit",
    "UiMain",
    "UiSetup",
    "WellProperties",
    "ZoneViewer",
    "numeric_table_widget_item",
    "StyledSliders",
]

# Create the Analysis object (✅ Only ONE `Analysis` block)
a = Analysis(
    ["Map2.py"],  # ✅ Use the main script, not debug_launcher.py
    pathex=[root_dir, seisware_path] if os.path.exists(seisware_path) else [root_dir],
    binaries=all_binaries,
    datas=[
        (os.path.join(root_dir, "Icons"), "Icons"),
        (os.path.join(root_dir, "Palettes"), "Palettes"),
    ] + all_datas,
    hiddenimports=hidden_imports,  # ✅ Ensures ALL dependencies are included
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],  # ✅ No runtime hooks needed
    excludes=["PyQt5"],  # ✅ Exclude PyQt5 to prevent conflicts
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
    name="Map2",
    debug=False,  # ✅ Debug mode is OFF
    bootloader_ignore_signals=False,
    strip=False,  # ✅ No Linux tools
    upx=True,  # ✅ UPX compression enabled (set to False if unstable)
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # ✅ No console window (set to True for CLI)
    disable_windowed_traceback=True,  # ✅ Prevents traceback pop-ups
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
