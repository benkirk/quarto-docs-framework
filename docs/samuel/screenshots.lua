-- Screenshot slides, per format.
-- ::: shot-link <url> ::: under a screenshot: a muted link to the live page. HTML: that
-- slide's footer. PDF: a tiny line, bottom center. pptx: dropped, since anything after
-- an image splits the slide there (link the image itself instead: [![](x.png)](url)).
-- HTML also resolves a percentage image height against the whole slide, so {height="72%"}
-- (the beamer recipe) overflows; there it becomes the cap the theme gives mermaid.
local MUTED = '6B7C99'  -- $ncar-muted in ncar-revealjs.scss

function Image(el)
  local h = el.attributes.height
  if quarto.doc.is_format('revealjs') and h and h:match('%%$') then
    el.attributes.height = nil
    el.attributes.style = 'max-height: calc(600px * var(--ncar-fit, 1)); width: auto;'
    return el
  end
end

function Div(el)
  if not el.classes:includes('shot-link') then return nil end
  local url = pandoc.utils.stringify(el):gsub('%s', '')
  local label = url:gsub('^https?://', '')
  if quarto.doc.is_format('revealjs') then
    local link = pandoc.Link(label, url, '', pandoc.Attr('', {}, {style = 'color:#' .. MUTED}))
    return pandoc.Div({pandoc.Plain({link})}, pandoc.Attr('', {'footer'}))
  elseif quarto.doc.is_format('beamer') then
    local tex = label:gsub('([_%%#&])', '\\%1')
    return pandoc.RawBlock('latex', string.format(
      '\\begin{tikzpicture}[remember picture, overlay]\\node[anchor=south] at ([yshift=2.5mm]current page.south)'
      .. ' {\\tiny\\href{%s}{\\textcolor[HTML]{%s}{%s}}};\\end{tikzpicture}',
      url:gsub('%%', '\\%%'), MUTED, tex))
  end
  return {}
end
