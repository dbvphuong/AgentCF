"""Build a self-contained Windows installer using local CPython and Windows .NET CSC.

No downloads or registry changes. Output is ignored runtime/client-build/CF Client Setup.exe.
"""
import importlib.metadata
import os
from pathlib import Path
import subprocess
import sys
import zipfile

from packaging.requirements import Requirement


ROOT = Path(__file__).resolve().parents[1]


def main():
    if sys.platform != "win32":
        raise SystemExit("Build CF Client on Windows x64")
    destination = ROOT / "runtime/client-build"
    destination.mkdir(parents=True, exist_ok=True)
    csc = Path(os.environ["WINDIR"]) / "Microsoft.NET/Framework64/v4.0.30319/csc.exe"
    if not csc.is_file():
        raise SystemExit("Windows .NET Framework C# compiler not found")
    source = ROOT / "infra/client/Bootstrap.cs"
    common = [str(csc), "/nologo", "/target:winexe", "/platform:x64", "/reference:System.Windows.Forms.dll", "/reference:System.Drawing.dll", "/reference:System.IO.Compression.dll"]
    launcher = destination / "CF Client.exe"
    subprocess.run([*common, f"/out:{launcher}", str(source)], check=True)
    payload = destination / "payload.zip"
    python_home = Path(sys.base_prefix)
    added = set()
    with zipfile.ZipFile(payload, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        def add(path, name):
            name = str(name).replace("\\", "/")
            if name not in added:
                archive.write(path, name); added.add(name)
        add(launcher, "CF Client.exe")
        for name in ("python.exe", "pythonw.exe", "LICENSE.txt"):
            add(python_home / name, "runtime/" + name)
        for path in python_home.glob("*.dll"):
            add(path, "runtime/" + path.name)
        for folder in ("Lib", "DLLs", "tcl"):
            for current, dirs, files in os.walk(python_home / folder):
                dirs[:] = [d for d in dirs if d not in {"__pycache__", "site-packages", "test", "tests", "idlelib", "ensurepip"}]
                for name in files:
                    path = Path(current) / name
                    if path.suffix not in {".pyc", ".pyo"}:
                        add(path, "runtime/" + path.relative_to(python_home).as_posix())
        pending, packages = ["httpx", "customtkinter", "darkdetect"], set()
        while pending:
            name = pending.pop()
            if name in packages:
                continue
            packages.add(name)
            dist = importlib.metadata.distribution(name)
            for entry in dist.files or []:
                if str(entry).startswith("..") or "__pycache__" in str(entry) or str(entry).endswith(".pyc"):
                    continue
                path = Path(dist.locate_file(entry))
                if path.is_file():
                    add(path, "runtime/Lib/site-packages/" + entry.as_posix())
            for requirement in dist.requires or []:
                req = Requirement(requirement)
                if req.marker is None or req.marker.evaluate():
                    pending.append(req.name)
        for path in (ROOT / "apps/client/src/agent_cf_client").rglob("*"):
            if path.is_file() and "__pycache__" not in str(path) and path.suffix not in {".pyc", ".pyo"}:
                add(path, "app/agent_cf_client/" + path.relative_to(ROOT / "apps/client/src/agent_cf_client").as_posix())
    installer = destination / "CF Client Setup.exe"
    subprocess.run([*common, "/define:INSTALLER", f"/resource:{payload},AgentCF.Payload", f"/out:{installer}", str(source)], check=True)
    print(f"Built {installer} ({installer.stat().st_size:,} bytes); {len(added)} files, dependencies: {', '.join(sorted(packages))}")


if __name__ == "__main__":
    main()
