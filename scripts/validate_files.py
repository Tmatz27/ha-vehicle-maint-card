from pathlib import Path
import json
import yaml

for path in Path('.').rglob('*.json'):
    if '.git' not in path.parts:
        json.loads(path.read_text())
for path in Path('.').rglob('*.yaml'):
    if '.git' not in path.parts and '.github' not in path.parts:
        yaml.safe_load(path.read_text())
print('JSON and YAML validation passed')
