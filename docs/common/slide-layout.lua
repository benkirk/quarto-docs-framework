-- pptx only. The theme's per-slide layout controls (.hcenter, .vcenter,
-- .center, scale="S", .fill, .full; see the vendored ncar-revealjs.lua) mean nothing
-- to pandoc's pptx writer, which drops slide classes. Carry them to
-- utils/slide_layout.py as one speaker-notes line,
--   ncar-layout: hcenter vcenter scale=1.4
-- which that script applies, and removes, after rendering. Pandoc merges
-- every notes Div on a slide, so the line joins any notes the author wrote.

if not quarto.doc.is_format("pptx") then
  return {}
end

local CLASSES = { hcenter = true, vcenter = true, center = true, fill = true, full = true }

local function take_layout(blk)
  local words, kept = {}, pandoc.List({})
  local h, v, fill, full = false, false, false, false
  for _, c in ipairs(blk.classes) do
    if CLASSES[c] then
      h = h or c == "hcenter" or c == "center"
      v = v or c == "vcenter" or c == "center"
      fill = fill or c == "fill"
      full = full or c == "full"
    else
      kept:insert(c)
    end
  end
  if h then table.insert(words, "hcenter") end
  if v then table.insert(words, "vcenter") end
  if fill then table.insert(words, "fill") end
  if full then table.insert(words, "full") end
  local scale = blk.attributes["scale"]
  if scale then
    blk.attributes["scale"] = nil
    if tonumber(scale) then table.insert(words, "scale=" .. scale) end
  end
  blk.classes = kept
  return #words > 0 and ("ncar-layout: " .. table.concat(words, " ")) or nil
end

function Pandoc(doc)
  local level = (PANDOC_WRITER_OPTIONS and PANDOC_WRITER_OPTIONS.slide_level) or 2
  local out, pending = pandoc.Blocks({}), nil
  local function flush()
    if pending then
      out:insert(pandoc.Div({ pandoc.Para({ pandoc.Str(pending) }) }, pandoc.Attr("", { "notes" })))
      pending = nil
    end
  end
  for _, b in ipairs(doc.blocks) do
    if (b.t == "Header" and b.level <= level) or b.t == "HorizontalRule" then flush() end
    if b.t == "Header" and b.level == level then pending = take_layout(b) end
    out:insert(b)
  end
  flush()
  doc.blocks = out
  return doc
end
