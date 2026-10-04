-- pptx only. Pandoc's pptx writer moves anything that follows a table or an
-- image (a rendered diagram arrives as a Para holding one Image) onto an
-- untitled continuation slide; a code block is text and does not split. The
-- paragraphs after one table or image (a footnote, a remark) move into its
-- caption, which pandoc draws at the slide's foot. Anything else after it
-- (a list, code, a second table) is left to split: an extra slide is visible,
-- where text in a 100% column wrapper was silently dropped. A slide that
-- already holds a columns div is left alone. Runs after notes-last.lua.

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

local function is_text(blk)
  return (blk.t == "Para" or blk.t == "Plain") and not is_image_para(blk)
end

-- The caption of a table or figure, or nil when blk has neither.
local function caption_of(blk)
  if blk.t == "Table" or blk.t == "Figure" then
    return blk.caption.long
  end
  return nil
end

-- blk with paras appended to its caption; an image paragraph becomes a figure.
-- A div holding exactly one table or figure is folded into that block.
local function fold(blk, paras)
  local cap = caption_of(blk)
  if cap then
    cap:extend(paras)
    return blk
  end
  if is_image_para(blk) then
    -- pandoc's pptx writer captions a figure from its image's text, so the
    -- paragraphs go there too, one line each
    local text = pandoc.Inlines({})
    for k, para in ipairs(paras) do
      if k > 1 then text:insert(pandoc.LineBreak()) end
      text:extend(para.content)
    end
    local content = blk.content:map(function(il)
      if il.t == "Image" then il.caption = text end
      return il
    end)
    return pandoc.Figure({ pandoc.Plain(content) }, { long = paras })
  end
  if blk.t == "Div" then
    local inner = nil
    for i, b in ipairs(blk.content) do
      if is_nontext(b) then
        if inner then return nil end
        inner = i
      end
    end
    if inner then
      local folded = fold(blk.content[inner], paras)
      if folded then
        blk.content[inner] = folded
        return blk
      end
    end
  end
  return nil
end

-- The body with trailing paragraphs folded into the one table or image they
-- follow, or the body unchanged when that is not its shape.
local function fold_trailing(body)
  local at = nil
  for i, blk in ipairs(body) do
    if blk.t == "Div" and blk.classes:includes("columns") then
      return body
    end
    if is_nontext(blk) then
      if at then return body end
      at = i
    end
  end
  if not at or at == #body then
    return body
  end
  local paras = pandoc.Blocks({})
  for i = at + 1, #body do
    if not is_text(body[i]) then return body end
    paras:insert(body[i])
  end
  local folded = fold(body[at], paras)
  if not folded then return body end
  local out = pandoc.Blocks({})
  for i = 1, at - 1 do out:insert(body[i]) end
  out:insert(folded)
  return out
end

function Pandoc(doc)
  local level = (PANDOC_WRITER_OPTIONS and PANDOC_WRITER_OPTIONS.slide_level) or 2
  local out = pandoc.Blocks({})
  local body, notes, in_slide = pandoc.Blocks({}), pandoc.Blocks({}), false
  local function flush()
    out:extend(in_slide and fold_trailing(body) or body)
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
