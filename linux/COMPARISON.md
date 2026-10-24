# Linux reference comparison

Reference: xkeyboard-config **2.46**, `us(altgr-intl)`.
Pinned sources and hashes: [reference/sources.json](reference/sources.json).

Compared 48 ANSI positions × 4 levels = 192 cells per platform.
Direct differences: macOS **0**, Windows **0**.

| Key | Level | Linux | macOS | Windows |
| --- | --- | --- | --- | --- |

## Dead-key sequences

Compared 977 explicit Linux Compose pairs. See [comparison.json](comparison.json)
for per-sequence differences. A missing explicit entry may be handled by
runtime fallback; it is not proof that the character cannot be typed.

Direct mappings and explicit compositions have different compatibility scopes; see the counts above.
Both generated layouts now use the pinned Linux reference; Windows omits unsupported KLC compositions.

## Scope

- Printable ANSI normal/Shift/AltGr/Shift+AltGr; excludes Control/CapsLock/Command/JIS/keypad/ISO extra key
- Explicit two-key en_US.UTF-8 Compose pairs; missing table entries are not proof of missing runtime output: toolkit fallback may apply
- Linux Compose can be customized by locale, toolkit and user; pinned here separately from xkeyboard-config
- No existing Mac/Windows layout or installer has been modified by this audit
