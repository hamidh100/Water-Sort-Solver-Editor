import pygame
import sys
import os
import math
import subprocess

pygame.init()

# ============================================================
# SETTINGS
# ============================================================

WIDTH, HEIGHT = 1000, 700

PURPLE = (120, 50, 160)
WHITE = (255, 255, 255)
BLACK = (30, 30, 30)

GREEN = (80, 220, 100)
RED = (230, 80, 80)
BLUE = (70, 130, 230)
LIGHT_BLUE = (100, 190, 255)
DARK_BLUE = (40, 70, 140)

YELLOW = (255, 220, 70)
GOLD = (240, 180, 50)

ORANGE = (245, 140, 50)
PINK = (240, 100, 180)
CYAN = (60, 210, 210)

DARK_GREEN = (40, 140, 70)
LIME = (160, 230, 70)

DARK_RED = (170, 50, 50)
DARK_PURPLE = (80, 30, 110)

LIGHT_GRAY = (220, 220, 220)
DARK_GRAY = (80, 80, 80)

# Colors that can appear as water
WATER_COLORS = [
    RED,
    BLUE,
    LIGHT_BLUE,
    DARK_BLUE,
    YELLOW,
    GOLD,
    ORANGE,
    PINK,
    CYAN,
    DARK_GREEN,
    LIME,
    DARK_RED,
    DARK_PURPLE,
]

# ============================================================
# BOTTLE SETTINGS
# ============================================================

BOTTLE_WIDTH = 62
BOTTLE_LAYER_HEIGHT = 48
BOTTLE_GAP = 35

BOTTLE_WALL = 4

# Empty glass rim left above the topmost liquid layer.
# It guarantees every tile (colored or empty, full or
# partly filled bottle) always has exactly the same height.
BOTTLE_LIP = 8


def bottle_height(capacity, layer_h=BOTTLE_LAYER_HEIGHT):
    """
    Total height (pixels) of a bottle image / rect.

    The glass needs a small empty rim above the topmost
    layer, otherwise that top cell gets eaten by the rim
    and looks shorter than all the others.
    """
    return capacity * layer_h + BOTTLE_LIP

# Render bottles at 4x resolution and then shrink them.
# This is what gives the curved glass its smooth appearance.
BOTTLE_SCALE = 4

GLASS_COLOR = (190, 195, 194)
BACKGROUND = (15, 40, 39)

# Default height for new bottles
DEFAULT_BOTTLE_HEIGHT = 4

new_bottle_height = DEFAULT_BOTTLE_HEIGHT

# Bottles per row (adjustable via buttons)
DEFAULT_ROW_COUNT = 7

bottles_per_row = DEFAULT_ROW_COUNT

# Number of bottles created by RESET
DEFAULT_BOTTLE_COUNT = 14

MIN_ROW_COUNT = 1
MAX_ROW_COUNT = 10

# Y where the first row of bottles begins
FIRST_ROW_TOP = 155

# Vertical gap between bottle rows
ROW_GAP = 40

# Minimum / maximum possible capacity
MIN_HEIGHT = 1
MAX_HEIGHT = 12

# ============================================================
# PALETTES
# ============================================================

# User palette is stored as:
#
#   [NUMBER OF COLORS]
#   [R1,G1,B1]
#   [R2,G2,B2]
#   ...
#
USER_PALETTE_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "user_palette.txt"
)

# Bottles are saved here when the app closes
BOTTLE_STATE_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "bottles.txt"
)

# External C++ solver.
#
# The current bottle state is piped to this
# executable's standard input.
SOLVER_EXECUTABLE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "solver"
)

# Line the solver prints instead of moves
# when the board can not be solved
SOLVER_CANT_MARKER = "CANT BE SOLVED"

# Used to seed the file on first run
DEFAULT_USER_PALETTE = [
    RED,
    GREEN,
    BLUE,
    YELLOW,
    ORANGE,
    PINK
]

MAX_USER_COLORS = 30

# Special "unknown" color.
#
# A string on purpose, so it can never be
# equal to a real (R, G, B) tuple.
#
# Layers of this color are drawn as empty
# space with a question mark.
UNKNOWN_COLOR = "?"

# Which palette the picker shows
active_palette = "default"

# Currently picked color (None = nothing picked)
selected_color = None


def save_user_palette(colors):

    lines = [str(len(colors))]

    for color in colors:

        lines.append(
            f"{color[0]},{color[1]},{color[2]}"
        )

    with open(USER_PALETTE_FILE, "w") as file:

        file.write("\n".join(lines) + "\n")


def load_user_palette():

    # --------------------------------------------------------
    # First run: create the file with default colors
    # --------------------------------------------------------

    if not os.path.exists(USER_PALETTE_FILE):

        save_user_palette(DEFAULT_USER_PALETTE)

        return list(DEFAULT_USER_PALETTE)

    # --------------------------------------------------------
    # Read the file
    #
    # If anything is broken, fall back to defaults
    # --------------------------------------------------------

    try:

        with open(USER_PALETTE_FILE) as file:

            lines = [
                line.strip()
                for line in file
                if line.strip()
            ]

        count = int(lines[0])

        colors = []

        for line in lines[1 : 1 + count]:

            r, g, b = [
                int(value)
                for value in line.split(",")
            ]

            colors.append(
                (
                    max(0, min(r, 255)),
                    max(0, min(g, 255)),
                    max(0, min(b, 255))
                )
            )

        return colors

    except (ValueError, IndexError):

        return list(DEFAULT_USER_PALETTE)


user_palette = load_user_palette()

# ============================================================
# SCREEN
# ============================================================

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Water Sort Bottle Editor")

font = pygame.font.Font(None, 32)
small_font = pygame.font.Font(None, 26)

# Question marks inside bottles are drawn
# at 4x resolution and shrinked with the
# bottle itself.
#
# Fonts are cached by pixel size, because
# the solution viewer renders bottles at
# other scales than the editor.
_question_fonts = {}


def get_question_font(size):

    font_obj = _question_fonts.get(size)

    if font_obj is None:

        font_obj = pygame.font.Font(None, size)

        _question_fonts[size] = font_obj

    return font_obj

clock = pygame.time.Clock()

# ============================================================
# BUTTONS
#
# Related controls are grouped into one panel:
# a caption above the panel and [ - ] value [ + ]
# inside it.
# ============================================================

ADD_BUTTON = pygame.Rect(30, 36, 95, 48)
REMOVE_BUTTON = pygame.Rect(135, 36, 115, 48)
RESET_BUTTON = pygame.Rect(260, 36, 100, 48)

HEIGHT_GROUP = pygame.Rect(400, 36, 170, 48)
HEIGHT_DOWN_BUTTON = pygame.Rect(408, 42, 40, 36)
HEIGHT_UP_BUTTON = pygame.Rect(522, 42, 40, 36)

ALL_GROUP = pygame.Rect(600, 36, 150, 48)
ALL_DOWN_BUTTON = pygame.Rect(608, 42, 40, 36)
ALL_UP_BUTTON = pygame.Rect(702, 42, 40, 36)

ROW_GROUP = pygame.Rect(780, 36, 170, 48)
ROW_DOWN_BUTTON = pygame.Rect(788, 42, 40, 36)
ROW_UP_BUTTON = pygame.Rect(902, 42, 40, 36)

COLORS_BUTTON = pygame.Rect(30, 94, 110, 44)
CLEAR_BUTTON = pygame.Rect(152, 94, 110, 44)
CLEAR_ALL_BUTTON = pygame.Rect(274, 94, 115, 44)
SOLVE_BUTTON = pygame.Rect(443, 94, 115, 44)

# Small square showing the active color
ACTIVE_COLOR_INDICATOR = pygame.Rect(
    401,
    101,
    30,
    30
)

# Colors used by the button design
GROUP_BG = (30, 68, 66)
CAPTION_COLOR = (140, 175, 172)

# ============================================================
# COLOR PICKER PANEL
#
# The panel keeps its original look; it can
# be moved by grabbing any empty spot of it
# (tabs, swatches and the user-palette
# controls still work as usual).
# ============================================================

PANEL_WIDTH = 270
PANEL_HEIGHT = 515

panel_pos = [715, 160]

panel_drag_offset = None


def get_panel_rect():
    """
    Current panel position as a rect.
    """

    return pygame.Rect(
        panel_pos[0],
        panel_pos[1],
        PANEL_WIDTH,
        PANEL_HEIGHT
    )


def get_default_tab():

    rect = get_panel_rect()

    return pygame.Rect(
        rect.x + 14,
        rect.y + 12,
        116,
        36
    )


def get_user_tab():

    rect = get_panel_rect()

    return pygame.Rect(
        rect.x + 140,
        rect.y + 12,
        116,
        36
    )

SWATCH_COLS = 5
SWATCH_SIZE = 42
SWATCH_STEP = 50

def get_rgb_field_y():

    return get_panel_rect().bottom - 88


def get_rgb_boxes():

    field_y = get_rgb_field_y()

    x = get_panel_rect().x

    return {
        "r": pygame.Rect(x + 14, field_y, 54, 36),
        "g": pygame.Rect(x + 76, field_y, 54, 36),
        "b": pygame.Rect(x + 138, field_y, 54, 36)
    }


def get_palette_add_button():

    return pygame.Rect(
        get_panel_rect().x + 200,
        get_rgb_field_y(),
        56,
        36
    )


def get_palette_remove_button():

    return pygame.Rect(
        get_panel_rect().x + 14,
        get_rgb_field_y() + 44,
        242,
        36
    )

panel_open = False

# Text typed into the R / G / B input boxes
rgb_values = {"r": "255", "g": "0", "b": "0"}

active_rgb_field = None


# ============================================================
# BOTTLES
# ============================================================

bottles = []

last_id = 0

selected_bottle = None


# ============================================================
# CREATE BOTTLE
# ============================================================

def create_bottle(height):
    """
    Creates a new empty bottle.

    The bottle can hold up to 'height'
    color layers.
    """

    global last_id

    last_id += 1

    bottle = {
        "id": last_id,

        # Maximum amount of liquid the bottle can hold
        "capacity": height,

        # Current water/colors in the bottle
        #
        # Example:
        # [RED, BLUE, BLUE, YELLOW]
        #
        # The last item is the top layer.
        "colors": []
    }

    return bottle


# ============================================================
# ADD BOTTLE
# ============================================================

def add_bottle():
    global selected_bottle

    bottle = create_bottle(new_bottle_height)

    # --------------------------------------------------------
    # Nothing selected:
    # add to the end
    # --------------------------------------------------------

    if selected_bottle is None:

        bottles.append(bottle)

    # --------------------------------------------------------
    # Bottle selected:
    # insert immediately to the right
    # --------------------------------------------------------

    else:

        selected_index = bottles.index(selected_bottle)

        bottles.insert(
            selected_index + 1,
            bottle
        )

        # Select the newly inserted bottle
        selected_bottle = bottle


# ============================================================
# REMOVE BOTTLE
# ============================================================

def remove_bottle():
    global selected_bottle

    if not bottles:
        return

    # --------------------------------------------------------
    # Selected bottle
    # --------------------------------------------------------

    if selected_bottle is not None:

        if selected_bottle in bottles:
            bottles.remove(selected_bottle)

        selected_bottle = None

    # --------------------------------------------------------
    # Nothing selected
    # --------------------------------------------------------

    else:

        bottles.pop()


# ============================================================
# CHANGE HEIGHT FOR NEW BOTTLES
# ============================================================

def increase_new_height():

    global new_bottle_height

    if new_bottle_height < MAX_HEIGHT:
        new_bottle_height += 1


def decrease_new_height():

    global new_bottle_height

    if new_bottle_height > MIN_HEIGHT:
        new_bottle_height -= 1


# ============================================================
# CHANGE ALL BOTTLE HEIGHTS
# ============================================================

def increase_all_heights():

    for bottle in bottles:

        if bottle["capacity"] < MAX_HEIGHT:

            bottle["capacity"] += 1


def decrease_all_heights():

    for bottle in bottles:

        if bottle["capacity"] > MIN_HEIGHT:

            bottle["capacity"] -= 1

            # Remove layers that no longer fit
            while len(bottle["colors"]) > bottle["capacity"]:
                bottle["colors"].pop()


# ============================================================
# CHANGE BOTTLES PER ROW
# ============================================================

def increase_bottles_per_row():

    global bottles_per_row

    if bottles_per_row < MAX_ROW_COUNT:
        bottles_per_row += 1


def decrease_bottles_per_row():

    global bottles_per_row

    if bottles_per_row > MIN_ROW_COUNT:
        bottles_per_row -= 1


# ============================================================
# RESET EVERYTHING
# ============================================================

def reset_editor():
    """
    Back to the starting state:

    - 7 bottles per row
    - new bottle height of 4
    - 14 clean (empty) bottles
    - nothing selected
    """

    global bottles_per_row
    global new_bottle_height
    global selected_bottle
    global selected_color
    global last_id

    bottles_per_row = DEFAULT_ROW_COUNT
    new_bottle_height = DEFAULT_BOTTLE_HEIGHT

    selected_bottle = None
    selected_color = None

    bottles.clear()

    last_id = 0

    for _ in range(DEFAULT_BOTTLE_COUNT):
        bottles.append(
            create_bottle(new_bottle_height)
        )


# ============================================================
# SAVE / LOAD BOTTLES
#
# The file looks like this:
#
#   [#BOTTLES]
#   [HEIGHT1] [#COLORS1] [RGB] [RGB] ... [RGB]
#   [HEIGHT2] [#COLORS2] [RGB] [RGB] ... [RGB]
#   ...
#
# Example:
#
#   3
#   4 0
#   2 2 255,0,0 0,128,255
#   6 4 10,20,30 ? ? 90,200,90
#
# HEIGHT is the bottle's capacity, even when
# it is not filled up completely.
#
# An empty bottle is just "HEIGHT 0".
# The unknown color is written as "?".
# ============================================================

def bottles_to_text(target_bottles=None):
    """
    Serializes bottles into the save format.
    Used for the file and for piping a state
    into the solver.

    Without an argument the current editor
    bottles are used.
    """

    if target_bottles is None:
        target_bottles = bottles

    lines = [str(len(target_bottles))]

    for bottle in target_bottles:

        parts = [
            str(bottle["capacity"]),
            str(len(bottle["colors"]))
        ]

        for color in bottle["colors"]:

            if color == UNKNOWN_COLOR:
                parts.append("?")

            else:
                parts.append(
                    f"{color[0]},{color[1]},{color[2]}"
                )

        lines.append(" ".join(parts))

    return "\n".join(lines) + "\n"


def save_bottles():

    with open(BOTTLE_STATE_FILE, "w") as file:

        file.write(
            bottles_to_text()
        )


def load_bottles():
    """
    Restores the last session from the save
    file.

    Returns True on success. On a missing or
    broken file the app falls back to its
    default state (14 clean bottles,
    per row = 7, height = 4).
    """

    global bottles

    # --------------------------------------------------------
    # No save yet -> default state
    # --------------------------------------------------------

    if not os.path.exists(BOTTLE_STATE_FILE):
        return False

    try:

        with open(BOTTLE_STATE_FILE) as file:

            lines = [
                line.strip()
                for line in file
                if line.strip()
            ]

        count = int(lines[0])

        restored = []

        for line in lines[1 : 1 + count]:

            tokens = line.split()

            # [HEIGHT] [#COLORS] [RGB] ...
            capacity = int(tokens[0])
            color_count = int(tokens[1])

            capacity = max(
                MIN_HEIGHT,
                min(capacity, MAX_HEIGHT)
            )

            colors = []

            for token in tokens[2 : 2 + color_count]:

                # Unknown layer
                if token == "?":
                    colors.append(UNKNOWN_COLOR)
                    continue

                r, g, b = [
                    int(value)
                    for value in token.split(",")
                ]

                colors.append(
                    (
                        max(0, min(r, 255)),
                        max(0, min(g, 255)),
                        max(0, min(b, 255))
                    )
                )

            # Never keep more layers than fit
            colors = colors[:capacity]

            bottle = create_bottle(capacity)

            bottle["colors"] = colors

            restored.append(bottle)

        bottles = restored

        return True

    except (ValueError, IndexError):

        return False


# ------------------------------------------------------------
# On startup: restore the last session,
# otherwise start with the default state.
# ------------------------------------------------------------

if not load_bottles():
    reset_editor()


# ============================================================
# SOLVE
# ============================================================

def bottles_have_any_color():

    return any(
        bottle["colors"]
        for bottle in bottles
    )


def bottles_have_unknown():

    return any(
        UNKNOWN_COLOR in bottle["colors"]
        for bottle in bottles
    )


def draw_busy_screen(text):
    """
    Dims the editor window with a message.
    Shown while the C++ solver is running,
    because that can take a few seconds.
    """

    overlay = pygame.Surface(
        (WIDTH, HEIGHT),
        pygame.SRCALPHA
    )

    overlay.fill((0, 0, 0, 160))

    screen.blit(overlay, (0, 0))

    text_surface = font.render(
        text,
        True,
        WHITE
    )

    screen.blit(
        text_surface,
        (
            WIDTH // 2
            - text_surface.get_width() // 2,

            HEIGHT // 2
            - text_surface.get_height() // 2
        )
    )


def solve_puzzle():
    """
    Pipes the current bottle state into the
    external C++ solver and opens the
    step-by-step solution window.

    Only does something when at least one
    color is placed in the bottles.
    """

    if not bottles_have_any_color():
        return

    if not os.path.exists(SOLVER_EXECUTABLE):

        print(f"Solver not found: {SOLVER_EXECUTABLE}")
        return

    state_text = bottles_to_text()

    # Feedback before the (possibly slow) solve
    draw_busy_screen("SOLVING...")
    pygame.display.flip()

    result = subprocess.run(
        [SOLVER_EXECUTABLE],
        input=state_text,
        capture_output=True,
        text=True
    )

    moves = parse_solver_output(result.stdout)

    if moves is None:

        print("Solver produced no usable output")
        return

    run_solution_window(
        clone_state(bottles),
        moves
    )


# ============================================================
# SOLVER OUTPUT / STATE HELPERS
#
# The solver prints:
#
#   DONE
#   [#MOVES]
#   [FROM] [TO]
#   ...
#
# A move pours the whole top color group of
# bottle FROM into bottle TO. Bottle numbers
# are 1-based.
# ============================================================

def clone_state(state):
    """
    Deep copy of a bottle state
    ([{"capacity", "colors"}, ...]).
    """

    return [
        {
            "capacity": bottle["capacity"],
            "colors": list(bottle["colors"])
        }
        for bottle in state
    ]


def parse_solver_output(text):
    """
    Reads the solver's stdout and returns a
    list of (from, to) moves, or None when
    the output is unusable.

    An unsolvable board prints "CANT BE
    SOLVED" and yields an empty move list -
    the viewer then shows the position as-is.
    """

    if SOLVER_CANT_MARKER in text:
        return []

    try:

        lines = [
            line.strip()
            for line in text.splitlines()
        ]

        lines = [
            line
            for line in lines
            if line
        ]

        done_index = lines.index("DONE")

        move_count = int(lines[done_index + 1])

        numbers = []

        for line in lines[done_index + 2:]:

            numbers.extend(
                int(token)
                for token in line.split()
            )

        if len(numbers) < 2 * move_count:
            return None

        return [
            (
                numbers[i],
                numbers[i + 1]
            )
            for i in range(0, 2 * move_count, 2)
        ]

    except (ValueError, IndexError):

        return None


def apply_group_move(state, source, target):
    """
    Applies one solver move to a state:
    pours the whole top color group from
    'source' to 'target' (1-based).
    """

    count = len(state)

    if not (
        1 <= source <= count
        and 1 <= target <= count
    ):
        return

    if source == target:
        return

    source_colors = state[source - 1]["colors"]
    target_colors = state[target - 1]["colors"]

    if not source_colors:
        return

    top_color = source_colors[-1]

    group_size = 0

    for color in reversed(source_colors):

        if color != top_color:
            break

        group_size += 1

    room = (
        state[target - 1]["capacity"]
        - len(target_colors)
    )

    moved = 0

    while (
        moved < group_size
        and moved < room
        and source_colors
    ):
        target_colors.append(
            source_colors.pop()
        )

        moved += 1


def replay_moves(start_state, moves):
    """
    Returns every board position from the
    start up to the solved one:

        [start, after_move_1, ...]
    """

    current = clone_state(start_state)

    states = [clone_state(current)]

    for source, target in moves:

        apply_group_move(current, source, target)

        states.append(clone_state(current))

    return states


def _unknown_token(bottle_index, layer_index):
    """
    Identity of an unknown layer: the exact
    (bottle, layer) it occupied in the start
    board. Using a tuple that can never collide
    with a real (r, g, b) color.
    """
    return (UNKNOWN_COLOR, bottle_index, layer_index)


def _is_unknown_token(entry):
    """
    True when an entry of a tokenized bottle is
    an unknown-layer identity token rather than a
    plain color.
    """
    return (
        isinstance(entry, tuple)
        and len(entry) == 3
        and entry[0] == UNKNOWN_COLOR
    )


def tokenize_state(state):
    """
    Returns a copy of 'state' where every "?" layer
    is replaced by its start-board identity token.
    Used to track where unknowns end up so painted
    colors can be written back onto the right "?"
    of the original start board.
    """
    tokenized = []

    for bottle_index, bottle in enumerate(state):

        colors = []

        for layer_index, color in enumerate(bottle["colors"]):

            if color == UNKNOWN_COLOR:

                colors.append(
                    _unknown_token(bottle_index, layer_index)
                )

            else:

                colors.append(color)

        tokenized.append(
            {
                "capacity": bottle["capacity"],
                "colors": colors
            }
        )

    return tokenized


def apply_traced_moves(tokens, moves):
    """
    Advances a tokenized state through 'moves',
    keeping each unknown layer's identity token
    attached to it as it is poured around.

    Mirrors apply_group_move, except any two unknown
    layers group together regardless of their origin
    tokens (exactly how the solver treats "?").
    """

    for source, target in moves:

        source_bottle = tokens[source - 1]
        target_bottle = tokens[target - 1]

        src = source_bottle["colors"]
        tgt = target_bottle["colors"]

        if not src:
            continue

        top = src[-1]

        def same_group(a, b):
            if _is_unknown_token(a) and _is_unknown_token(b):
                return True
            return a == b

        group_size = 0

        for entry in reversed(src):

            if not same_group(entry, top):
                break

            group_size += 1

        room = target_bottle["capacity"] - len(tgt)

        moved = 0

        while (
            moved < group_size
            and moved < room
            and src
        ):
            tgt.append(src.pop())

            moved += 1


def state_has_unknown(state):

    return any(
        UNKNOWN_COLOR in bottle["colors"]
        for bottle in state
    )


def state_has_unknown_at_top(state):
    """
    True when at least one bottle's topmost
    layer is still unknown - the point where
    the user can see and assign its color.
    """

    return any(
        bottle["colors"]
        and bottle["colors"][-1] == UNKNOWN_COLOR
        for bottle in state
    )


def state_is_solved(state):
    """
    Same win condition as the C++ solver:
    every color may appear in one bottle
    only (bottles do not need to be full).
    """

    owner = {}

    for bottle_index, bottle in enumerate(state):

        for color in bottle["colors"]:

            if color == UNKNOWN_COLOR:
                return False

            if owner.setdefault(
                color,
                bottle_index
            ) != bottle_index:
                return False

    return True


# ============================================================
# SOLUTION VIEWER WINDOW
#
# Shows the solver's moves step by step in
# its own window:
#
#   RIGHT / DOWN / ENTER   next step
#   LEFT / UP              previous step
#   ESC                    close
#
# The header counts MOVES: an already solved
# puzzle shows 0/0, a one-move puzzle starts
# at 0/1 and ends at 1/1.
#
# On the final step, while question marks
# remain:
#
#   - click any tile to select it (click
#     again to deselect)
#   - the PALETTE button opens a picker that
#     floats over the board - the exact same
#     panel as in the editor; click a color
#     to paint all selected tiles, the "?"
#     swatch clears them back to unknown
#   - SOLVE repeats the solving process on
#     the changed board
#   - UPDATE colors the painted "?" tiles onto the
#     ORIGINAL start board (step 0 stays intact,
#     just with fewer unknowns), writes it back to
#     the editor (and the save file) and closes
#
# Status text ("SOLVED!" / "NO SOLUTION")
# sits on the right side of the header line,
# away from the move counter.
# ============================================================

# Space for the header line
VIEWER_HEADER = 64

# Same horizontal margin as the editor board;
# Y where the first row starts
VIEWER_MARGIN = 40
VIEWER_TOP = VIEWER_HEADER + 16

# Reserved height at the bottom of the window
# (buttons + hints)
VIEWER_FOOTER_H = 110


def viewer_board_size(state, per_row, bw, gap, layer_h):
    """
    Width / height needed to show a state's
    bottles in rows of 'per_row' bottles
    (same row alignment as the editor).
    """

    total = len(state)

    rows = max(1, math.ceil(total / per_row)) if total else 1

    width = (
        VIEWER_MARGIN * 2
        + per_row * bw
        + (per_row - 1) * gap
    )

    # Returning sizes relative to the top of the board
    # (not absolute screen Y). The caller compares these
    # against the budget between VIEWER_TOP and the footer.
    bottom_y = 0

    for row in range(rows):

        first = row * per_row

        count = min(per_row, total - first)

        tallest = max(
            bottle["capacity"]
            for bottle in state[first : first + count]
        )

        bottom_y += (
            bottle_height(tallest, layer_h)
            + ROW_GAP
        )

    return width, bottom_y + 6


def viewer_unknown_mark_center(rect, layer_index, layer_h):
    """
    Screen position of a "?" in a bottle layer,
    matching render_bottle_image placement.
    """

    wall = int(
        BOTTLE_WALL
        * layer_h
        / BOTTLE_LAYER_HEIGHT
    )

    mark_y = (
        rect.top
        + rect.height
        - wall
        - (layer_index + 0.5) * layer_h
    )

    return rect.centerx, mark_y


def viewer_bottle_positions(state, per_row, bw, gap, layer_h):
    """
    Rect of every bottle, laid out like the
    editor: each row stands on a shared
    baseline under its tallest bottle.
    """

    rects = []

    total = len(state)

    rows = max(1, math.ceil(total / per_row)) if total else 1

    top_y = VIEWER_TOP

    for row in range(rows):

        first = row * per_row

        count = min(per_row, total - first)

        tallest = max(
            bottle["capacity"]
            for bottle in state[first : first + count]
        )

        baseline = (
            top_y
            + bottle_height(tallest, layer_h)
        )

        for k in range(count):

            bottle = state[first + k]

            height_pixels = (
                bottle_height(bottle["capacity"], layer_h)
            )

            rects.append(
                pygame.Rect(
                    VIEWER_MARGIN
                    + k * (bw + gap),

                    baseline - height_pixels,

                    bw,
                    height_pixels
                )
            )

        top_y += (
            bottle_height(tallest, layer_h)
            + ROW_GAP
        )

    return rects


def plan_solution_layout(state):
    """
    Computes the whole layout of the solution
    window up front.

    The viewer always uses the same window
    size as the editor (WIDTH x HEIGHT) and
    lays the board out across the full window
    width. The palette panel (only shown while
    "?" tiles remain on the final step) floats
    over the board exactly like the editor
    picker, so it never steals width from the
    bottles.

    Bottles use the same per-row setting and
    geometry as the editor; only when that
    does not fit, another row count is tried
    and finally everything gets scaled down.
    """

    has_unknown = state_has_unknown(state)

    avail_width = (
        WIDTH
        - 2 * VIEWER_MARGIN
    )

    avail_height = (
        HEIGHT
        - VIEWER_TOP
        - VIEWER_FOOTER_H
    )

    total = len(state)

    def fits(per_row):
        return viewer_board_size(
            state,
            per_row,
            BOTTLE_WIDTH,
            BOTTLE_GAP,
            BOTTLE_LAYER_HEIGHT
        )

    def scaled():

        scale = min(
            avail_width / max(width, 1),
            avail_height / max(height, 1),
            1.0
        )

        scale = max(scale, 0.35)

        def board_size(lh, b, g):
            return viewer_board_size(
                state, per_row, b, g, lh
            )

        # Shrink the whole bottle uniformly (width, gap
        # and layer height), so solution bottles keep the
        # exact proportions of the main editor bottles
        # instead of getting stretched out of shape.
        lh = max(12, round(BOTTLE_LAYER_HEIGHT * scale))
        b = max(22, round(BOTTLE_WIDTH * scale))
        g = max(8, round(BOTTLE_GAP * scale))

        # The estimate above ignores the fixed row gaps,
        # so tighten the layer height until the board
        # actually fits.
        while lh > 12:
            w_, h_ = board_size(lh, b, g)
            if w_ <= avail_width and h_ <= avail_height:
                return b, g, lh
            lh -= 1

        # Last resort: slim the bottle width as well.
        while b > 22:
            w_, h_ = board_size(lh, b, g)
            if w_ <= avail_width and h_ <= avail_height:
                return b, g, lh
            b -= 1

        return b, g, lh

    # Native editor sizes; only changed when
    # the board does not fit the window
    per_row = max(1, min(bottles_per_row, total))

    bw = BOTTLE_WIDTH
    gap = BOTTLE_GAP
    layer_h = BOTTLE_LAYER_HEIGHT

    width, height = fits(per_row)

    if width > avail_width or height > avail_height:

        # Try other row counts before scaling
        found = None

        for candidate in range(max(1, total), 0, -1):

            c_width, c_height = fits(candidate)

            if (
                c_width <= avail_width
                and c_height <= avail_height
            ):
                found = candidate
                break

        if found is not None:

            per_row = found

            width, height = fits(per_row)

        if width > avail_width or height > avail_height:

            bw, gap, layer_h = scaled()

    body_width, body_height = viewer_board_size(
        state,
        per_row,
        bw,
        gap,
        layer_h
    )

    return {
        "has_unknown": has_unknown,
        "per_row": per_row,
        "bw": bw,
        "gap": gap,
        "layer_h": layer_h,
        "body_width": body_width,
        "body_height": body_height,

        # Where the palette panel floats once it
        # opens - the same x as in the editor but
        # a bit higher, so it sits above the bottles
        "panel_home": [
            panel_pos[0],
            panel_pos[1] - 50
        ]
    }


def run_solution_window(initial_state, moves):
    """
    Opens the step-by-step solution window.

    Blocks until the window is closed, then
    restores the editor window.

    The editor's bottles are never modified
    while stepping around and painting. Only
    UPDATE writes the user's painted colors onto
    the ORIGINAL start board (keeping its
    layout) before closing.
    """

    global screen
    global active_rgb_field

    clear_picker_selection()

    states = replay_moves(initial_state, moves)

    step = 0

    # Selected "?" tiles as (bottle, layer) pairs
    selected_tiles = set()

    # Whether anything got painted already
    painted = False

    # --------------------------------------------------------
    # Painting tracking for UPDATE
    #
    # UPDATE keeps the start board (step 0) and only colors
    # the "?" tiles the user painted. Because the solution
    # moves can pour unknown layers around, each "?" keeps
    # an identity token pointing to the (bottle, layer) it
    # started at. painted_unknowns maps those identities to
    # the color the user chose, so UPDATE can write them back
    # onto the exact start-board tiles.
    # --------------------------------------------------------

    # The very first board; UPDATE restores this layout
    original_start = clone_state(initial_state)

    # Tokenized twin of the current final board
    tokens = tokenize_state(states[-1])

    # Identity token -> color picked by the user
    painted_unknowns = {}

    # Hitboxes of the "?" tiles, rebuilt every
    # frame for click handling
    tile_boxes = []

    # --------------------------------------------------------
    # Verdict of the last solver run:
    #
    #   "none"       nothing decided yet
    #   "solved"     the solve ended in a win
    #   "none_found" the search ran dry
    #
    # The verdict is only refreshed by an
    # explicit SOLVE - painting a tile does not
    # silently flip it (the old live status
    # jumped between SOLVED / NO SOLUTION while
    # filling colors, which was confusing).
    # --------------------------------------------------------

    solve_verdict = "none"

    def coloring_active():
        """
        The user can assign colors while unknown
        layers remain and the last solve did not
        end in a hard "no solution" verdict.
        """

        return (
            solve_verdict == "none"
            and state_has_unknown(states[-1])
        )

    def refresh_verdict(*, from_fresh_solve=False):
        """
        Recompute the header verdict from the
        current final board.

        from_fresh_solve is True right after
        SOLVE runs again; stale painted_unknowns
        from an earlier coloring pass must not
        keep the coloring UI alive when the new
        attempt failed.
        """

        nonlocal solve_verdict

        if state_is_solved(states[-1]):
            solve_verdict = "solved"
        elif state_has_unknown_at_top(states[-1]):
            solve_verdict = "none"
        elif (
            not from_fresh_solve
            and state_has_unknown(states[-1])
            and (painted or painted_unknowns)
        ):
            # A top "?" was already colored, but more
            # unknown layers remain underneath.
            solve_verdict = "none"
        else:
            solve_verdict = "none_found"

    # Fixed window: same size as the editor.
    plan = plan_solution_layout(initial_state)

    per_row = plan["per_row"]
    body_width = plan["body_width"]
    body_height = plan["body_height"]
    bw = plan["bw"]
    gap = plan["gap"]
    layer_h = plan["layer_h"]

    # --------------------------------------------------------
    # Palette panel
    #
    # When the puzzle contains "?" layers, the
    # exact same picker panel as the editor opens
    # as a floating panel over the board (it never
    # reserves its own column, so the bottles keep
    # the editor's full size).
    # --------------------------------------------------------

    palette_open = False

    # Whether the palette was already opened
    # automatically for this arrival at the
    # last slide
    auto_opened = False

    set_viewer_window_done = False

    # --------------------------------------------------------
    # Key hold / auto-repeat for stepping:
    #
    # Holding RIGHT/LEFT (etc.) advances the
    # steps one after another. The held key
    # fires immediately once, then after a
    # short delay repeats at a fixed rate -
    # the classic OS keyboard-repeat feel.
    # --------------------------------------------------------

    STEP_REPEAT_DELAY_MS = 350   # hold this long before repeating starts

    STEP_REPEAT_INTERVAL_MS = 90 # time between repeated steps

    held_step_keys = []          # held step keys, most recent last

    next_step_repeat_ms = 0      # when the next repeat fires

    def handle_step_key(key):
        """
        Applies one stepping action for a
        just-pressed or repeated key. Returns
        True when the key was a step key.
        """

        nonlocal step

        if key in (
            pygame.K_RIGHT,
            pygame.K_DOWN,
            pygame.K_RETURN,
            pygame.K_KP_ENTER,
            pygame.K_SPACE
        ):
            step = min(step + 1, last_step)
            return True

        if key in (
            pygame.K_LEFT,
            pygame.K_UP,
            pygame.K_BACKSPACE
        ):
            step = max(step - 1, 0)
            return True

        return False

    def set_viewer_window():
        """
        Creates the viewer window once - fixed
        editor-sized, no resizing later.
        """

        nonlocal set_viewer_window_done
        global screen

        if set_viewer_window_done:
            return

        screen = pygame.display.set_mode((WIDTH, HEIGHT))

        set_viewer_window_done = True

    palette_drag_offset = None

    # Whether the panel was already placed at its
    # editor spot during this viewer session;
    # keeps a user-dragged position stable
    # across slide changes
    palette_placed = False

    def place_palette():

        nonlocal palette_placed

        if palette_placed:
            return

        # Show the picker where it lives in the
        # editor (once per session), so the viewer
        # looks exactly like it
        panel_pos[:] = list(plan["panel_home"])

        palette_placed = True

    def open_palette():

        nonlocal palette_open

        if palette_open:
            return

        palette_open = True

        global active_rgb_field

        active_rgb_field = None

        place_palette()

    def close_palette():

        nonlocal palette_open

        if not palette_open:
            return

        palette_open = False

        global active_rgb_field

        active_rgb_field = None

    def update_palette_visibility():
        """
        The palette belongs to the last slide:

        - arriving at a colorable final position
          -> the palette opens automatically
        - stepping away from the last slide, or
          coloring is no longer active -> it closes;
          coming back to the last slide opens it
          again
        """

        nonlocal auto_opened

        on_last_step = (
            step == len(states) - 1
        )

        # Leaving the last slide closes the
        # palette and allows it to reopen on
        # the next arrival
        if not on_last_step:

            if palette_open:
                close_palette()

            auto_opened = False

            return

        if not coloring_active():

            if palette_open:
                close_palette()

            return

        if not palette_open and not auto_opened:
            open_palette()
            auto_opened = True

    # --------------------------------------------------------
    # Buttons live in the body region, so they
    # never move when the palette opens.
    # Bottom row, right aligned to the window:
    #
    #   [UPDATE] [SOLVE]
    # --------------------------------------------------------

    solve_button = pygame.Rect(
        WIDTH - 170,
        HEIGHT - 58,
        135,
        44
    )

    update_button = pygame.Rect(
        WIDTH - 315,
        HEIGHT - 58,
        130,
        44
    )

    # --------------------------------------------------------
    # Re-run the solver on the (painted) final
    # state and restart the step view
    # --------------------------------------------------------

    def re_solve():

        nonlocal states
        nonlocal step
        nonlocal painted
        nonlocal selected_tiles
        nonlocal auto_opened
        nonlocal palette_placed

        result = subprocess.run(
            [SOLVER_EXECUTABLE],
            input=bottles_to_text(states[-1]),
            capture_output=True,
            text=True
        )

        new_moves = parse_solver_output(result.stdout)

        if new_moves is None:

            print("Solver produced no usable output")
            return

        states = replay_moves(states[-1], new_moves)

        # Advance the token twin through the new
        # moves, keeping the "?" identities attached
        # to the still-unknown layers.
        apply_traced_moves(tokens, new_moves)

        moves.clear()
        moves.extend(new_moves)

        step = 0
        painted = False
        selected_tiles = set()

        # The verdict now describes this solve
        refresh_verdict(from_fresh_solve=True)

        # A fresh solution may or may not still
        # contain question marks
        auto_opened = False
        palette_placed = False

        update_palette_visibility()

    # --------------------------------------------------------
    # UPDATE keeps the ORIGINAL start board (step 0) and
    # only colors the "?" tiles the user painted onto it,
    # then writes it to the editor (and the save file)
    # and closes the viewer - so the layout stays and
    # fewer unknowns remain for the next solve.
    # --------------------------------------------------------

    def update_editor():

        global bottles
        global selected_bottle

        # ------------------------------------------------
        # Rebuild through create_bottle so every
        # bottle keeps a unique id. Plain copies
        # of equal bottles would compare equal,
        # which breaks the editor's selection.
        # ------------------------------------------------

        rebuilt = []

        for bottle in original_start:

            new_bottle = create_bottle(bottle["capacity"])

            new_bottle["colors"] = list(bottle["colors"])

            rebuilt.append(new_bottle)

        # ------------------------------------------------
        # Color exactly the "?" tiles the user painted:
        # every identity token maps back to a "?" of the
        # original start board, so the layout stays and
        # only those unknowns become colored (fewer "?"
        # left for the next solve).
        # ------------------------------------------------

        for identity, color in painted_unknowns.items():

            _, bottle_index, layer_index = identity

            target_colors = rebuilt[bottle_index]["colors"]

            if 0 <= layer_index < len(target_colors):

                target_colors[layer_index] = color

        bottles[:] = rebuilt

        selected_bottle = None

        save_bottles()

        raise StopIteration

    def handle_viewer_panel_click(pos):
        """
        Click handling for the picker panel
        floating over the solution board.

        Mirrors the editor's panel handler, but
        a swatch click paints all currently
        selected tiles instead of editing the
        editor board. The unknown swatch clears
        tiles back to "?".
        """

        global active_palette
        global active_rgb_field

        nonlocal painted
        nonlocal selected_tiles
        nonlocal solve_verdict

        # ------------------------------------------------
        # Palette tabs
        # ------------------------------------------------

        if get_default_tab().collidepoint(pos):

            active_palette = "default"
            active_rgb_field = None
            return

        if get_user_tab().collidepoint(pos):

            active_palette = "user"
            active_rgb_field = None
            return

        # ------------------------------------------------
        # User palette tools
        # ------------------------------------------------

        if active_palette == "user":

            for key, box in get_rgb_boxes().items():

                if box.collidepoint(pos):

                    active_rgb_field = key
                    return

            if get_palette_add_button().collidepoint(pos):

                add_color_to_user_palette()
                return

            if get_palette_remove_button().collidepoint(pos):

                remove_color_from_user_palette()
                return

        active_rgb_field = None

        # ------------------------------------------------
        # Swatches: paint / clear selected tiles
        #
        # Painting changes the board, so the
        # verdict of the previous solve no longer
        # applies; it gets cleared until the user
        # runs SOLVE again.
        # ------------------------------------------------

        colors = get_active_palette_colors()

        for index, color in enumerate(colors):

            if get_swatch_rect(index).collidepoint(pos):

                if not selected_tiles:
                    return True

                for bottle_index, layer_index in (
                    selected_tiles
                ):

                    colors_list = (
                        states[-1][bottle_index]["colors"]
                    )

                    if layer_index < len(colors_list):

                        colors_list[layer_index] = color

                        # ------------------------------------
                        # Keep the token twin in sync and
                        # remember which start-board "?" the
                        # user just colored, so UPDATE can
                        # write it back onto step 0.
                        # ------------------------------------

                        token_slot = (
                            tokens[bottle_index]["colors"]
                        )

                        if layer_index < len(token_slot):

                            entry = token_slot[layer_index]

                            if _is_unknown_token(entry):

                                if color == UNKNOWN_COLOR:

                                    # The "?" swatch: still
                                    # unknown, nothing to save
                                    painted_unknowns.pop(
                                        entry,
                                        None
                                    )

                                else:

                                    painted_unknowns[entry] = color

                                    token_slot[layer_index] = color

                            else:

                                token_slot[layer_index] = color

                painted = True
                selected_tiles = set()
                solve_verdict = "none"

                return True

        # Nothing interactive was hit -> the
        # empty spot can grab the panel for
        # dragging (same as in the editor)
        return False

    def draw_status_text():
        """
        Right-aligned status in the header line,
        showing the verdict of the last solver
        run - never a live guess while painting.
        """

        if solve_verdict == "solved":

            text, color = "SOLVED!", GREEN

        elif solve_verdict == "none_found":

            text, color = "NO SOLUTION", RED

        else:
            return

        status_surface = font.render(
            text,
            True,
            color
        )

        screen.blit(
            status_surface,
            (
                body_width
                - VIEWER_MARGIN
                - status_surface.get_width(),

                20
            )
        )

    # --------------------------------------------------------
    # Swap to the viewer window and apply the
    # initial palette visibility
    # --------------------------------------------------------

    # The editor picker is borrowed for the
    # viewer; remember where it lived so it can
    # be put back when the viewer closes
    previous_panel_pos = list(panel_pos)

    set_viewer_window()

    # Verdict of the initial editor-triggered
    # solve
    refresh_verdict()

    update_palette_visibility()

    pygame.display.set_caption("Solution")

    try:

        while True:

            # ==================================================
            # EVENTS
            # ==================================================

            for event in pygame.event.get():

                if event.type == pygame.QUIT:
                    raise StopIteration

                if event.type == pygame.KEYDOWN:

                    last_step = len(states) - 1

                    # --------------------------------------------
                    # ESC always works: it first leaves an
                    # RGB input field, then closes the
                    # palette, then closes the viewer
                    # --------------------------------------------

                    if event.key == pygame.K_ESCAPE:

                        if active_rgb_field is not None:
                            active_rgb_field = None

                        elif palette_open:
                            close_palette()

                        else:
                            raise StopIteration

                    # --------------------------------------------
                    # While an RGB field of the palette
                    # is active, other keys edit its content
                    # --------------------------------------------

                    elif active_rgb_field is not None:

                        if event.key == pygame.K_BACKSPACE:

                            rgb_values[active_rgb_field] = (
                                rgb_values[active_rgb_field][:-1]
                            )

                        elif (
                            event.unicode.isdigit()
                            and len(
                                rgb_values[active_rgb_field]
                            ) < 3
                        ):

                            rgb_values[active_rgb_field] += (
                                event.unicode
                            )

                    else:

                        # ----------------------------------------
                        # Stepping with key-hold support:
                        # a step key fires immediately, then
                        # repeats while held (handled in the
                        # loop below)
                        # ----------------------------------------

                        if handle_step_key(event.key):

                            if event.key in held_step_keys:
                                held_step_keys.remove(event.key)
                            else:
                                next_step_repeat_ms = (
                                    pygame.time.get_ticks()
                                    + STEP_REPEAT_DELAY_MS
                                )

                            held_step_keys.append(event.key)

                        elif event.key == pygame.K_HOME:
                            step = 0

                        elif event.key == pygame.K_END:
                            step = last_step

                elif event.type == pygame.KEYUP:

                    if event.key in held_step_keys:
                        held_step_keys.remove(event.key)

                elif (
                    event.type == pygame.MOUSEBUTTONDOWN
                    and event.button == 1
                ):

                    mouse_pos = event.pos

                    on_last_step = step == len(states) - 1

                    can_color_unknowns = coloring_active()

                    # ============================================
                    # SOLVE AGAIN (after changing tiles)
                    # ============================================

                    if on_last_step and solve_button.collidepoint(
                        mouse_pos
                    ):

                        if painted:
                            re_solve()

                    # ============================================
                    # UPDATE back to the editor
                    # ============================================

                    elif on_last_step and update_button.collidepoint(
                        mouse_pos
                    ):

                        if painted_unknowns:
                            update_editor()

                    # ============================================
                    # The picker panel floating over the board:
                    # the same controls as the editor; a swatch
                    # paints all selected "?" tiles ("?" clears).
                    # Empty spots grab it for dragging.
                    # ============================================

                    elif (
                        on_last_step
                        and can_color_unknowns
                        and palette_open
                        and get_panel_rect().collidepoint(mouse_pos)
                    ):

                        def viewer_panel_spot_is_empty():

                            busy = [
                                get_default_tab(),
                                get_user_tab()
                            ]

                            colors = get_active_palette_colors()

                            for index in range(len(colors)):

                                busy.append(
                                    get_swatch_rect(index)
                                )

                            if active_palette == "user":

                                busy.extend(
                                    get_rgb_boxes().values()
                                )

                                busy.append(
                                    get_palette_add_button()
                                )

                                busy.append(
                                    get_palette_remove_button()
                                )

                            return not any(
                                rect.collidepoint(mouse_pos)
                                for rect in busy
                            )

                        if viewer_panel_spot_is_empty():

                            palette_drag_offset = (
                                mouse_pos[0] - panel_pos[0],
                                mouse_pos[1] - panel_pos[1]
                            )

                        else:

                            handle_viewer_panel_click(mouse_pos)

                    # ============================================
                    # Toggle a clicked "?" tile (only
                    # while question marks are around;
                    # colored tiles are not clickable)
                    # ====================================

                    elif on_last_step and can_color_unknowns:

                        for tile_rect, tile in reversed(
                            tile_boxes
                        ):

                            if tile_rect.collidepoint(
                                mouse_pos
                            ):

                                if tile in selected_tiles:
                                    selected_tiles.discard(tile)

                                else:
                                    selected_tiles.add(tile)

                                break

                elif event.type == pygame.MOUSEMOTION:

                    # Drag the palette panel along,
                    # kept inside the window
                    if palette_drag_offset is not None:

                        panel_pos[0] = max(
                            0,
                            min(
                                event.pos[0]
                                - palette_drag_offset[0],

                                WIDTH - PANEL_WIDTH
                            )
                        )

                        panel_pos[1] = max(
                            0,
                            min(
                                event.pos[1]
                                - palette_drag_offset[1],

                                HEIGHT - PANEL_HEIGHT
                            )
                        )

                elif event.type == pygame.MOUSEBUTTONUP:

                    if event.button == 1:

                        palette_drag_offset = None

            # ==================================================
            # KEY HOLD REPEAT
            #
            # While a step key is held, advance one
            # step per interval once the initial
            # delay has passed. Only the most
            # recently pressed held key repeats.
            # ==================================================

            if held_step_keys:

                now = pygame.time.get_ticks()

                if now >= next_step_repeat_ms:

                    last_step = len(states) - 1

                    handle_step_key(held_step_keys[-1])

                    next_step_repeat_ms = (
                        now + STEP_REPEAT_INTERVAL_MS
                    )

            # ==================================================
            # DRAW
            # ==================================================

            # Keep the palette tied to the question
            # marks of the final position: it opens
            # once when a "?"-position is reached and
            # closes as soon as no "?" is left
            update_palette_visibility()

            screen.fill(BACKGROUND)

            last_step = len(states) - 1
            current = states[step]

            # ------------------------------------------------
            # Header: move counter and current move
            #
            # Counts moves, not screens: 0/1 is the
            # start of a one-move solution, N/N its
            # end, 0/0 an already solved puzzle.
            # ------------------------------------------------

            header_text = f"{step}/{len(moves)}"

            if step > 0:

                source, target = moves[step - 1]

                header_text += (
                    f"   (move {step}:  {source} -> {target})"
                )

            header_surface = font.render(
                header_text,
                True,
                WHITE
            )

            screen.blit(
                header_surface,
                (VIEWER_MARGIN, 18)
            )

            # ------------------------------------------------
            # Bottles
            # ------------------------------------------------

            bottle_rects = viewer_bottle_positions(
                current,
                per_row,
                bw,
                gap,
                layer_h
            )

            tile_boxes = []

            for bottle_index, rect in enumerate(bottle_rects):

                image = get_bottle_image(
                    current[bottle_index]["capacity"],
                    tuple(current[bottle_index]["colors"]),
                    bw,
                    layer_h
                )

                screen.blit(image, rect.topleft)

                number_surface = small_font.render(
                    str(bottle_index + 1),
                    True,
                    WHITE
                )

                screen.blit(
                    number_surface,
                    (
                        rect.centerx
                        - number_surface.get_width() // 2,

                        rect.bottom + 6
                    )
                )

                # --------------------------------------------
                # Highlight the two bottles of the move
                # that produced this step
                # --------------------------------------------

                if step > 0:

                    source, target = moves[step - 1]

                    if bottle_index == source - 1:

                        pygame.draw.rect(
                            screen,
                            GOLD,
                            rect.inflate(10, 10),
                            width=4,
                            border_radius=12
                        )

                    if bottle_index == target - 1:

                        pygame.draw.rect(
                            screen,
                            LIME,
                            rect.inflate(10, 10),
                            width=4,
                            border_radius=12
                        )

                # --------------------------------------------
                # Clickable "?" tiles (final step only)
                #
                # Only unknown layers get a hitbox, so
                # colored tiles can not be selected or
                # changed by accident. Selection marker:
                # a crisp white frame exactly around
                # the tile.
                # --------------------------------------------

                if step == last_step and coloring_active():

                    colors_list = current[bottle_index]["colors"]

                    for layer_index, layer_color in enumerate(
                        colors_list
                    ):

                        if layer_color != UNKNOWN_COLOR:
                            continue

                        layer_rect = pygame.Rect(
                            rect.x,
                            rect.bottom
                            - (layer_index + 1) * layer_h,

                            rect.w,
                            layer_h
                        )

                        tile_boxes.append(
                            (layer_rect, (bottle_index, layer_index))
                        )

                        if (bottle_index, layer_index) in (
                            selected_tiles
                        ):

                            selection_size = 34

                            selection_rect = pygame.Rect(
                                0,
                                0,
                                selection_size,
                                selection_size
                            )

                            selection_rect.center = (
                                viewer_unknown_mark_center(
                                    rect,
                                    layer_index,
                                    layer_h
                                )
                            )

                            pygame.draw.rect(
                                screen,
                                WHITE,
                                selection_rect,
                                width=2,
                                border_radius=8
                            )

            # ------------------------------------------------
            # Final step extras
            #
            # Status text (right side of the header),
            # the picker panel floating over the board
            # while question marks are around, and the
            # button row.
            # ------------------------------------------------

            can_color_unknowns = coloring_active()

            draw_status_text()

            if palette_open:

                # The exact editor picker, rendered
                # from the shared state at its
                # floating position
                draw_color_picker()

            if step == last_step:

                if can_color_unknowns:

                    instruction_surface = small_font.render(
                        "Select ? tiles, then pick a color"
                        " ('?' clears)",
                        True,
                        CAPTION_COLOR
                    )

                    screen.blit(
                        instruction_surface,
                        (
                            VIEWER_MARGIN,
                            HEIGHT - 56
                        )
                    )

                draw_button(
                    update_button,
                    "UPDATE",
                    GOLD if painted_unknowns else (60, 66, 65),
                    text_color=BLACK if painted_unknowns else (
                        130, 138, 136
                    ),
                    dimmed=not painted_unknowns
                )

                draw_button(
                    solve_button,
                    "SOLVE",
                    CYAN if painted else (60, 66, 65),
                    text_color=BLACK if painted else (
                        130, 138, 136
                    ),
                    dimmed=not painted
                )

            # ------------------------------------------------
            # Control hints (bottom left, never under
            # the buttons)
            # ------------------------------------------------

            hint_surface = small_font.render(
                "ARROWS/ENTER: step    ESC: close",
                True,
                CAPTION_COLOR
            )

            screen.blit(
                hint_surface,
                (
                    VIEWER_MARGIN,
                    HEIGHT - 28
                )
            )

            # ==================================================
            # UPDATE
            # ==================================================

            pygame.display.flip()

            clock.tick(60)

    except StopIteration:
        pass

    finally:

        # ----------------------------------------------------
        # Give the editor its picker panel back at
        # the position it had before the viewer
        # borrowed it, then restore the editor
        # window itself.
        # ----------------------------------------------------

        panel_pos[:] = previous_panel_pos

        clear_picker_selection()

        screen = pygame.display.set_mode((WIDTH, HEIGHT))

        pygame.display.set_caption("Water Sort Bottle Editor")


# ============================================================
# COLOR PICKER LOGIC
# ============================================================

def clear_picker_selection():
    """
    Clears the active swatch and any RGB
    input focus in the shared color picker.
    """

    global selected_color
    global active_rgb_field

    selected_color = None
    active_rgb_field = None


def add_color_layer(bottle, color):
    """
    Adds one layer of 'color' to the bottle
    if there is still room.
    """

    if len(bottle["colors"]) < bottle["capacity"]:
        bottle["colors"].append(color)


def clear_selected_bottle():

    if selected_bottle is not None:
        selected_bottle["colors"] = []


def clear_all_bottles():

    for bottle in bottles:
        bottle["colors"] = []


def get_rgb_input_color():
    """
    Reads the R / G / B text boxes and turns
    them into one color tuple.
    """

    def channel(key):

        value = rgb_values[key]

        return min(int(value), 255) if value else 0

    return (
        channel("r"),
        channel("g"),
        channel("b")
    )


def add_color_to_user_palette():

    global active_palette
    global selected_color

    new_color = get_rgb_input_color()

    # --------------------------------------------------------
    # Duplicate: select the existing swatch
    # instead of adding it twice
    # --------------------------------------------------------

    if new_color in user_palette:

        selected_color = new_color

        # Switch to the user tab so the
        # selection is visible
        active_palette = "user"

        return

    if len(user_palette) >= MAX_USER_COLORS:
        return

    user_palette.append(new_color)

    save_user_palette(user_palette)

    # Select the newly added color
    selected_color = new_color


def remove_color_from_user_palette():

    global selected_color

    if selected_color in user_palette:

        user_palette.remove(selected_color)

        save_user_palette(user_palette)

        selected_color = None


def get_active_palette_colors():
    """
    The unknown color is always the very
    first swatch of every palette.
    """

    if active_palette == "user":
        return [UNKNOWN_COLOR] + user_palette

    return [UNKNOWN_COLOR] + WATER_COLORS


def get_swatch_rect(index):

    column = index % SWATCH_COLS
    row = index // SWATCH_COLS

    rect = get_panel_rect()

    return pygame.Rect(
        rect.x + 14 + column * SWATCH_STEP,
        rect.y + 58 + row * SWATCH_STEP,
        SWATCH_SIZE,
        SWATCH_SIZE
    )


def handle_panel_click(pos):
    """
    Handles a click inside the picker panel.
    """

    global active_palette
    global selected_color
    global active_rgb_field

    # --------------------------------------------------------
    # Palette tabs
    # --------------------------------------------------------

    if get_default_tab().collidepoint(pos):

        active_palette = "default"
        active_rgb_field = None
        return

    if get_user_tab().collidepoint(pos):

        active_palette = "user"
        active_rgb_field = None
        return

    # --------------------------------------------------------
    # User palette controls
    # --------------------------------------------------------

    if active_palette == "user":

        for key, box in get_rgb_boxes().items():

            if box.collidepoint(pos):

                active_rgb_field = key
                return

        if get_palette_add_button().collidepoint(pos):

            add_color_to_user_palette()
            return

        if get_palette_remove_button().collidepoint(pos):

            remove_color_from_user_palette()
            return

    active_rgb_field = None

    # --------------------------------------------------------
    # Color swatches
    #
    # If a bottle is selected, picking a color
    # adds it as a new layer to that bottle.
    #
    # Otherwise the color becomes the active
    # color (click again to deselect it).
    # --------------------------------------------------------

    colors = get_active_palette_colors()

    for index, color in enumerate(colors):

        if get_swatch_rect(index).collidepoint(pos):

            if selected_bottle is not None:
                add_color_layer(selected_bottle, color)

            elif selected_color == color:
                selected_color = None

            else:
                selected_color = color

            return


# ============================================================
# BOTTLE POSITION
#
# Every row has a shared bottom line.
# Bottles of a row stand on that line, so
# short and tall bottles end at the same
# height and their numbers line up.
# ============================================================

def get_row_range(target_row):
    """
    Returns (first_index, count) of the
    bottles belonging to a row.
    """

    first = target_row * bottles_per_row

    count = min(
        bottles_per_row,
        len(bottles) - first
    )

    return first, max(count, 0)


def get_row_tallest(first, count):

    return max(
        bottle["capacity"]
        for bottle in bottles[first : first + count]
    )


def get_row_top(target_row):
    """
    Y where a row begins.

    Each previous row takes up as much space
    as its tallest bottle plus one gap.
    """

    top_y = FIRST_ROW_TOP

    for row in range(target_row):

        first, count = get_row_range(row)

        if count <= 0:
            break

        tallest = get_row_tallest(first, count)

        top_y += (
            bottle_height(tallest)
            + ROW_GAP
        )

    return top_y


def get_row_baseline(target_row):
    """
    Bottom line of a row where all of its
    bottles are standing on.
    """

    first, count = get_row_range(target_row)

    if count <= 0:
        return get_row_top(target_row)

    tallest = get_row_tallest(first, count)

    return (
        get_row_top(target_row)
        + bottle_height(tallest)
    )


def get_bottle_rect(index, bottle):

    column = index % bottles_per_row
    row = index // bottles_per_row

    x = 40 + column * (
        BOTTLE_WIDTH + BOTTLE_GAP
    )

    height_pixels = bottle_height(
        bottle["capacity"]
    )

    y = (
        get_row_baseline(row)
        - height_pixels
    )

    return pygame.Rect(
        x,
        y,
        BOTTLE_WIDTH,
        height_pixels
    )


# ============================================================
# DRAW BOTTLE
# ============================================================

# ============================================================
# RENDER BOTTLE IMAGE
#
# Draws one bottle into a standalone surface
# so both the editor and the solution viewer
# can display bottles.
# ============================================================

def render_bottle_image(capacity, colors, bottle_width, layer_height):

    # ========================================================
    # HIGH RESOLUTION BOTTLE
    # ========================================================

    S = BOTTLE_SCALE

    width = bottle_width
    height = bottle_height(capacity, layer_height)

    W = width * S
    H = height * S

    wall = int(
        BOTTLE_WALL
        * S
        * layer_height
        / BOTTLE_LAYER_HEIGHT
    )

    # Radius of the rounded bottom.
    #
    # The bottle width is 62, so the radius is roughly 29.
    radius = (W - wall) / 2

    center_x = W / 2

    # Center of the semicircle.
    bottom = H - wall
    curve_center_y = bottom - radius

    # ========================================================
    # CREATE BOTTLE SHAPE
    # ========================================================

    def make_bottle_points():

        points = []

        # ----------------------------------------------------
        # Top-left
        # ----------------------------------------------------

        points.append(
            (wall / 2, wall / 2)
        )

        # ----------------------------------------------------
        # Down left side
        # ----------------------------------------------------

        points.append(
            (
                wall / 2,
                curve_center_y
            )
        )

        # ----------------------------------------------------
        # Bottom semicircle
        #
        # theta goes from 180 degrees -> 0 degrees.
        #
        # This creates:
        #
        #       \        /
        #        \______/
        #
        # instead of a polygonal-looking corner.
        # ----------------------------------------------------

        segments = 2 ** 10

        for i in range(segments + 1):

            theta = math.pi - (
                math.pi * i / segments
            )

            x = (
                center_x
                + radius * math.cos(theta)
            )

            y = (
                curve_center_y
                + radius * math.sin(theta)
            )

            points.append((x, y))

        # ----------------------------------------------------
        # Right side
        # ----------------------------------------------------

        points.append(
            (
                W - wall / 2,
                wall / 2
            )
        )

        return points

    bottle_points = make_bottle_points()

    # ========================================================
    # LIQUID SURFACE
    # ========================================================

    liquid_surface = pygame.Surface(
        (W, H),
        pygame.SRCALPHA
    )

    colors = list(colors)

    # --------------------------------------------------------
    # Draw each liquid layer
    #
    # Unknown layers stay empty; their question
    # marks are stamped on later (after the
    # liquid got clipped to the bottle shape).
    # --------------------------------------------------------

    # Every cell gets exactly 'layer_height' pixels,
    # anchored to the glass floor. The bottle surface is
    # one BOTTLE_LIP taller than the cells, so even a
    # completely full bottle keeps a thin empty rim at
    # the top instead of clipping its topmost tile.
    cell_height = layer_height * S

    unknown_layer_centers = []

    for layer_index, color in enumerate(colors):

        layer_top = (
            bottom
            - layer_index * cell_height
            - cell_height
        )

        if color == UNKNOWN_COLOR:

            unknown_layer_centers.append(
                (
                    center_x,
                    layer_top + cell_height / 2
                )
            )

            continue

        pygame.draw.rect(
            liquid_surface,
            color,
            pygame.Rect(
                wall / 2,
                layer_top,
                W - wall,
                cell_height + 1
            )
        )

    # ========================================================
    # BOTTLE INTERIOR MASK
    # ========================================================

    mask_surface = pygame.Surface(
        (W, H),
        pygame.SRCALPHA
    )

    # --------------------------------------------------------
    # Interior shape
    # --------------------------------------------------------

    inner_wall = wall

    inner_radius = (
        (W - inner_wall * 2) / 2
    )

    inner_center_x = W / 2

    inner_bottom = H - inner_wall

    inner_curve_center_y = (
        inner_bottom - inner_radius
    )

    interior_points = []

    # Left upper corner
    #
    # Let the liquid reach the very top of the bottle
    # interior. The glass outline is drawn afterwards,
    # so the liquid still stays visually inside the
    # glass while every color layer keeps the same
    # height as the others.
    interior_points.append(
        (
            0,
            0
        )
    )

    # Left side
    interior_points.append(
        (
            inner_wall,
            inner_curve_center_y
        )
    )

    # Smooth bottom
    segments = 2 ** 10

    for i in range(segments + 1):

        theta = math.pi - (
            math.pi * i / segments
        )

        x = (
            inner_center_x
            + inner_radius * math.cos(theta)
        )

        y = (
            inner_curve_center_y
            + inner_radius * math.sin(theta)
        )

        interior_points.append((x, y))

    # Right upper corner
    interior_points.append(
        (
            W,
            0
        )
    )

    pygame.draw.polygon(
        mask_surface,
        (255, 255, 255, 255),
        interior_points
    )

    # ========================================================
    # CLIP LIQUID TO BOTTLE
    # ========================================================

    liquid_surface.blit(
        mask_surface,
        (0, 0),
        special_flags=pygame.BLEND_RGBA_MULT
    )

    # ========================================================
    # HIGH RESOLUTION BOTTLE SURFACE
    # ========================================================

    bottle_surface = pygame.Surface(
        (W, H),
        pygame.SRCALPHA
    )

    # Draw liquid
    bottle_surface.blit(
        liquid_surface,
        (0, 0)
    )

    # ========================================================
    # QUESTION MARKS FOR UNKNOWN LAYERS
    # ========================================================

    for mark_center in unknown_layer_centers:

        question_size = max(
            8,
            int(
                26
                * BOTTLE_SCALE
                * width
                / BOTTLE_WIDTH
            )
        )

        question_surface = get_question_font(
            question_size
        ).render(
            "?",
            True,
            WHITE
        )

        # Center the visible ink of the glyph,
        # not its whole line box, so the "?"
        # sits truly in the middle of its layer
        ink_rect = question_surface.get_bounding_rect()

        bottle_surface.blit(
            question_surface,
            (
                mark_center[0]
                - ink_rect.centerx,

                mark_center[1]
                - ink_rect.centery
            )
        )

    # ========================================================
    # GLASS OUTLINE
    # ========================================================

    glass_width = wall

    # Smooth glass outline
    pygame.draw.lines(
        bottle_surface,
        GLASS_COLOR,
        False,
        bottle_points,
        glass_width
    )

    # ========================================================
    # TOP EDGE
    # ========================================================

    pygame.draw.line(
        bottle_surface,
        GLASS_COLOR,
        (
            wall / 2,
            wall / 2
        ),
        (
            W - wall / 2,
            wall / 2
        ),
        glass_width
    )

    # ========================================================
    # DOWNSCALE
    # ========================================================

    smooth_bottle = pygame.transform.smoothscale(
        bottle_surface,
        (width, height)
    )

    return smooth_bottle


# Image cache keyed by capacity, colors and
# size. The editor redraws every bottle
# every frame, so this saves a lot of work.
_bottle_image_cache = {}


def get_bottle_image(
    capacity,
    colors,
    bottle_width=BOTTLE_WIDTH,
    layer_height=BOTTLE_LAYER_HEIGHT
):

    key = (
        capacity,
        tuple(colors),
        bottle_width,
        layer_height
    )

    image = _bottle_image_cache.get(key)

    if image is None:

        image = render_bottle_image(
            capacity,
            colors,
            bottle_width,
            layer_height
        )

        _bottle_image_cache[key] = image

    return image


# ============================================================
# DRAW BOTTLE (EDITOR)
# ============================================================

def draw_bottle(index, bottle):

    rect = get_bottle_rect(index, bottle)

    smooth_bottle = get_bottle_image(
        bottle["capacity"],
        tuple(bottle["colors"])
    )

    screen.blit(
        smooth_bottle,
        rect.topleft
    )

    # ========================================================
    # SELECTED BOTTLE
    # ========================================================

    if bottle is selected_bottle:

        pygame.draw.rect(
            screen,
            YELLOW,
            rect.inflate(10, 10),
            width=3,
            border_radius=10
        )

    # ========================================================
    # NUMBER
    # ========================================================

    number_text = font.render(
        str(index + 1),
        True,
        WHITE
    )

    screen.blit(
        number_text,
        (
            rect.centerx
            - number_text.get_width() // 2,

            rect.bottom + 8
        )
    )


# ============================================================
# DRAW BUTTON
# ============================================================

def adjust_color(color, amount):
    """
    Makes a color lighter (positive amount)
    or darker (negative amount).
    """

    r, g, b = color

    return (
        max(0, min(r + amount, 255)),
        max(0, min(g + amount, 255)),
        max(0, min(b + amount, 255))
    )


def blit_optical_centered(
    target_surface,
    text_surface,
    center_x,
    center_y
):
    """
    Centers the visible ink of a rendered
    text, not its whole line box.

    Without this, symbols like "+" or "?"
    look slightly off-center because their
    glyph does not fill the full font height.
    """

    ink_rect = text_surface.get_bounding_rect()

    target_surface.blit(
        text_surface,
        (
            center_x - ink_rect.centerx,
            center_y - ink_rect.centery
        )
    )


def draw_button(
    rect,
    text,
    color,
    text_color=BLACK,
    dimmed=False
):

    # --------------------------------------------------------
    # Lighter while the mouse is over it
    # (disabled buttons never highlight)
    # --------------------------------------------------------

    hovered = (
        rect.collidepoint(pygame.mouse.get_pos())
        and not dimmed
    )

    fill_color = (
        adjust_color(color, 35)
        if hovered
        else color
    )

    pygame.draw.rect(
        screen,
        fill_color,
        rect,
        border_radius=10
    )

    pygame.draw.rect(
        screen,
        adjust_color(fill_color, -70),
        rect,
        width=2,
        border_radius=10
    )

    text_surface = small_font.render(
        text,
        True,
        text_color
    )

    blit_optical_centered(
        screen,
        text_surface,
        rect.centerx,
        rect.centery
    )


def draw_control_group(
    panel_rect,
    down_button,
    up_button,
    caption,
    value_text
):
    """
    Draws one control group:

        [caption]
      [ - ]  4  [ + ]
    """

    # --------------------------------------------------------
    # Panel
    # --------------------------------------------------------

    pygame.draw.rect(
        screen,
        GROUP_BG,
        panel_rect,
        border_radius=12
    )

    pygame.draw.rect(
        screen,
        adjust_color(GROUP_BG, 30),
        panel_rect,
        width=2,
        border_radius=12
    )

    # --------------------------------------------------------
    # Caption above the panel
    # --------------------------------------------------------

    caption_surface = small_font.render(
        caption,
        True,
        CAPTION_COLOR
    )

    screen.blit(
        caption_surface,
        (
            panel_rect.centerx
            - caption_surface.get_width() // 2,

            panel_rect.y
            - caption_surface.get_height()
            - 5
        )
    )

    # --------------------------------------------------------
    # Minus / plus buttons
    # --------------------------------------------------------

    draw_button(down_button, "-", LIGHT_GRAY)
    draw_button(up_button, "+", LIGHT_GRAY)

    # --------------------------------------------------------
    # Value between them
    # --------------------------------------------------------

    if value_text:

        value_surface = font.render(
            value_text,
            True,
            WHITE
        )

        blit_optical_centered(
            screen,
            value_surface,
            panel_rect.centerx,
            panel_rect.centery
        )


# ============================================================
# DRAW COLOR PICKER
# ============================================================

def draw_color_picker():

    # --------------------------------------------------------
    # Panel background (slightly translucent)
    # --------------------------------------------------------

    panel_rect = get_panel_rect()

    panel_surface = pygame.Surface(
        (panel_rect.w, panel_rect.h),
        pygame.SRCALPHA
    )

    panel_surface.fill(
        (20, 45, 44, 235)
    )

    screen.blit(
        panel_surface,
        panel_rect.topleft
    )

    pygame.draw.rect(
        screen,
        GLASS_COLOR,
        panel_rect,
        width=2,
        border_radius=10
    )

    # --------------------------------------------------------
    # Palette tabs
    # --------------------------------------------------------

    draw_button(
        get_default_tab(),
        "DEFAULT",
        LIGHT_GRAY if active_palette == "default" else DARK_GRAY
    )

    draw_button(
        get_user_tab(),
        "USER",
        LIGHT_GRAY if active_palette == "user" else DARK_GRAY
    )

    # --------------------------------------------------------
    # Color swatches
    # --------------------------------------------------------

    colors = get_active_palette_colors()

    for index, color in enumerate(colors):

        swatch_rect = get_swatch_rect(index)

        # ------------------------------------------------
        # Swatch fill
        # ------------------------------------------------

        if color == UNKNOWN_COLOR:

            # Empty space with a question mark
            pygame.draw.rect(
                screen,
                BACKGROUND,
                swatch_rect,
                border_radius=6
            )

            question_surface = small_font.render(
                "?",
                True,
                WHITE
            )

            blit_optical_centered(
                screen,
                question_surface,
                swatch_rect.centerx,
                swatch_rect.centery
            )

        else:

            pygame.draw.rect(
                screen,
                color,
                swatch_rect,
                border_radius=6
            )

        # ------------------------------------------------
        # Selection outline
        # ------------------------------------------------

        if selected_color == color:

            pygame.draw.rect(
                screen,
                YELLOW,
                swatch_rect.inflate(8, 8),
                width=3,
                border_radius=9
            )

        else:

            outline_color = (
                GLASS_COLOR if color == UNKNOWN_COLOR
                else BLACK
            )

            pygame.draw.rect(
                screen,
                outline_color,
                swatch_rect,
                width=1,
                border_radius=6
            )

    # --------------------------------------------------------
    # User palette controls
    # --------------------------------------------------------

    if active_palette == "user":

        for key, box in get_rgb_boxes().items():

            box_color = (
                WHITE if active_rgb_field == key
                else LIGHT_GRAY
            )

            pygame.draw.rect(
                screen,
                box_color,
                box,
                border_radius=6
            )

            value_text = small_font.render(
                rgb_values[key],
                True,
                BLACK
            )

            screen.blit(
                value_text,
                (
                    box.centerx
                    - value_text.get_width() // 2,

                    box.centery
                    - value_text.get_height() // 2
                )
            )

            label = small_font.render(
                key.upper(),
                True,
                WHITE
            )

            screen.blit(
                label,
                (
                    box.x + 4,
                    box.y - 22
                )
            )

        draw_button(
            get_palette_add_button(),
            "ADD",
            GREEN
        )

        draw_button(
            get_palette_remove_button(),
            "REMOVE SELECTED",
            RED
        )


# ============================================================
# MAIN LOOP
# ============================================================

while True:

    # ========================================================
    # EVENTS
    # ========================================================

    for event in pygame.event.get():

        if event.type == pygame.QUIT:

            save_bottles()

            pygame.quit()
            sys.exit()

        if event.type == pygame.MOUSEBUTTONDOWN:

            mouse_pos = event.pos

            # =================================================
            # ADD
            # =================================================

            if ADD_BUTTON.collidepoint(mouse_pos):

                add_bottle()

            # =================================================
            # REMOVE
            # =================================================

            elif REMOVE_BUTTON.collidepoint(mouse_pos):

                remove_bottle()

            # =================================================
            # NEW BOTTLE HEIGHT -
            # =================================================

            elif HEIGHT_DOWN_BUTTON.collidepoint(mouse_pos):

                decrease_new_height()

            # =================================================
            # NEW BOTTLE HEIGHT +
            # =================================================

            elif HEIGHT_UP_BUTTON.collidepoint(mouse_pos):

                increase_new_height()

            # =================================================
            # ALL BOTTLES HEIGHT -
            # =================================================

            elif ALL_DOWN_BUTTON.collidepoint(mouse_pos):

                decrease_all_heights()

            # =================================================
            # ALL BOTTLES HEIGHT +
            # =================================================

            elif ALL_UP_BUTTON.collidepoint(mouse_pos):

                increase_all_heights()

            # =================================================
            # BOTTLES PER ROW -
            # =================================================

            elif ROW_DOWN_BUTTON.collidepoint(mouse_pos):

                decrease_bottles_per_row()

            # =================================================
            # BOTTLES PER ROW +
            # =================================================

            elif ROW_UP_BUTTON.collidepoint(mouse_pos):

                increase_bottles_per_row()

            # =================================================
            # COLORS PANEL OPEN / CLOSE
            # =================================================

            elif COLORS_BUTTON.collidepoint(mouse_pos):

                panel_open = not panel_open
                active_rgb_field = None

            # =================================================
            # CLEAR SELECTED BOTTLE
            # =================================================

            elif CLEAR_BUTTON.collidepoint(mouse_pos):

                clear_selected_bottle()

            # =================================================
            # CLEAR EVERY BOTTLE
            # =================================================

            elif CLEAR_ALL_BUTTON.collidepoint(mouse_pos):

                clear_all_bottles()

            # =================================================
            # SOLVE
            # =================================================

            elif SOLVE_BUTTON.collidepoint(mouse_pos):

                solve_puzzle()

            # =================================================
            # RESET EVERYTHING
            # =================================================

            elif RESET_BUTTON.collidepoint(mouse_pos):

                reset_editor()

            # =================================================
            # COLOR PICKER PANEL
            #
            # Clicks on tabs / swatches / user
            # controls go to the panel handler;
            # clicks on any empty spot of the panel
            # grab it for dragging.
            # =================================================

            elif panel_open and get_panel_rect().collidepoint(
                mouse_pos
            ):

                def panel_spot_is_empty():

                    busy = [
                        get_default_tab(),
                        get_user_tab()
                    ]

                    colors = get_active_palette_colors()

                    for index in range(len(colors)):

                        busy.append(
                            get_swatch_rect(index)
                        )

                    if active_palette == "user":

                        busy.extend(
                            get_rgb_boxes().values()
                        )

                        busy.append(
                            get_palette_add_button()
                        )

                        busy.append(
                            get_palette_remove_button()
                        )

                    return not any(
                        rect.collidepoint(mouse_pos)
                        for rect in busy
                    )

                if panel_spot_is_empty():

                    panel_drag_offset = (
                        mouse_pos[0] - panel_pos[0],
                        mouse_pos[1] - panel_pos[1]
                    )

                else:

                    handle_panel_click(mouse_pos)

            # =================================================
            # CLICK BOTTLE
            #
            # If a color is picked, clicking a bottle
            # adds that color as one new layer.
            #
            # Otherwise clicking selects the bottle.
            # =================================================

            else:

                clicked_bottle = None

                # Search backwards
                for index in range(
                    len(bottles) - 1,
                    -1,
                    -1
                ):

                    bottle = bottles[index]

                    rect = get_bottle_rect(
                        index,
                        bottle
                    )

                    # Include the neck area in selection
                    click_rect = rect.inflate(
                        20,
                        25
                    )

                    if click_rect.collidepoint(
                        mouse_pos
                    ):

                        clicked_bottle = bottle
                        break

                # =================================================
                # SELECT / ADD LAYER / DESELECT
                # =================================================

                if clicked_bottle is not None:

                    if selected_color is not None:

                        add_color_layer(
                            clicked_bottle,
                            selected_color
                        )

                    elif clicked_bottle is selected_bottle:

                        selected_bottle = None

                    else:

                        selected_bottle = clicked_bottle

                # Click empty space -> deselect
                else:

                    selected_bottle = None

        # =====================================================
        # KEYBOARD (RGB INPUT BOXES)
        # =====================================================

        elif event.type == pygame.KEYDOWN:

            if active_rgb_field is not None:

                if event.key == pygame.K_BACKSPACE:

                    rgb_values[active_rgb_field] = (
                        rgb_values[active_rgb_field][:-1]
                    )

                elif (
                    event.unicode.isdigit()
                    and len(rgb_values[active_rgb_field]) < 3
                ):

                    rgb_values[active_rgb_field] += (
                        event.unicode
                    )

            # =================================================
            # HOTKEYS (no RGB field active)
            #
            #   BACKSPACE  clears the selected bottle's colors
            #   DELETE     removes the selected bottle; if no
            #              bottle is selected it removes the
            #              selected color - but only while on
            #              the user's own palette tab (the
            #              built-in colors can not be edited)
            # =================================================

            else:

                if event.key == pygame.K_BACKSPACE:

                    clear_selected_bottle()

                elif event.key == pygame.K_DELETE:

                    if selected_bottle is not None:

                        remove_bottle()

                    elif (
                        selected_color is not None
                        and active_palette == "user"
                    ):

                        remove_color_from_user_palette()

        # =====================================================
        # MOUSE MOTION: DRAG THE PICKER PANEL
        # =====================================================

        elif (
            event.type == pygame.MOUSEMOTION
            and panel_drag_offset is not None
        ):

            panel_pos[0] = max(
                0,
                min(
                    event.pos[0] - panel_drag_offset[0],
                    WIDTH - PANEL_WIDTH
                )
            )

            panel_pos[1] = max(
                0,
                min(
                    event.pos[1] - panel_drag_offset[1],
                    HEIGHT - PANEL_HEIGHT
                )
            )

        # =====================================================
        # MOUSE BUTTON UP: RELEASE THE PICKER PANEL
        # =====================================================

        elif (
            event.type == pygame.MOUSEBUTTONUP
            and event.button == 1
        ):

            panel_drag_offset = None

    # ========================================================
    # DRAW BACKGROUND
    # ========================================================

    screen.fill(BACKGROUND)

    # ========================================================
    # DRAW BUTTONS
    # ========================================================

    draw_button(
        ADD_BUTTON,
        "ADD",
        GREEN
    )

    draw_button(
        REMOVE_BUTTON,
        "REMOVE",
        RED
    )

    draw_button(
        RESET_BUTTON,
        "RESET",
        GOLD
    )

    draw_control_group(
        HEIGHT_GROUP,
        HEIGHT_DOWN_BUTTON,
        HEIGHT_UP_BUTTON,
        "NEW HEIGHT",
        str(new_bottle_height)
    )

    draw_control_group(
        ALL_GROUP,
        ALL_DOWN_BUTTON,
        ALL_UP_BUTTON,
        "ALL HEIGHTS",
        ""
    )

    draw_control_group(
        ROW_GROUP,
        ROW_DOWN_BUTTON,
        ROW_UP_BUTTON,
        "PER ROW",
        str(bottles_per_row)
    )

    draw_button(
        COLORS_BUTTON,
        "COLORS",
        LIGHT_BLUE
    )

    draw_button(
        CLEAR_BUTTON,
        "CLEAR SEL",
        RED
    )

    draw_button(
        CLEAR_ALL_BUTTON,
        "CLEAR ALL",
        DARK_RED
    )

    # --------------------------------------------------------
    # SOLVE button:
    #
    # - no colors anywhere  -> disabled
    # - unknown "?" inside  -> purple "SOLVE ?"
    # - otherwise           -> cyan "SOLVE"
    # --------------------------------------------------------

    if not bottles_have_any_color():

        draw_button(
            SOLVE_BUTTON,
            "SOLVE",
            (60, 66, 65),
            text_color=(130, 138, 136),
            dimmed=True
        )

    elif bottles_have_unknown():

        draw_button(
            SOLVE_BUTTON,
            "SOLVE ?",
            PURPLE
        )

    else:

        draw_button(
            SOLVE_BUTTON,
            "SOLVE",
            CYAN
        )

    # ========================================================
    # ACTIVE COLOR INDICATOR
    # ========================================================

    if selected_color is not None:

        fill_color = (
            BACKGROUND
            if selected_color == UNKNOWN_COLOR
            else selected_color
        )

        pygame.draw.rect(
            screen,
            fill_color,
            ACTIVE_COLOR_INDICATOR,
            border_radius=8
        )

        pygame.draw.rect(
            screen,
            BLACK,
            ACTIVE_COLOR_INDICATOR,
            width=2,
            border_radius=8
        )

        if selected_color == UNKNOWN_COLOR:

            question_surface = small_font.render(
                "?",
                True,
                WHITE
            )

            blit_optical_centered(
                screen,
                question_surface,
                ACTIVE_COLOR_INDICATOR.centerx,
                ACTIVE_COLOR_INDICATOR.centery
            )

    # ========================================================
    # ACTIVE COLOR INDICATOR
    #
    # (drawn above with the buttons)
    # ========================================================

    # ========================================================
    # DRAW BOTTLES
    # ========================================================

    for index, bottle in enumerate(bottles):

        draw_bottle(
            index,
            bottle
        )

    # ========================================================
    # DRAW COLOR PICKER (on top of bottles)
    # ========================================================

    if panel_open:

        draw_color_picker()

    # ========================================================
    # UPDATE
    # ========================================================

    pygame.display.flip()

    clock.tick(60)
