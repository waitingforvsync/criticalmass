"""The screen's static parts, after Rich's prototype (D13), and where the game draws on it (D18).

The starting screen is assets/screen.png, the source (screenpng.py): the checker over everything outside the
well, a thin white wall each side and a white floor, the logo at the top of the panel, and the panel's black
boxes with their labels. compose() drew its first version from the numbers here; it's retouched by hand
since, so the numbers the game draws by (where the next ball, the score and GAME OVER go) must follow it.

Byte columns across and lines down, as mode2.py has them. The checker is blocks of 4 pixels (two byte
columns) by 8 lines (a character row), black and dark blue: blue stippled with black, anchored to the
screen as the balls' colours are (blue where pixel + line is even). The top left block is dark.

	columns 0-1     the checker: a margin of one block
	column 2        the left wall: its right pixel white, against the well
	columns 3-34    the well, 32 bytes: each row's 256 bytes one page (WellAddr, D18)
	column 35       the right wall: its left pixel white
	columns 36-63   the checker, the logo at the top, the panel's boxes below

The 6502 draws by columns from the well's first (the plotter's pixels likewise): WellAddr is a page.
"""

from colours import B as Blue, W as White, Y as Yellow
from font import draw_label
from mode2 import Columns, Lines, ScreenBase, pixel_byte

MarginCols = 2							# the checker left of the well: one block
WallLeftCol = MarginCols
WellCol = WallLeftCol + 1
WellCols = 32
WallRightCol = WellCol + WellCols		# 35
WellAddr = ScreenBase + WellCol * 8		# the well's first byte: on an even page (the plotter ORs in a page)
FloorRow = 27
FloorLine = FloorRow * 8				# the well's bottom: the floor's first line
FloorLines = 2							# the floor: two lines white, then two black, then the checker
RimLine = 32							# a ball poking above this, touching another, is failing
LimitLine = RimLine						# the limit's line across the well (D21): drawn by the game, not in screen.png;
										# under the held ball (its lowest line is 31)

assert WellAddr % 512 == 0, "the well's rows each start a page, an even one"

# The checker's bytes: a dark block's on even lines and odd ones (a black block's are 0)
StippleEven = pixel_byte(Blue, 0)
StippleOdd = pixel_byte(0, Blue)

# The walls' bytes, the rim's (both pixels white: a tick out from each wall) and the floor's
WallLeft = pixel_byte(0, White)
WallRight = pixel_byte(White, 0)
RimMark = pixel_byte(White, White)
FloorByte = pixel_byte(White, White)
LimitByte = pixel_byte(Blue, 0)				# dotted: the left pixel of each byte (the checker's blue on even lines)

# The panel: the logo (48 x 32 pixels) at the top with a block of checker round it, then black boxes on the
# checker's blocks, (top row, rows), all from BoxCol for BoxCols
LogoCol, LogoRow = 38, 1
BoxCol, BoxCols = 40, 20
NextBox = (6, 6)
ScoreBox = (13, 4)
BestBox = (18, 4)
PanelBoxes = (NextBox, ScoreBox, BestBox)

# GAME OVER, at the game's end: in the middle of the well, in a black box as wide as the panel's (over the
# balls; a new game clears the well)
OverBoxCol = WellCol + (WellCols - BoxCols) // 2	# 9
OverBox = (12, 3)						# lines 96 to 119: the well's middle is 108

# The text: the labels (only in screen.png) centred on the boxes' middle pixel, from their top lines; the
# numbers' 6-digit field (byte column, top line) centred too
BoxMiddle = 2 * BoxCol + BoxCols		# the boxes' middle pixel column
LabelCol = BoxCol + (BoxCols - 12) // 2	# the digits' field: 12 bytes
NextLabel = 51
ScoreLabel, ScoreLine = 107, 123
BestLabel, BestLine = 147, 163
OverCol = OverBoxCol + 1				# GAME OVER is 18 bytes: one in from each side
OverLine = 103							# the box's middle 10 lines

# The next ball's centre, units from the well's left: in its box, under NEXT (the biggest drop, 29 lines,
# from line 65 to 93)
NextX, NextY = 2 * (2 * (BoxCol - WellCol) + BoxCols), 79

assert BoxCol % 2 == 0 and BoxCols % 2 == 0, "the boxes are on the checker's blocks"
assert BoxCol >= WallRightCol + 1 and BoxCol + BoxCols <= Columns


def checker_byte(col, line):
	if ((col >> 1) + (line >> 3)) & 1:
		return 0
	return StippleEven if line % 2 == 0 else StippleOdd


def black_box(screen, box, left=BoxCol):
	row, rows = box
	for col in range(left, left + BoxCols):
		for line in range(row * 8, (row + rows) * 8):
			screen.put(col, line, 0)


def compose(screen):
	"""The starting screen's first version, from the numbers here and the logo: what screen.png began as.
	Plain stores, outside the well, so never EORed."""
	from screenpng import LogoLines, LogoPng, LogoWidth, game_codes, read_pixels
	for col in range(Columns):
		for line in range(Lines):
			screen.put(col, line, checker_byte(col, line))
	for col in range(WellCol, WallRightCol):
		for line in range(FloorLine):
			screen.put(col, line, 0)
	for line in range(FloorLine):
		rim = RimLine - 1 <= line <= RimLine
		screen.put(WallLeftCol, line, RimMark if rim else WallLeft)
		screen.put(WallRightCol, line, RimMark if rim else WallRight)
	for line in range(FloorLine, FloorLine + 2 * FloorLines):
		white = line < FloorLine + FloorLines
		screen.put(WallLeftCol, line, WallLeft if white else 0)
		screen.put(WallRightCol, line, WallRight if white else 0)
		for col in range(WellCol, WallRightCol):
			screen.put(col, line, FloorByte if white else 0)
	codes = game_codes()
	for y, row in enumerate(read_pixels(LogoPng, LogoWidth, LogoLines)):
		for col in range(LogoWidth // 2):
			screen.put(LogoCol + col, LogoRow * 8 + y, pixel_byte(codes[row[2 * col]], codes[row[2 * col + 1]]))
	for box in PanelBoxes:
		black_box(screen, box)
	draw_label(screen, "NEXT", BoxMiddle, NextLabel)
	draw_label(screen, "SCORE", BoxMiddle, ScoreLabel)
	draw_label(screen, "BEST", BoxMiddle, BestLabel)


def draw_limit(screen):
	"""The limit's line across the well, as new_screen draws it (limit.6502)."""
	for col in range(WellCol, WallRightCol):
		screen.put(col, LimitLine, LimitByte)


def wipe_row(screen, row):
	"""The game over's wipe of a row of the well (D25): its even lines cleared, as wipe_row does."""
	for col in range(WellCol, WallRightCol):
		for line in range(row * 8, row * 8 + 8, 2):
			screen.put(col, line, 0)


def background(screen):
	"""The starting screen, from assets/screen.png: what the loader unpacks."""
	from screenpng import ScreenPng, game_codes, read_pixels, screen_bytes
	screen.mem[:] = screen_bytes(read_pixels(ScreenPng, Columns * 2, Lines), game_codes(), Columns)
