"""Build a Windows folder/ZIP with a self-authored .NET launcher and official CPython.

No pip packager is imported. Site packages, pip, scientific DLLs and build tools
are never copied. Source interpreter must be the audited official 3.14.7 build.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import zipfile
from pe_imports import dll_imports

ROOT = Path(__file__).resolve().parents[1]
NATIVE = ["_ctypes.pyd", "_tkinter.pyd", "_queue.pyd", "_socket.pyd", "select.pyd",
          "unicodedata.pyd", "libffi-8.dll", "libtommath.dll", "tcl90.dll", "tcl9tk90.dll", "zlib1.dll"]
SYSTEM = {"advapi32.dll", "bcrypt.dll", "comctl32.dll", "comdlg32.dll", "gdi32.dll",
          "imm32.dll", "iphlpapi.dll", "kernel32.dll", "mscoree.dll", "netapi32.dll", "ole32.dll", "oleaut32.dll", "rpcrt4.dll",
          "shell32.dll", "user32.dll", "userenv.dll", "version.dll", "winspool.drv", "ws2_32.dll"}


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--python-root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--version", default="1.0.1")
    args = parser.parse_args()
    source, out = args.python_root.resolve(), args.output.resolve()
    metadata = json.loads((source / "__install__.json").read_text(encoding="utf-8"))
    assert metadata["id"] == "pythoncore-3.14-64" and metadata["sort-version"] == "3.14.7"
    reviewed = json.loads((ROOT / "licenses/portable/native-inputs.json").read_text(encoding="utf-8"))
    for item in reviewed["files"]:
        assert digest(source / item["path"]) == item["sha256"], ("Runtime changed; review required", item["path"])
    # Exact reviewed platform; never silently package a different DLL collection.
    assert (ROOT / "licenses/portable/CPython-incorporated-software.rst").is_file()
    out.mkdir(parents=True, exist_ok=False)
    runtime = out / "runtime"
    runtime.mkdir()
    (runtime / "DLLs").mkdir()
    for name in ["python.exe", "python314.dll", "vcruntime140.dll"]:
        shutil.copy2(source / name, runtime / name)
    for name in NATIVE:
        shutil.copy2(source / "DLLs" / name, runtime / "DLLs" / name)
    # Full stdlib .py implementation, without test suites, tools, assets or third-party packages.
    excluded = {"site-packages", "__pycache__", "test", "tests", "idlelib", "turtledemo", "ensurepip", "venv", "_pyrepl"}
    upstream = json.loads((ROOT / "licenses/portable/stdlib-upstream.json").read_text(encoding="utf-8"))
    reviewed_stdlib = {item["path"]:item["upstream_git_blob_sha1"] for item in upstream["files"]}
    with zipfile.ZipFile(runtime / "python314.zip", "x", compression=zipfile.ZIP_DEFLATED) as archive:
        for file in sorted((source / "Lib").rglob("*.py")):
            relative = file.relative_to(source / "Lib")
            if not excluded.intersection(relative.parts):
                content = file.read_bytes().replace(b"\r\n", b"\n")
                blob = hashlib.sha1(b"blob " + str(len(content)).encode() + b"\0" + content).hexdigest()
                assert reviewed_stdlib.get(relative.as_posix()) == blob, ("Unreviewed stdlib source", relative)
                archive.write(file, relative.as_posix())
    (runtime / "python314._pth").write_text("python314.zip\nDLLs\n../application\n", encoding="ascii")
    app = out / "application"
    app.mkdir()
    for name in ["app.py", "startup_check.py"]:
        shutil.copy2(ROOT / name, app / name)
    for name in ["core", "ui", "io_utils"]:
        shutil.copytree(ROOT / name, app / name, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    for name in ["LICENSE", "NOTICE", "THIRD_PARTY_LICENSES.md", "PORTABLE_LICENSES.md", "PORTABLE_README.txt"]:
        shutil.copy2(ROOT / name, out / name)
    shutil.copytree(ROOT / "licenses/portable", out / "licenses")
    shutil.copy2(source / "LICENSE.txt", out / "licenses/CPython-Windows-3.14.7.txt")
    shutil.copy2(ROOT / "tools/PortableLauncher.cs", out / "launcher-source.cs")
    compiler = Path(os.environ["WINDIR"]) / "Microsoft.NET/Framework64/v4.0.30319/csc.exe"
    subprocess.run([str(compiler), "/nologo", "/target:winexe", "/platform:x64", "/optimize+",
                    "/reference:System.Windows.Forms.dll", f"/out:{out / 'FFT Playground.exe'}",
                    str(ROOT / "tools/PortableLauncher.cs")], check=True)
    bundled = {p.name.lower() for p in out.rglob("*") if p.suffix.lower() in (".dll", ".pyd", ".exe")}
    manifest = {"application": "FFT Playground " + args.version, "upstream": metadata["url"],
                "upstream_archive_sha256": metadata["hash"]["sha256"],
                "runtime_provenance": "official installed distribution; native/source file hashes below",
                "isolation": "python314._pth; site packages disabled; no installed Python needed",
                "files": []}
    manifest["build_tools"] = {"packager": "original Python stdlib script; no pip build packages",
                               "compiler": "Windows .NET Framework csc 14.8.10001.0 (not redistributed)"}
    manifest["managed_platform_references"] = ["mscorlib 4.0.0.0", "System 4.0.0.0", "System.Windows.Forms 4.0.0.0"]
    with zipfile.ZipFile(runtime / "python314.zip") as archive:
        manifest["stdlib_members"] = [{"path": name, "sha256": hashlib.sha256(archive.read(name)).hexdigest()}
                                      for name in archive.namelist()]
    manifest["component_versions"] = {"CPython": "3.14.7", "Tcl": "9.0.4", "Tk": "9.0.4",
                                      "libffi": "3.4.4", "LibTomMath": "Tcl9.0.4.0 snapshot",
                                      "Tcl zlib": "1.3.2", "CPython zlib-ng": "2.2.4",
                                      "Microsoft CRT": "14.51.36247.0"}
    for file in sorted(out.rglob("*")):
        if not file.is_file(): continue
        entry = {"path": file.relative_to(out).as_posix(), "sha256": digest(file), "bytes": file.stat().st_size}
        if file.suffix.lower() in (".exe", ".dll", ".pyd"):
            entry["imports"] = dll_imports(file)
            for dependency in entry["imports"]:
                assert dependency in bundled or dependency in SYSTEM or dependency.startswith("api-ms-win-"), (file, dependency)
        manifest["files"].append(entry)
    (out / "MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    target = out.parent / (out.name + ".zip")
    with zipfile.ZipFile(target, "x", compression=zipfile.ZIP_DEFLATED) as archive:
        for file in sorted(out.rglob("*")):
            if file.is_file(): archive.write(file, out.name + "/" + file.relative_to(out).as_posix())
    print(json.dumps({"directory": str(out), "zip": str(target), "zip_sha256": digest(target),
                      "size": target.stat().st_size, "files": len(manifest["files"])}))


if __name__ == "__main__":
    main()
