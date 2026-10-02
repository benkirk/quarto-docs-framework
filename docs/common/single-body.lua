-- pptx only. Pandoc's pptx writer moves anything that follows a table or an
-- image (a rendered diagram arrives as a Para holding one Image) onto an
-- untitled continuation slide; a code block is text and does not split.
-- Wrapping the slide's body in one 100% column keeps it on one slide. A slide
-- that already holds a columns div is left alone: content after one also
-- splits, but moving it changes the layout. Runs after notes-last.lua.

if not quarto.doc.is_format("pptx") then
  return {}
end

-- Speaker notes, and the hidden div quarto appends, stay outside the wrapper.
local function is_aside(blk)
  return blk.t == "Div" and (blk.classes:includes("notes") or blk.classes:includes("hidden"))
end

local function is_image_para(blk)
  if blk.t ~= "Para" and blk.t ~= "Plain" then
    return false
  end
  local images = 0
  for _, il in ipairs(blk.content) do
    if il.t == "Image" then
      images = images + 1
    elseif il.t ~= "Space" and il.t ~= "SoftBreak" and il.t ~= "LineBreak" then
      return false
    end
  end
  return images > 0
end

local function is_nontext(blk)
  if blk.t == "Table" or blk.t == "Figure" or is_image_para(blk) then
    return true
  end
  if blk.t == "Div" then
    for _, inner in ipairs(blk.content) do
      if is_nontext(inner) then return true end
    end
  end
  return false
end

local function needs_wrap(body)
  local seen = false
  for _, blk in ipairs(body) do
    if blk.t == "Div" and blk.classes:includes("columns") then
      return false
    end
    if seen then
      return true
    end
    seen = is_nontext(blk)
  end
  return false
end

local function wrap(body)
  local column = pandoc.Div(body, pandoc.Attr("", { "column" }, { width = "100%" }))
  return pandoc.Div({ column }, pandoc.Attr("", { "columns" }))
end

function Pandoc(doc)
  local level = (PANDOC_WRITER_OPTIONS and PANDOC_WRITER_OPTIONS.slide_level) or 2
  local out = pandoc.Blocks({})
  local body, notes, in_slide = pandoc.Blocks({}), pandoc.Blocks({}), false
  local function flush()
    if in_slide and needs_wrap(body) then
      out:insert(wrap(body))
    else
      out:extend(body)
    end
    out:extend(notes)
    body, notes = pandoc.Blocks({}), pandoc.Blocks({})
  end
  for _, blk in ipairs(doc.blocks) do
    if (blk.t == "Header" and blk.level <= level) or blk.t == "HorizontalRule" then
      flush()
      out:insert(blk)
      in_slide = blk.t == "Header" and blk.level == level
    elseif is_aside(blk) then
      notes:insert(blk)
    else
      body:insert(blk)
    end
  end
  flush()
  doc.blocks = out
  return doc
end
