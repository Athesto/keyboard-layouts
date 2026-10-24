# Pinned Linux reference

`reference/us` is the unmodified symbols/us from xkeyboard-config 2.46.
`reference/level3` and `reference/types-extra` preserve supporting definitions.
`sources.json` in that directory records upstream URLs, revisions and hashes.
Compose is pinned separately from libX11; keysyms come from libxkbcommon.

`us-intl-altgr.json` is generated, not an upstream file. It resolves the
us(intl) -> us(altgr-intl) inheritance and records the canonical ANSI mappings
and explicit two-key dead-key compositions used to generate both platforms.
Space uses the normal PC keyboard behavior because symbols/us does not
redefine it. The initial Mac template retains platform-only maps; its ANSI
four-level values and active Compose actions are generated from Linux.

From the repository root, regenerate the outputs and run all tests:

```sh
python tools/generate_from_linux.py
python tools/compare_linux.py
python -m unittest discover -s tools -p 'test_*.py'
```

See COMPARISON.md and comparison.json for scope and remaining differences.
Do not edit the pinned reference files: their hashes are checked first.
