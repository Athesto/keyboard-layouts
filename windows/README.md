# US International — AltGr dead keys

The same layout name is used across platforms. The printable ANSI layout
is generated from the pinned Linux reference,
**xkeyboard-config 2.46, us(altgr-intl)**. No PowerToys, Kanata or Keyman is
required at runtime.

## Install and test

1. Download the Windows ZIP from [Releases][releases].
   Pre-releases are intended for testing.
2. Extract it and run **us-intl-altgr-x64.msi** on Intel/AMD 64-bit Windows,
   or **us-intl-altgr-x86.msi** on 32-bit Windows. ARM64 is unsupported.
   Administrator approval is required. Packages are unsigned.
3. Add **US International — AltGr dead keys** under English
   (United States). Sign out and back in if it does not appear.
4. Test quotes, AltGr+A/E/I/O/U, AltGr+N, Shift+AltGr+N,
   AltGr+slash and Shift+AltGr+1. Check Ctrl+C/V in your applications.

The MSI registers layout `a1700409` and installs `usagrlx.dll`. It does not
change your default input source. Remove the input source before
uninstalling the package from Installed apps. Restart if requested.
Uninstall any older MSKLC-generated `usagrlx` package and restart before
using the automated MSI: the old installer has a separate product identity.
The installer stops if it detects a conflicting layout or an older DLL.

Files under `dist/` are local build outputs and are not tracked in Git.
Installation and interactive typing still need testing.

## Compatibility and limitations

- 48 ANSI positions x 4 levels = **192 direct assignments**, all matching
  Linux. Quotes type normally. Dead keys require AltGr.
- Mac represents all 977 explicit two-key Compose pairs in our reference.
- Windows represents **853** of those pairs; **124** multi-character or
  non-BMP results cannot be expressed by the KLC DEADKEY format and are
  omitted. See [us-intl-altgr.report.json](us-intl-altgr.report.json).
- Command, Control, Caps Lock, JIS and runtime fallback are platform-specific.
  This is not a claim of full Linux runtime or toolkit equivalence.
- Windows treats AltGr as Ctrl+Alt; shortcuts using that combination can
  interact with the layout. Check your editor and terminal.

Full comparison: [Linux audit](../linux/COMPARISON.md).

## Validation status

Local DLL compilation and MSI content checks passed. The MSI checks verify
registration, destination directories, bitness and extracted DLL hashes.
They do not install the keyboard or verify interactive typing.

A separate MSKLC GUI validation of the Linux-derived source reported
**0 errors** and **1,161 warnings**:

| Warning category | Count | Meaning |
| --- | --- | --- |
| Outside Windows-1252 | 787 | Legacy non-Unicode apps may not support it |
| Repeated output | 15 | Intentional duplicate symbols in Linux |
| Compose input not on direct keyboard | 359 | Linux tables cover more letters |

These are source-validation results, not MSI installation-test results.
Compose inputs include letters not directly assigned to this ANSI keyboard.
Automated packages include compiler logs and `build-info.json`; the earlier
GUI validation is a separate check and is not rerun by the workflow.

## Rebuild from Linux

With Python 3 (standard library only), from the repository root:

```sh
python tools/generate_from_linux.py
python tools/compare_linux.py
python -m unittest discover -s tools -p 'test_*.py'
```

This generates BOTH the Mac and Windows sources from Linux. Do not edit
the generated main layouts by hand.
`mac_to_klc.py` remains a compatibility command for this same pipeline.

For a manual GUI build, install [MSKLC 1.4][msklc], open the KLC and use
Project > Validate Layout, then Project > Build DLL and Setup Package.

## Automated builds and releases

The workflow `.github/workflows/release.yml` runs on pull requests, manual
runs and pushed `v*` tags. It regenerates and checks the Linux-derived
sources, then builds x64/x86 DLLs with MSKLC 1.4 and MSI packages with
WiX 5.0.2. The MSKLC download is checked against a pinned SHA-256.
WiX and MSKLC are build tools; end users only run the MSI.

MSI verification inspects registry entries, system directories and bitness,
then administratively extracts each package and compares its DLL hashes
with the compiled originals. It does not install the layout or test typing.

Pull requests and manual runs upload an Actions artifact without publishing.
To publish a **pre-release**, push a tag such as `v0.1.0-rc.1` at the tested
commit. The workflow attaches MSI files, a ZIP, SHA256SUMS.txt and build-info.
Existing release assets are never overwritten by the publishing step.
If a release already exists, publication fails instead of replacing it.

After installation and typing tests, edit that GitHub release and clear
**Set as a pre-release**. Keep its tag and assets: promotion needs no rebuild
or second tag. A future changed build should use a new version.

MSI versions use the numeric MAJOR.MINOR.PATCH portion of the tag, within
255.255.65535. Different `-rc` suffixes share that MSI version; uninstall a
previous candidate before testing another candidate with the same number.
Promoting the already-tested candidate requires no reinstall.

Local headless build, with MSKLC and WiX available:

```sh
python tools/build_windows.py --msklc "PATH_TO_MSKLC" --version v0.1.0-rc.1
```

Output defaults to `windows/dist/ci/`. Use `--output` for a new destination;
the builder refuses to overwrite an existing directory. The ZIP includes
build logs, compatibility reports, license and source metadata. MSI and DLL
bytes may vary between builds; promote the tested assets without rebuilding.

[msklc]: https://www.microsoft.com/en-us/download/details.aspx?id=102134
[releases]: https://github.com/Athesto/keyboard-layouts/releases

## File formats

- Mac XML: UTF-8, LF; maxout matches the generated composition lengths.
- Windows KLC: UTF-16 LE with BOM, CRLF.
- DLL/MSI/EXE/ZIP: binary; never edit as text.
- Pinned Linux reference files: original bytes, checked against SHA-256.

`.gitattributes` disables Git newline conversion for KLC and pinned sources.
Generation is deterministic: repeated runs produce byte-identical sources.
Regeneration does NOT rebuild the installer; build-info records the KLC
hash so a stale package can be detected.
