-- Move each slide's speaker notes (::: {.notes}) to the end of the slide
-- when writing pptx.  Pandoc's pptx writer only picks the Two Content
-- layout when a slide's body *starts* with a columns div, so notes written
-- before the columns split the slide into a title-only slide plus an
-- untitled continuation.  Notes after any content (images and tables
-- included) are harmless, so last is always safe.  Other formats: untouched.

local function is_notes(blk)
  return blk.t == "Div" and blk.classes:includes("notes")
end

function Pandoc(doc)
  if FORMAT ~= "pptx" then
    return nil
  end
  local level = PANDOC_WRITER_OPTIONS.slide_level or 2
  local out, notes = pandoc.Blocks({}), pandoc.Blocks({})
  local function flush()
    out:extend(notes)
    notes = pandoc.Blocks({})
  end
  for _, blk in ipairs(doc.blocks) do
    if (blk.t == "Header" and blk.level <= level) or blk.t == "HorizontalRule" then
      flush()
      out:insert(blk)
    elseif is_notes(blk) then
      notes:insert(blk)
    else
      out:insert(blk)
    end
  end
  flush()
  doc.blocks = out
  return doc
end
