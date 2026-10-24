# How to install

## 🍎 macOS

### US International — AltGr dead keys

File: `mac/us-intl-altgr.keylayout`.
On macOS, use Option for AltGr combinations. Quotes type normally;
Option + quote activates the acute dead key.

The original version is by xv0x7c0:
[osx-us-altgr-intl](https://github.com/xv0x7c0/osx-us-altgr-intl).
Related work: [Tobias Müller — US International on OS X][mac-reference].

[mac-reference]: https://www.twam.info/hardware/us-international-on-os-x

```sh
curl --fail --create-dirs -L \
  --output "$HOME/Library/Keyboard Layouts/us-intl-altgr.keylayout" \
  https://athesto.github.io/keyboard-layouts/mac/us-intl-altgr.keylayout
```

The download URL becomes available after these changes are published.
Then select **US International — AltGr dead keys** in macOS input sources.

## 🪟 Windows

Download the versioned x64 or x86 MSI from [Releases][releases] for your
system and run it. Then add the keyboard under English
(United States) in Windows language settings. Pre-releases are for testing.

See [windows/README.md](windows/README.md) for installation details,
compatibility limits and build instructions.

[releases]: https://github.com/Athesto/keyboard-layouts/releases

Reference project: https://github.com/thomasfaingnaert/win-us-intl-altgr

## 🐧 Linux

Linux includes **English (intl., with AltGr dead keys)**.
Use layout `us` and variant `altgr-intl`.

The definition is in `/usr/share/X11/xkb/symbols/us`.
See the [xkeyboard-config source][xkb-us].

[xkb-us]: https://gitlab.freedesktop.org/xkeyboard-config/xkeyboard-config/-/blob/master/symbols/us

### `intl` vs. `altgr-intl`

- **`intl`:** quotes act as dead keys. Type `'` then `a` for `á`, or `'`
  then Space for a literal quote.
- **`altgr-intl`:** quotes type normally. Use **AltGr+quote**, then **A → á**.
  **AltGr+A → á** also works directly.

### Reading the definition

Search for `xkb_symbols "altgr-intl"`. Its `include "us(intl)"` uses the
`xkb_symbols "intl"` block as a starting point, then overrides selected keys.

Inside `intl`, this inherited definition provides accented A:

```text
key <AC01> { [ a, A, aacute, Aacute ] };
```

The four values represent **normal, Shift, AltGr, and Shift+AltGr**.

Inside `altgr-intl`, this override restores normal quotes and moves their
dead-key behavior to AltGr:

```text
key <AC11> { [ apostrophe, quotedbl, dead_acute, dead_diaeresis ] };
```

`include "level3(ralt_switch)"` configures Right Alt as AltGr.

## Typing examples

Use Right Alt (AltGr) on Windows/Linux, or Option on macOS.

| Keys | Result |
| --- | --- |
| AltGr+A | á |
| AltGr+N | ñ |
| Shift+AltGr+N | Ñ |
| AltGr+quote, release, then A | á |
| Quote without AltGr | ' (types immediately) |

## TODO
- include command into button below "tab" and left of "1" for iso keyboard
