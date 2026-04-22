# NOTE: this file was taken from https://github.com/Aperence/FFSexp3-master-thesis/blob/main/evaluation/plotting/style.py

# Constants used to plot with latex font
# Scripts provided by Louis Navarre

COLORS = ["#d7191c", "#fdae61", "#2b83ba", "#abd9e9", "#abdda4", "#999999"]
COLORS_GREY = ["dimgray", "silver", "white"]
COLORS_BLACK_WHITE = ["black", "dimgray", "silver", "white"]
COLORS_SEQUENTIAL_5 = ["#253494", "#2c7fb8", "#41b6c4", "#a1dab4", "#ffffcc"]
COLORS_SEQUENTIAL_4 = ["#253494", "#2c7fb8", "#a1dab4", "#ffffcc"]
COLORS_SEQUENTIAL_3 = ["#253494", "#41b6c4", "#ffffcc"]
COLORS_SEQUENTIAL_2 = ["#2c7fb8", "#ffffcc"]
MARKERS = ["d", "s", "D", "v", "P", "*", "^"]
LINESTYLES = [
    "solid",
    (0, (1, 1)),
    "dashed",
    "dashdot",
    (5, (10, 3)),
    (0, (3, 1, 1, 1)),
]
LINEWIDTH = 1.5
MARKERSIZE = 8
HANDLETEXTPAD = 0.2
HANDLELENGTH = 2.5
FIG_HEIGHT = 3.5
FONT_SIZE = 15
LABEL_FONT_SIZE = FONT_SIZE + 5
CONFIDENCE_BAND_OPACITY = 0.2

NO_RELAY_COLOR = COLORS[1]
NO_RELAY_LINESTYLE = LINESTYLES[0]
NO_RELAY_MARKER = MARKERS[0]

APP_RELAY_COLOR = COLORS[4]
APP_RELAY_LINESTYLE = LINESTYLES[4]
APP_RELAY_MARKER = MARKERS[3]

FCQUIC_RELAY_COLOR = COLORS[3]
FCQUIC_RELAY_LINESTYLE = LINESTYLES[3]
FCQUIC_RELAY_MARKER = MARKERS[1]


def latexify(fig_width=None, fig_height=None, columns=2, nb_subplots_line=1):
    """Set up matplotlib's RC params for LaTeX plotting.
    Call this before plotting a figure.
    Parameters
    ----------
    fig_width : float, optional, inches
    fig_height : float,  optional, inches
    columns : {1, 2}
    """

    # code adapted from http://www.scipy.org/Cookbook/Matplotlib/LaTeX_Examples
    # also adapted from http://bkanuka.com/posts/native-latex-plots/

    # Width and max height in inches for IEEE journals taken from
    # computer.org/cms/Computer.org/Journal%20templates/transactions_art_guide.pdf

    from math import sqrt

    import matplotlib

    assert columns in [1, 2]

    if fig_width is None:
        # Get this from LaTeX using \the\textwidth
        fig_width_pt = 418.25368
        inches_per_pt = 1.0 / 72.27  # Convert pt to inch
        scale = 3.39 / 6.9 if columns == 1 else 1
        fig_width = fig_width_pt * inches_per_pt * scale  # width in inches
        # fig_width = 3.39 if columns==1 else 6.9 # width in inches

    if fig_height is None:
        golden_mean = (sqrt(5) - 1.0) / 2.0  # Aesthetic ratio
        fig_height = fig_width * golden_mean  # height in inches

    fig_width *= nb_subplots_line

    # MAX_HEIGHT_INCHES = 8.0
    # if fig_height > MAX_HEIGHT_INCHES:
    #     print(
    #         "WARNING: fig_height too large {}: so will reduce to {} inches.".format(
    #             fig_height, MAX_HEIGHT_INCHES
    #         )
    #     )
    #     fig_height = MAX_HEIGHT_INCHES
    params = {
        "backend": "ps",
        "text.latex.preamble": r"\usepackage[T1]{fontenc} \usepackage{gensymb}",
        "axes.labelsize": LABEL_FONT_SIZE,  # fontsize for x and y labels (was 10)
        "axes.titlesize": LABEL_FONT_SIZE,
        "font.size": FONT_SIZE,  # was 10
        "legend.fontsize": FONT_SIZE,  # was 10
        "xtick.labelsize": FONT_SIZE,
        "ytick.labelsize": FONT_SIZE,
        "text.usetex": True,
        "figure.figsize": [fig_width, fig_height],
        "pgf.texsystem": "pdflatex",
        "grid.alpha": 0.25,
        "mathtext.default": "regular",  # Don't italize math text
        "font.family": "serif",
    }

    matplotlib.rcParams.update(params)
