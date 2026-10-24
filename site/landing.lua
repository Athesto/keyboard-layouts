-- Pandoc owns Markdown parsing; the filter applies only landing-page rules.
local stringify = pandoc.utils.stringify
local icon = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true"><rect x="8" y="8" width="12" height="12" rx="3"></rect><path d="M16 8V6a2 2 0 0 0-2-2H6a2 2 0 0 0-2 2v8a2 2 0 0 0 2 2h2"></path></svg>'

function Pandoc(doc)
  local settings, blocks, hidden = {}, pandoc.List(), false
  for _, block in ipairs(doc.blocks) do
    local raw = block.t == 'RawBlock' and block.format == 'html' and block.text:match('^%s*(.-)%s*$') or ''
    if raw:match('^<!%-%- website\r?\n') then
      for line in raw:gmatch('[^\r\n]+') do
        local key, value = line:match('^%s*(%a+):%s*(.-)%s*$')
        if key == 'title' or key == 'description' or key == 'repository' then
          settings[key] = value:gsub('^"(.*)"$', '%1'):gsub("^'(.*)'$", '%1')
        end
      end
    elseif raw == '<!-- github-only:start -->' then
      assert(not hidden, 'Nested github-only block')
      hidden = true
    elseif raw == '<!-- github-only:end -->' then
      assert(hidden, 'Unmatched github-only end marker')
      hidden = false
    elseif not hidden then
      blocks:insert(block)
    end
  end
  assert(not hidden, 'Unclosed github-only block')
  doc.blocks = blocks

  local title, description = 'Markdown page', ''
  for i, block in ipairs(blocks) do
    if block.t == 'Header' and block.level == 1 then
      title = stringify(block.content)
      local intro = blocks[i + 1]
      if intro and intro.t == 'Para' then description = stringify(intro.content):gsub('%s+', ' ') end
      break
    end
  end
  doc.meta.pagetitle = pandoc.MetaString(settings.title ~= nil and settings.title ~= '' and settings.title or title)
  doc.meta.description = pandoc.MetaString(settings.description ~= nil and settings.description ~= '' and settings.description or description)

  -- The first paragraph consisting only of links becomes the download row.
  for _, block in ipairs(blocks) do
    if block.t == 'Para' then
      local links, only_links = {}, true
      for _, inline in ipairs(block.content) do
        if inline.t == 'Link' then table.insert(links, inline)
        elseif inline.t ~= 'Space' and inline.t ~= 'SoftBreak' then only_links = false end
      end
      if only_links and #links > 0 then
        for i, link in ipairs(links) do
          link.attributes.role = 'button'
          link.classes = pandoc.List(i == 1 and {'button', 'primary'} or {'button', 'secondary', 'outline'})
        end
        -- Keep the paragraph wrapper for the same CSS layout as the local reader.
        for i, candidate in ipairs(doc.blocks) do
          if candidate == block then doc.blocks[i] = pandoc.Div({block}, pandoc.Attr('', {'downloads'})); break end
        end
        break
      end
    end
  end

  local repository = settings.repository and settings.repository:gsub('/$', '') or nil
  if repository then assert(repository:match('^https?://'), 'Repository must use HTTP or HTTPS') end
  return doc:walk({
    Link = function(link)
      local target = link.target
      if repository and not target:match('^[%a][%w+.-]*:') and not target:match('^[/#]')
        and (target:match('%.md$') or target:match('%.md[?#]')) then
        link.target = repository .. '/blob/main/' .. target
      end
      return link
    end,
    CodeBlock = function(block)
      block.classes:insert('snippet')
      local header = '<div class="snippet-header"><span>Code</span><button type="button" class="copy-button secondary outline" aria-label="Copy code"><span class="copy-feedback" role="status"></span>' .. icon .. '</button></div>'
      return {pandoc.RawBlock('html', header), block}
    end
  })
end
