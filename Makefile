# Makefile - Critical Mass.
#
#   make           build/mass.ssd: !BOOT (*OPT 4,2) and MASS, with the listing and the symbols
#   make run       boot the game in b2, as a Model B with the Acorn 1770 DFS. It starts a b2 of its own and
#                  closes the one the last make run started; any other b2 (another session's) is left alone
#   make test      the 6502 against the model, in py65, one at a time, after the real loader: every table,
#                  the screen it unpacks, the plotter (every byte), the physics (every ball, every step), and
#                  the whole game in lockstep (every frame: balls, state and screen): a bot's game, a forced
#                  explosion, repeated explosions with the bot, each drop size pushed into both walls, and a
#                  crowded game (seed 3, where merges in one frame share slots). About eleven minutes
#   make model     the Python model: a bot game, with stats, in build/model/
#   make preview   the shapes and colours as PNGs, in build/model/
#   make release MSG="what's new"
#                  the disc to the site's staging folder (SITE/beeb/criticalmass.ssd, which a jsbeeb link
#                  loads), committed there with this repo's commit named, and pushed. After make test
#   make clean
#
# Claude's emulator is jsbeeb, through jsbeeb-mcp only (D11). make run is for Rich: Claude never runs it.

BARON ?= baron
B2 ?= /snap/bin/b2
B2_CONFIG ?= B/Acorn 1770
PY ?= .venv/bin/python
SITE ?= $(HOME)/dev/waitingforvsync.github.io
RELEASE = beeb/criticalmass.ssd
BUILD = build
GEN = $(BUILD)/gen

SRC = src/boot.6502 src/critical.6502
GENERATED = $(GEN)/data.6502 $(GEN)/tables.6502 $(GEN)/made.6502 $(GEN)/tables.json $(GEN)/screen.bin \
	$(GEN)/title.bin
DEPS = $(wildcard src/*.6502) $(GENERATED)

all: $(BUILD)/mass.ssd

$(GENERATED) &: tools/gendata.py tools/shapes.py tools/colours.py tools/tables.py tools/mode2.py tools/game.py \
		tools/layout.py tools/font.py tools/physics.py tools/screenpng.py tools/sparks.py assets/screen.png \
		assets/title.png
	$(PY) tools/gendata.py $(GEN)

$(BUILD)/mass.ssd: $(DEPS)
	mkdir -p $(BUILD)/bin
	$(BARON) -v --symbols $(BUILD)/mass.json -o $@ -p $(BUILD)/bin --title CRITMASS --opt 2 $(SRC) > $(BUILD)/mass.lst
	$(PY) tools/check_inplace.py

# b2 -0 with -b always starts a new process (only a lone file argument hands the disc to a running b2).
# build/b2.pid is the b2 the last run started: it's closed only if its command line still names this disc.
# Closing it waits (up to 5 s) for it to exit, since b2 rewrites its config file in place as it quits.
run: $(BUILD)/mass.ssd
	@pid=$$(cat $(BUILD)/b2.pid 2>/dev/null); \
	if [ -n "$$pid" ] && grep -qsF '$(abspath $<)' /proc/$$pid/cmdline; then \
	    kill $$pid; \
	    for i in $$(seq 50); do kill -0 $$pid 2>/dev/null || break; sleep 0.1; done; \
	fi; \
	nohup $(B2) --config='$(B2_CONFIG)' -0 '$(abspath $<)' -b > $(BUILD)/b2.log 2>&1 & \
	echo $$! > $(BUILD)/b2.pid

# Only the disc is committed there (another project's releases share the repo): pulled first, so the
# push goes on top of theirs.
release: $(BUILD)/mass.ssd
	@test -n "$(MSG)" || { echo 'make release MSG="what changed"'; exit 1; }
	git -C $(SITE) pull --ff-only --quiet
	cp $< $(SITE)/$(RELEASE)
	git -C $(SITE) add $(RELEASE)
	git -C $(SITE) commit --quiet -m "Critical Mass: $(MSG) (criticalmass $$(git describe --always --dirty))" -- $(RELEASE)
	git -C $(SITE) push --quiet

test: $(BUILD)/mass.ssd
	$(PY) tools/test_tables.py
	$(PY) tools/test_background.py
	$(PY) tools/test_plot.py --cases 280
	$(PY) tools/test_physics.py --scenes 10 --steps 20
	$(PY) tools/lockstep.py --frames 400
	$(PY) tools/lockstep.py --scene critical --frames 200
	$(PY) tools/lockstep.py --scene twin --frames 150
	$(PY) tools/lockstep.py --scene explosions --frames 250 --seed 9
	$(PY) tools/lockstep.py --scene walls --frames 500 --seed 7
	$(PY) tools/lockstep.py --frames 1100 --seed 3

model:
	$(PY) tools/model.py --out $(BUILD)/model

preview:
	$(PY) tools/preview.py --out $(BUILD)/model

clean:
	rm -rf $(BUILD)

.PHONY: all run release test model preview clean
