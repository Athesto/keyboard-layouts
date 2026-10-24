"""Inspect MSI tables and administrative extraction, without installation."""
import ctypes, hashlib, subprocess, tempfile, time
from ctypes import wintypes
from pathlib import Path


def tables(path, query):
    msi = ctypes.WinDLL("msi")
    handle = wintypes.UINT
    msi.MsiOpenDatabaseW.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR, ctypes.POINTER(handle)]
    msi.MsiDatabaseOpenViewW.argtypes = [handle, wintypes.LPCWSTR, ctypes.POINTER(handle)]
    msi.MsiViewExecute.argtypes = [handle, handle]
    msi.MsiViewFetch.argtypes = [handle, ctypes.POINTER(handle)]
    msi.MsiRecordGetStringW.argtypes = [handle, handle, wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD)]
    msi.MsiCloseHandle.argtypes = [handle]
    database, view = handle(), handle()
    def check(code):
        if code:
            raise RuntimeError(f"MSI query error {code}: {query}")
    check(msi.MsiOpenDatabaseW(str(path), None, ctypes.byref(database)))
    try:
        check(msi.MsiDatabaseOpenViewW(database, query, ctypes.byref(view)))
        check(msi.MsiViewExecute(view, 0))
        rows = []
        while True:
            record = handle()
            code = msi.MsiViewFetch(view, ctypes.byref(record))
            if code == 259:
                return rows
            check(code)
            try:
                row = []
                for index in range(1, msi.MsiRecordGetFieldCount(record) + 1):
                    size = wintypes.DWORD(32767)
                    buffer = ctypes.create_unicode_buffer(size.value)
                    check(msi.MsiRecordGetStringW(record, index, buffer, ctypes.byref(size)))
                    row.append(buffer.value)
                rows.append(row)
            finally:
                msi.MsiCloseHandle(record)
    finally:
        if view.value:
            msi.MsiCloseHandle(view)
        msi.MsiCloseHandle(database)


def verify(package, arch, version, native_hash, wow_hash):
    properties = dict(tables(package, "SELECT `Property`, `Value` FROM `Property`"))
    if properties["ProductVersion"] != version:
        raise ValueError("Unexpected MSI product version")
    registry = tables(package, "SELECT `Root`, `Key`, `Name`, `Value` FROM `Registry`")
    expected = {"Layout File": "usagrlx.dll", "Layout Text": "US International — AltGr dead keys", "Layout Id": "0170"}
    if len(registry) != 3 or any(root != "2" or key != r"SYSTEM\CurrentControlSet\Control\Keyboard Layouts\a1700409" or expected.get(name) != value for root, key, name, value in registry):
        raise ValueError(f"Unexpected registration: {registry}")
    components = {row[0]: row[1:] for row in tables(package, "SELECT `Component`, `Directory_`, `Attributes` FROM `Component`")}
    directory, flags = components["NativeDll"]
    if directory != ("System64Folder" if arch == "x64" else "SystemFolder") or bool(int(flags) & 256) != (arch == "x64"):
        raise ValueError("Native DLL has wrong target directory or bitness")
    if arch == "x64" and (components["WowDll"][0] != "SystemFolder" or int(components["WowDll"][1]) & 256):
        raise ValueError("WOW64 DLL has wrong target directory or bitness")
    with tempfile.TemporaryDirectory(prefix="kbd-msi-check-") as temporary:
        for attempt in range(3):
            result = subprocess.run(["msiexec.exe", "/a", str(package), "/qn", f"TARGETDIR={temporary}"])
            if result.returncode != 1618 or attempt == 2:
                break
            time.sleep(2)  # Windows Installer may still be finishing another extraction.
        if result.returncode not in (0, 3010):
            raise ValueError(f"Administrative extraction failed: {result.returncode}")
        hashes = sorted(hashlib.sha256(p.read_bytes()).hexdigest() for p in Path(temporary).rglob("*.dll"))
        expected_hashes = sorted([native_hash, wow_hash] if arch == "x64" else [native_hash])
        if hashes != expected_hashes:
            raise ValueError("Extracted MSI payload differs from compiled DLLs")
    return {"registry_verified": True, "directories_verified": True, "extracted_dlls_verified": True}
