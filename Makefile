# Makefile - Critical Mass.
#
#   make           build/mass.ssd: !BOOT (*OPT 4,2) and MASS, with the listing and the symbols
#   make test      the 6502 against the model, in py65, one at a time: the plotter (every byte), the
#                  physics (every ball, every step), and the whole game in lockstep (every frame: balls,
#                  state and screen): a bot's game, a forced explosion, repeated explosions with the bot,
#                  and a crowded game (seed 3, where merges in one frame share slots). About eleven minutes
#   make model     the Python model: a bot game, with stats, in build/model/
#   make preview   the shapes and colours as PNGs, in build/model/
#   make clean
#
# The emulator is jsbeeb, through jsbeeb-mcp only (D11): nothing here launches b2.

BARON ?= baron
PY ?= .venv/bin/python
BUILD = build
GEN = $(BUILD)/gen

SRC = src/boot.6502 src/critical.6502
DEPS = $(wildcard src/*.6502) $(GEN)/data.6502

all: $(BUILD)/mass.ssd

$(GEN)/data.6502: tools/gendata.py tools/shapes.py tools/colours.py tools/tables.py tools/mode2.py tools/game.py
	$(PY) tools/gendata.py $(GEN)

$(BUILD)/mass.ssd: $(DEPS)
	mkdir -p $(BUILD)/bin
	$(BARON) -v --symbols $(BUILD)/mass.json -o $@ -p $(BUILD)/bin --title CRITMASS --opt 2 $(SRC) > $(BUILD)/mass.lst

test: $(BUILD)/mass.ssd
	$(PY) tools/test_background.py
	$(PY) tools/test_plot.py --cases 280
	$(PY) tools/test_physics.py --scenes 10 --steps 20
	$(PY) tools/lockstep.py --frames 400
	$(PY) tools/lockstep.py --scene critical --frames 200
	$(PY) tools/lockstep.py --scene explosions --frames 250 --seed 9
	$(PY) tools/lockstep.py --frames 1100 --seed 3

model:
	$(PY) tools/model.py --out $(BUILD)/model

preview:
	$(PY) tools/preview.py --out $(BUILD)/model

clean:
	rm -rf $(BUILD)

.PHONY: all test model preview clean
