import json
from pathlib import Path

import yaml

for path in Path(".").rglob("*.json"):
    if ".git" not in path.parts:
        json.loads(path.read_text(encoding="utf-8"))

for path in Path(".").rglob("*.yaml"):
    if ".git" not in path.parts and ".github" not in path.parts:
        yaml.safe_load(path.read_text(encoding="utf-8"))

print("JSON and YAML validation passed")
