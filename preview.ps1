docker run --rm -it `
  --volume "${PSScriptRoot}:/docs" `
  --volume "${PSScriptRoot}/pictures:/docs/docs/pictures:ro" `
  --volume "${PSScriptRoot}/mac:/docs/docs/mac:ro" `
  --publish 127.0.0.1:8000:8000 `
  zensical/zensical:0.0.72 `
  serve --config-file zensical.toml --dev-addr 0.0.0.0:8000
