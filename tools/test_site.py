"""Check the actual Pandoc output and landing-page rules (stdlib only)."""
from html.parser import HTMLParser
from pathlib import Path
import os
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
PANDOC = os.environ.get("PANDOC") or shutil.which("pandoc")
if not PANDOC:
    local = Path.home() / "AppData/Local/Pandoc/pandoc.exe"
    PANDOC = str(local) if local.is_file() else None


class Page(HTMLParser):
    def __init__(self, text):
        super().__init__(convert_charrefs=True)
        self.elements = []
        self.title = ""
        self.in_title = False
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        self.elements.append((tag, dict(attrs)))
        if tag == "title":
            self.in_title = True

    def handle_endtag(self, tag):
        if tag == "title":
            self.in_title = False

    def handle_data(self, data):
        if self.in_title:
            self.title += data

    def attrs(self, tag):
        return [attrs for name, attrs in self.elements if name == tag]


def convert(markdown):
    result = subprocess.run(
        [PANDOC, "--from=gfm", "--to=html5", "--standalone",
         "--template=site/template.html", "--lua-filter=site/landing.lua",
         "--syntax-highlighting=none", "--wrap=none"],
        input=markdown, encoding="utf-8", capture_output=True, cwd=ROOT)
    return result


@unittest.skipUnless(PANDOC, "Pandoc is only needed for site checks")
class SiteTests(unittest.TestCase):
    def test_repository_page_is_static_and_assets_exist(self):
        result = convert((ROOT / "README.md").read_text(encoding="utf-8"))
        self.assertEqual(result.returncode, 0, result.stderr)
        page = Page(result.stdout)
        self.assertEqual(page.title, "US International — AltGr dead keys")
        description = next(a["content"] for a in page.attrs("meta") if a.get("name") == "description")
        self.assertTrue(description.startswith("Keep the familiar US layout"))
        self.assertEqual(len(page.attrs("table")), 2)
        self.assertEqual(len([a for a in page.attrs("a") if a.get("role") == "button"]), 2)
        self.assertEqual(len([a for a in page.attrs("button") if a.get("aria-label") == "Copy code"]), 1)
        self.assertFalse(any("hidden" in a for _, a in page.elements))
        self.assertNotIn("markdownit", result.stdout)
        self.assertNotIn("fetch(", result.stdout)
        self.assertNotIn("github-only", result.stdout)
        self.assertNotIn('id="todo"', result.stdout)
        for image in page.attrs("img"):
            self.assertTrue((ROOT / image["src"]).is_file(), image["src"])
        links = [a.get("href", "") for a in page.attrs("a")]
        self.assertIn("https://github.com/Athesto/keyboard-layouts/blob/main/windows/README.md", links)
        self.assertIn("https://athesto.github.io/keyboard-layouts/mac/us-intl-altgr.keylayout", links)

    def test_metadata_precedence_fallback_and_escaping(self):
        for metadata, title, description in [
            ('title: Custom & "title"\ndescription: Explicit <summary>', 'Custom & "title"', 'Explicit <summary>'),
            ('', 'Heading', 'First paragraph with code.'),
        ]:
            with self.subTest(metadata=metadata):
                source = '<!-- website\n' + metadata + '\n-->\n\n# Heading\n\nFirst **paragraph** with `code`.\n'
                result = convert(source)
                self.assertEqual(result.returncode, 0, result.stderr)
                page = Page(result.stdout)
                self.assertEqual(page.title, title)
                actual = next(a["content"] for a in page.attrs("meta") if a.get("name") == "description")
                self.assertEqual(actual, description)

    def test_excluded_blocks_and_code_examples(self):
        source = '# Heading\n\nVisible.\n\n<!-- github-only:start -->\n## PRIVATE SECTION\n<!-- github-only:end -->\n\n```html\n<!-- github-only:start -->\n```\n'
        result = convert(source)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn('PRIVATE SECTION', result.stdout)
        self.assertIn('&lt;!-- github-only:start --&gt;', result.stdout)
        self.assertNotEqual(convert('# Heading\n\n<!-- github-only:start -->\nUnclosed.').returncode, 0)


if __name__ == "__main__":
    unittest.main()
