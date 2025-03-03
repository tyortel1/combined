
import os
import sys
import importlib.util

def ensure_module_path():
    # Get the executable directory
    exec_dir = os.path.dirname(sys.executable)
    
    # Add the SeisWare directory to the path
    seisware_dir = os.path.join(exec_dir, 'SeisWare')
    if os.path.isdir(seisware_dir) and seisware_dir not in sys.path:
        print(f"Adding SeisWare directory to path: {seisware_dir}")
        sys.path.insert(0, seisware_dir)
        
    # Check for the SDK file specifically
    sdk_path = os.path.join(seisware_dir, 'seisware_sdk_312.py')
    if os.path.exists(sdk_path):
        print(f"Found SDK file at: {sdk_path}")
    else:
        print(f"SDK file not found at: {sdk_path}")
        
    # Try to find any .py files in the SeisWare directory
    try:
        py_files = [f for f in os.listdir(seisware_dir) if f.endswith('.py')]
        print(f"Python files in SeisWare directory: {py_files}")
    except Exception as e:
        print(f"Error listing SeisWare directory: {e}")

# Run the path adjustment
ensure_module_path()
