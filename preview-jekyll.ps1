docker run --rm -it `
  --volume "${PSScriptRoot}:/srv/jekyll" `
  --publish 127.0.0.1:4000:4000 `
  --publish 127.0.0.1:35729:35729 `
  jekyll/jekyll:pages `
  jekyll serve --host 0.0.0.0 --livereload --force_polling
