OUT := $(notdir $(CURDIR))

include ../Make.common

# The README's images (screenshots/*.png, committed): rerun after editing the deck.
.PHONY: screenshots
screenshots: $(OUT).html $(OUT).pdf
	python3 screenshots.py
