"""Download and administratively extract MSKLC; never install it."""
import argparse, hashlib, shutil, subprocess, urllib.request
from pathlib import Path

URL = "https://download.microsoft.com/download/6/f/5/6f5ce43a-e892-4fd1-b9a6-1a0cbb64e6e2/MSKLC.exe"
SHA256 = "cd12a6b08066133dc4ad71bdcaccf1492e3d9a1de93cf84b7b2824309f0d7255"

def main():
    p = argparse.ArgumentParser()
    p.add_argument("destination", type=Path)
    p.add_argument("--seven-zip", default=shutil.which("7z") or r"C:\Program Files\7-Zip\7z.exe")
    args = p.parse_args()
    dest = args.destination.resolve()
    dest.mkdir(parents=True, exist_ok=True)
    archive = dest / "MSKLC.exe"
    urllib.request.urlretrieve(URL, archive)
    if hashlib.sha256(archive.read_bytes()).hexdigest() != SHA256:
        raise SystemExit("MSKLC download hash mismatch")
    seven = args.seven_zip
    subprocess.run([seven, "x", str(archive), f"-o{dest / 'extract'}", "-y"], check=True)
    msi = dest / "extract/MSKLC/MSKLC.msi"
    result = subprocess.run(["msiexec.exe", "/a", str(msi), "/qn",
                             f"TARGETDIR={dest / 'sdk'}"])
    if result.returncode not in (0, 3010):
        raise SystemExit(f"MSKLC extraction failed: {result.returncode}")
    if not (dest / "sdk/bin/i386/kbdutool.exe").is_file():
        raise SystemExit("Missing kbdutool after extraction")
    print(dest / "sdk")

if __name__ == "__main__":
    main()
