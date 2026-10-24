"""Build native MSI packages and a diagnostic ZIP without the MSKLC GUI."""
import argparse, hashlib, json, os, re, shutil, struct, subprocess, tempfile, zipfile
from pathlib import Path
from verify_windows import verify

ROOT = Path(__file__).resolve().parents[1]
UPGRADES = {"x64": "39d0f985-b150-40da-9145-a0761047e2f7",
            "x86": "3898d48f-08f4-42cd-b9c2-252e499a7f1c"}

def version_number(value):
    match = re.fullmatch(r"v?(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-[0-9A-Za-z.-]+)?", value)
    if not match:
        raise ValueError("Version must be vMAJOR.MINOR.PATCH, optionally with a prerelease suffix")
    parts = tuple(map(int, match.groups()))
    if any(n > limit for n, limit in zip(parts, (255, 255, 65535))):
        raise ValueError("Version exceeds MSI limits (255.255.65535)")
    return ".".join(map(str, parts))

def pe_machine(path):
    data = path.read_bytes()
    offset = struct.unpack_from("<I", data, 0x3c)[0]
    if data[:2] != b"MZ" or data[offset:offset+4] != b"PE\0\0":
        raise ValueError(f"Invalid PE: {path}")
    return struct.unpack_from("<H", data, offset+4)[0]

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--msklc", type=Path, required=True)
    parser.add_argument("--wix", default="wix")
    parser.add_argument("--version", required=True)
    parser.add_argument("--output", type=Path, default=ROOT / "windows/dist/ci")
    args = parser.parse_args()
    version = version_number(args.version)
    label = "v" + args.version.removeprefix("v")
    out = args.output.resolve()
    if out.exists():
        raise SystemExit("Output already exists; choose an empty path to preserve previous builds")
    out.mkdir(parents=True)
    compiler = args.msklc.resolve() / "bin/i386/kbdutool.exe"
    source = ROOT / "windows/us-intl-altgr.klc"
    env = dict(os.environ, DOTNET_ROLL_FORWARD="Major")
    with tempfile.TemporaryDirectory(prefix="kbd-build-") as temporary:
        work = Path(temporary)
        dlls = {}
        for arch, switch, machine in (("x64", "-m", 0x8664), ("x86", "-x", 0x14c), ("wow64", "-o", 0x14c)):
            folder = work / arch
            folder.mkdir()
            result = subprocess.run([str(compiler), "-u", switch, str(source)], cwd=folder,
                                    capture_output=True, env=env)
            log = result.stdout + result.stderr
            (out / f"compile-{arch}.log").write_bytes(log)
            dll = folder / "usagrlx.dll"
            if result.returncode or not dll.is_file() or pe_machine(dll) != machine:
                raise SystemExit(f"Compilation failed for {arch}; inspect {out}")
            dlls[arch] = dll
        verification = {}
        binary_hashes = {arch: digest(path) for arch, path in dlls.items()}
        for arch in ("x64", "x86"):
            values = {"Version": version, "Arch": arch, "UpgradeCode": UPGRADES[arch],
                      "RegistryBitness": "always64" if arch == "x64" else "always32",
                      "NativeBitness": "always64" if arch == "x64" else "always32",
                      "NativeDirectory": "System64Folder" if arch == "x64" else "SystemFolder",
                      "NativeDll": str(dlls[arch]), "WowDll": str(dlls["wow64"])}
            command = [args.wix, "build", str(ROOT / "windows/installer/layout.wxs"),
                       "-arch", arch, "-o", str(out / f"us-intl-altgr-{label}-{arch}.msi")]
            for key, value in values.items():
                command += ["-d", f"{key}={value}"]
            result = subprocess.run(command, cwd=work, env=env, capture_output=True)
            (out / f"installer-{arch}.log").write_bytes(result.stdout + result.stderr)
            if result.returncode:
                raise SystemExit(f"MSI build failed for {arch}; inspect {out}")
            verification[arch] = verify(out / f"us-intl-altgr-{label}-{arch}.msi", arch, version,
                                        binary_hashes[arch], binary_hashes["wow64"])
    for relative in ("windows/us-intl-altgr.klc", "windows/us-intl-altgr.report.json",
                     "linux/comparison.json", "linux/COMPARISON.md", "linux/reference/sources.json",
                     "linux/reference/COPYING.xkeyboard-config"):
        shutil.copy2(ROOT / relative, out / Path(relative).name)
    shutil.copy2(ROOT / "windows/installer/INSTALL.txt", out / "INSTALL.txt")
    info = {"version": args.version, "msi_version": version, "compiled": True,
            "installation_tested": False, "signed": False, "msi_checks": verification,
            "dll_sha256": binary_hashes, "architectures": ["x64", "x86"],
            "klc_sha256": digest(source), "commit": os.environ.get("GITHUB_SHA"),
            "wix_version": subprocess.check_output([args.wix, "--version"], env=env, text=True).strip(),
            "files": {p.name: digest(p) for p in sorted(out.iterdir()) if p.is_file() and p.suffix != ".wixpdb"}}
    (out / "build-info.json").write_text(json.dumps(info, indent=2) + "\n", encoding="utf-8")
    package = out / f"us-intl-altgr-diagnostics-{label}.zip"
    with zipfile.ZipFile(package, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(out.iterdir()):
            if path.is_file() and path != package and path.suffix not in (".wixpdb", ".msi"):
                archive.write(path, path.name)
    (out / "SHA256SUMS.txt").write_text(
        "".join(f"{digest(p)}  {p.name}\n" for p in [package, *sorted(out.glob("*.msi"))]), encoding="ascii")
    print(package)

if __name__ == "__main__":
    main()
