"""Audit the delivered ZIP, including nested stdlib members and PE dependencies."""
import hashlib
import io
import json
from pathlib import Path
import sys
import zipfile
from build_portable import NATIVE, SYSTEM
from pe_imports import dll_imports
import tempfile


def audit(path):
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        top = names[0].split("/")[0] + "/"
        manifest = json.loads(archive.read(top + "MANIFEST.json"))
        indexed = {top + item["path"] for item in manifest["files"]} | {top + "MANIFEST.json"}
        assert set(names) == indexed, "Unlisted or missing files in ZIP"
        expected = {"FFT Playground.exe", "runtime/python.exe", "runtime/python314.dll", "runtime/vcruntime140.dll"}
        expected.update("runtime/DLLs/" + name for name in NATIVE)
        actual = {item["path"] for item in manifest["files"] if Path(item["path"]).suffix.lower() in (".dll", ".pyd", ".exe")}
        assert actual == expected, "Unexpected native component"
        binaries = {Path(name).name.lower() for name in expected}
        for item in manifest["files"]:
            data = archive.read(top + item["path"])
            assert hashlib.sha256(data).hexdigest() == item["sha256"], item["path"]
            if item["path"] in expected:
                with tempfile.TemporaryDirectory() as scratch:
                    file = Path(scratch) / Path(item["path"]).name
                    file.write_bytes(data)
                    dependencies = dll_imports(file)
                assert dependencies == item["imports"]
                assert all(d in binaries or d in SYSTEM or d.startswith("api-ms-win-") for d in dependencies)
        assert archive.read(top+"runtime/python314._pth").replace(b"\r\n", b"\n") == b"python314.zip\nDLLs\n../application\n"
        with zipfile.ZipFile(io.BytesIO(archive.read(top+"runtime/python314.zip"))) as stdlib:
            expected_members = {m["path"]:m["sha256"] for m in manifest["stdlib_members"]}
            assert set(stdlib.namelist()) == set(expected_members)
            forbidden = {"site-packages", "test", "tests", "ensurepip", "idlelib", "venv", "_pyrepl"}
            for name, digest in expected_members.items():
                assert not forbidden.intersection(Path(name).parts)
                assert name.endswith(".py")
                assert hashlib.sha256(stdlib.read(name)).hexdigest() == digest
        project = Path(__file__).resolve().parents[1]
        for item in manifest["files"]:
            if item["path"].startswith("licenses/"):
                original = project / "licenses/portable" / Path(item["path"]).name
                assert original.is_file(), original
                assert archive.read(top+item["path"]) == original.read_bytes(), original
        assert archive.read(top+"launcher-source.cs") == (project/"tools/PortableLauncher.cs").read_bytes()
        reviewed = json.loads(archive.read(top+"licenses/native-inputs.json"))
        for item in reviewed["files"]:
            assert hashlib.sha256(archive.read(top+"runtime/"+item["path"])).hexdigest() == item["sha256"]
        upstream = json.loads(archive.read(top+"licenses/stdlib-upstream.json"))
        with zipfile.ZipFile(io.BytesIO(archive.read(top+"runtime/python314.zip"))) as stdlib:
            for item in upstream["files"]:
                data = stdlib.read(item["path"]).replace(b"\r\n", b"\n")
                assert hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest() == item["upstream_git_blob_sha1"]
        return {"status":"PASS", "native_files":len(expected), "all_files":len(manifest["files"])+1,
                "stdlib_members":len(expected_members), "unresolved_native_dependencies":0,
                "unreviewed_components":0, "runtime_site_packages":0,
                "zip_sha256":hashlib.sha256(Path(path).read_bytes()).hexdigest()}


if __name__ == "__main__":
    print(json.dumps(audit(sys.argv[1]), indent=2))
