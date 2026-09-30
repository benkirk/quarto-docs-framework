-- A linked image, [![](shot.png)](https://...), gets a visible link line on
-- its slide in every format, so a viewer knows the picture opens the live page:
--   revealjs  the slide's footer, muted
--   beamer    a tiny muted line, bottom center (a TikZ overlay); a linked
--             image taller than 68% is capped there to keep the line clear
--   pptx      nothing here: anything after an image splits the slide, so
--             utils/link_captions.py adds a caption box after rendering
-- The picture itself is the link in all three. One line per slide: the first
-- linked image's URL.

local MUTED = "6B7C99"  -- the theme's muted gray ($ncar-muted)
local PDF_MAX = 68      -- % height that leaves the PDF foot line clear of a 16:9 shot

-- PDF: a linked 16:9 screenshot at {height="72%"} reaches the page foot, under
-- the link line; cap it so authors keep one recipe for every format.
function Link(link)
  if not quarto.doc.is_format("beamer") then return nil end
  for _, il in ipairs(link.content) do
    local pct = il.t == "Image" and tonumber((il.attributes.height or ""):match("^([%d.]+)%%$"))
    if pct and pct > PDF_MAX then il.attributes.height = PDF_MAX .. "%" end
  end
  return link
end

local function image_link(blk)
  local url
  pandoc.walk_block(blk, {
    Link = function(link)
      if url then return end
      for _, il in ipairs(link.content) do
        if il.t == "Image" then url = link.target; return end
      end
    end,
  })
  return url
end

local function link_line(url)
  local label = url:gsub("^https?://", "")
  if quarto.doc.is_format("revealjs") then
    local link = pandoc.Link(label, url, "", pandoc.Attr("", {}, { style = "color:#" .. MUTED }))
    return pandoc.Div({ pandoc.Plain({ link }) }, pandoc.Attr("", { "footer" }))
  elseif quarto.doc.is_format("beamer") then
    local tex = label:gsub("([_%%#&~^$])", "\\%1")
    return pandoc.RawBlock("latex", string.format(
      "\\begin{tikzpicture}[remember picture, overlay]"
        .. "\\node[anchor=south] at ([yshift=1mm]current page.south)"
        .. " {\\tiny\\href{%s}{\\textcolor[HTML]{%s}{%s}}};\\end{tikzpicture}",
      (url:gsub("[%%#]", "\\%0")), MUTED, tex))
  end
end

function Pandoc(doc)
  if not (quarto.doc.is_format("revealjs") or quarto.doc.is_format("beamer")) then
    return nil
  end
  local level = PANDOC_WRITER_OPTIONS.slide_level or 2
  local out, url = pandoc.Blocks({}), nil
  local function close_slide()
    if url then out:insert(link_line(url)) end
    url = nil
  end
  for _, blk in ipairs(doc.blocks) do
    if (blk.t == "Header" and blk.level <= level) or blk.t == "HorizontalRule" then
      close_slide()
    else
      url = url or image_link(blk)
    end
    out:insert(blk)
  end
  close_slide()
  doc.blocks = out
  return doc
end
