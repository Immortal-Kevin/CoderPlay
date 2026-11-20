"""Offline verification of the reviewed source-only license inventory.

Hashes detect changed notice files; SPDX assignments require human review and
are not inferred from a simplistic GPL keyword search or package description.
"""
import ast
import hashlib
import importlib.metadata
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
PERMITTED = {"MIT", "Apache-2.0", "BSD-2-Clause", "BSD-3-Clause", "TCL",
             "Python-2.0", "PSF-2.0", "ISC", "Apache-2.0 OR BSD-2-Clause", "MPL-2.0"}


def audit(development=False):
    data = json.loads((ROOT / "licenses/manifest.json").read_text(encoding="utf-8"))
    assert data["runtime_pip_dependencies"] == [], "Runtime dependencies changed; re-audit required"
    for item in data["license_files"]:
        path = ROOT / item["file"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == item["sha256"], str(path)
    for item in data["tools"] + data["verified_platform"]:
        assert item["spdx"] in PERMITTED, item
        if item["spdx"] == "MPL-2.0":
            assert item["scope"] == "vendored by bootstrap pip only" and not item["distributed"]
    for folder in [ROOT / "core", ROOT / "ui", ROOT / "io_utils"]:
        for path in folder.glob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                names = []
                if isinstance(node, ast.Import):
                    names = [n.name.split(".")[0] for n in node.names]
                elif isinstance(node, ast.ImportFrom) and node.level == 0:
                    names = [node.module.split(".")[0]]
                for name in names:
                    assert name in sys.stdlib_module_names | {"core", "ui", "io_utils"}, (path, name)
                    assert name not in {"socket", "urllib", "http", "ssl", "subprocess"}, (path, name)
    checked = []
    if development:
        for item in data["tools"]:
            if item["scope"] == "development only":
                actual = importlib.metadata.version(item["name"])
                assert actual == item["version"], (item["name"], actual)
                checked.append(item["name"] + "==" + actual)
    return {"status": "PASS", "scope": data["distribution"],
            "runtime_pip_dependencies": 0, "verified_license_files": len(data["license_files"]),
            "development_versions_checked": checked,
            "prohibited_or_unknown_distributed_components": 0,
            "packager": "none for source; portable ZIP is separately checked by tools/audit_portable.py"}


if __name__ == "__main__":
    print(json.dumps(audit("--development" in sys.argv), indent=2, ensure_ascii=False))
