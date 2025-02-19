import os
import ast
from pathlib import Path

def get_imports(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            tree = ast.parse(file.read())
            
        imports = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for name in node.names:
                    base_module = name.name.split('.')[0]
                    imports.add(base_module)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    base_module = node.module.split('.')[0]
                    imports.add(base_module)
        return imports
    except Exception as e:
        print(f"\nError in {file_path}: {e}")
        return set()

def find_all_python_files(start_path):
    python_files = []
    for path in Path(start_path).rglob('*.py'):
        path_str = str(path)
        # Skip venv and site-packages
        if not any(x in path_str for x in ['venv', 'site-packages', '__pycache__']):
            python_files.append(path)
    return sorted(python_files)

print("Scanning for Python files in your project...\n")
all_imports = set()
files = find_all_python_files('.')

for py_file in files:
    imports = get_imports(py_file)
    if imports:
        print(f"📄 {py_file}:")
        print("   Imports:", ", ".join(sorted(imports)))
        all_imports.update(imports)

print("\n📦 All unique imports found:")
for imp in sorted(all_imports):
    print(f"- {imp}")