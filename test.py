import os
import re

def find_all_imports(directory):
    imports = set()
    pattern = re.compile(r'^\s*(?:import|from)\s+([\w\d_.]+)')

    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith(".py"):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        for line in f:
                            match = pattern.match(line)
                            if match:
                                imports.add(match.group(1).split('.')[0])  # Only get top-level package
                except Exception as e:
                    print(f"Error reading {file_path}: {e}")

    return imports

# Set your project directory
project_path = r"C:\Users\jerem\source\repos\Combined"
all_imports = find_all_imports(project_path)

# Print all found imports
print("\nAll Imports in Your Project:")
for imp in sorted(all_imports):
    print(imp)
