# Landing page

README.md is the content source. `template.html` provides Pico CSS (17px,
900px maximum width) and the copy button. `landing.lua` applies the README
metadata, excludes github-only blocks and formats the download links.
No Python or Node packages are needed to generate the site.

With Pandoc 3.12.1 installed, run from the repository root:

```sh
pandoc README.md --from=gfm --to=html5 --standalone --template=site/template.html --lua-filter=site/landing.lua --syntax-highlighting=none --wrap=none --output=index.html
```

Open the generated `index.html` directly. Content, title and description
are in the HTML; JavaScript only copies code. Pico CSS uses a pinned CDN.
The generated file is ignored by Git. Edit the README or template instead.
`index-backup.html` preserves the earlier browser-based Markdown reader.
`index-pandoc.html`, if present locally, is an earlier ignored preview.

Optional README metadata (not YAML; one plain key: value per line):

```md
<!-- website
repository: https://github.com/example/project
title: Optional page title
description: Optional description
-->
```

The first H1 supplies the title if omitted; its following paragraph
supplies the description. Relative Markdown links use the repository's
main branch when repository is provided. Image and layout paths stay local.
The first paragraph made entirely of links becomes the download row.

Whole blocks between github-only:start and github-only:end HTML comments
are omitted from the web page. Examples inside fenced code stay intact.

The Pages workflow generates index.html in the runner's repository root,
then packages tracked repository files plus that HTML in a temporary folder.
This folder becomes the root of the published site; URLs such as
`mac/us-intl-altgr.keylayout` and `pictures/us-intl-altgr.png` stay unchanged.
The backup reader is not deployed. Publishing does not create a release
or commit generated HTML back into the repository.
