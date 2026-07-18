-- Strip the raw-HTML <figure>/</figure> wrappers quarto emits around
-- rendered diagrams (e.g. mermaid PNGs) when writing pptx.  Pandoc's pptx
-- writer ignores raw HTML, but its slide-layout chooser counts it as text
-- content -- the closing tag even lands in the same paragraph as the image
-- -- so a columns slide holding a bare diagram reads as text+content and
-- is demoted to the Comparison layout, whose small per-column heading box
-- then swallows the other column's text.  Removing the wrappers restores
-- the Two Content layout.  HTML formats keep their <figure> semantics.
--
-- Quarto emits the tags as raw *inlines* (`<figure>`{=html}) wrapped in
-- Paras, so filter paragraphs; the RawBlock case is kept for good measure.

local function is_figure_tag(el)
  return el.format == "html"
     and (el.text:match("^<figure") or el.text:match("^</figure"))
end

function RawBlock(el)
  if FORMAT == "pptx" and is_figure_tag(el) then
    return {}
  end
end

function Para(el)
  if FORMAT ~= "pptx" then
    return nil
  end
  local kept, changed = {}, false
  for _, il in ipairs(el.content) do
    if il.t == "RawInline" and is_figure_tag(il) then
      changed = true
    else
      table.insert(kept, il)
    end
  end
  if not changed then
    return nil
  end
  while #kept > 0 and (kept[1].t == "SoftBreak" or kept[1].t == "Space") do
    table.remove(kept, 1)
  end
  while #kept > 0 and (kept[#kept].t == "SoftBreak" or kept[#kept].t == "Space") do
    table.remove(kept)
  end
  if #kept == 0 then
    return {}
  end
  return pandoc.Para(kept)
end
