import math
from unittest.mock import Mock

import pytest
from travertino.size import at_least

from toga.style.pack import COLUMN, NORMAL, PRE, PRE_WRAP, ROW, Pack

from ..utils import ExampleNode, ExampleViewport

# A synthetic "reflowable text" model for the example backend. The real per-backend
# wrapping fidelity is exercised by the testbed; here we only validate the engine
# plumbing: that a node's height is recomputed for the width the layout assigns it.
LINE_HEIGHT = 20
SINGLE_LINE_WIDTH = 400  # width the text would need on a single line
MIN_WORD_WIDTH = 60  # width of the widest unbreakable token (min-content width)


def wrapped_height(width):
    """Height the synthetic text needs when reflowed into ``width``."""
    usable = max(int(width), MIN_WORD_WIDTH)
    lines = max(1, math.ceil(SINGLE_LINE_WIDTH / usable))
    return lines * LINE_HEIGHT


def make_label(white_space=NORMAL, **style):
    """An ExampleNode that behaves like a reflowable label.

    Its backend reports a flexible min-content width and recomputes its height for the
    width it is assigned (height-for-width), like a wrapping Label's backend.
    """
    node = ExampleNode("label", style=Pack(white_space=white_space, **style))
    if white_space == PRE:
        # Non-wrapping: minimum width is the whole single line, height is fixed.
        node.intrinsic.width = at_least(SINGLE_LINE_WIDTH)
    else:
        # Wrapping: the min-content floor is the widest token; the max-content (single
        # line) width and the height come from measurement.
        node.intrinsic.width = at_least(MIN_WORD_WIDTH)
        node._impl.measure_text_width = Mock(return_value=SINGLE_LINE_WIDTH)
    node.intrinsic.height = LINE_HEIGHT  # single-line fallback
    node._impl.measure_text_height = Mock(side_effect=wrapped_height)
    return node


def column_with_label(label, viewport_width, viewport_height=600):
    root = ExampleNode("root", style=Pack(direction=COLUMN), children=[label])
    root.style.layout(ExampleViewport(viewport_width, viewport_height))
    return root


@pytest.mark.parametrize(
    "white_space",
    [NORMAL, PRE_WRAP],
)
@pytest.mark.parametrize(
    "viewport_width, expected_width, expected_height",
    [
        (400, 400, 20),  # fits on one line
        (200, 200, 40),  # wraps to two lines
        (100, 100, 80),  # wraps to four lines
    ],
)
def test_height_for_width(white_space, viewport_width, expected_width, expected_height):
    """A wrapping label gets shorter as it gets wider, and taller as it narrows."""
    label = make_label(white_space=white_space)
    column_with_label(label, viewport_width)

    assert label.layout.content_width == expected_width
    assert label.layout.content_height == expected_height
    # The backend was asked for the height at exactly the width it was allocated.
    label._impl.measure_text_height.assert_called_with(expected_width)


def test_min_content_width_floor():
    """A wrapping label is never squeezed narrower than its widest token."""
    label = make_label()
    # Viewport narrower than the widest token: the label uses its min-content width.
    column_with_label(label, 30)

    assert label.layout.content_width == MIN_WORD_WIDTH
    assert label.layout.content_height == wrapped_height(MIN_WORD_WIDTH)
    label._impl.measure_text_height.assert_called_with(MIN_WORD_WIDTH)
    # The node also reports that floor as its minimum width.
    assert label.layout.min_width == MIN_WORD_WIDTH


def test_pre_does_not_reflow():
    """The default ``white-space: pre`` is byte-identical to single-pass behavior."""
    label = make_label(white_space=PRE)
    # Column narrower than the single-line width: a wrapping label would reflow, but a
    # `pre` label keeps its full single-line width and fixed single-line height.
    column_with_label(label, 200)

    assert label.layout.content_width == SINGLE_LINE_WIDTH
    assert label.layout.content_height == LINE_HEIGHT
    # The height-for-width path is never invoked for non-wrapping content.
    label._impl.measure_text_height.assert_not_called()


def test_explicit_height_overrides_measurement():
    """An explicit height wins over the measured height-for-width."""
    label = make_label(height=123)
    column_with_label(label, 100)

    assert label.layout.content_height == 123
    label._impl.measure_text_height.assert_not_called()


def test_row_without_flex_uses_max_content():
    """A non-flex reflowable widget in a row takes its single-line (max-content) width.

    This matches CSS ``flex: <f> 0 auto`` (which Pack emits for an auto-width box):
    flex-shrink is 0, so the widget does not shrink below its content and does not wrap.
    Its min-content (widest token) is still reported as the minimum width.
    """
    label = make_label()
    root = ExampleNode("root", style=Pack(direction=ROW), children=[label])
    root.style.layout(ExampleViewport(500, 600))

    assert label.layout.content_width == SINGLE_LINE_WIDTH  # single line, no wrap
    assert label.layout.content_height == LINE_HEIGHT
    assert label.layout.min_width == MIN_WORD_WIDTH  # min-content floor still reported
    label._impl.measure_text_width.assert_called_once()
    label._impl.measure_text_height.assert_called_with(SINGLE_LINE_WIDTH)


def test_row_with_explicit_width_wraps():
    """An explicit width in a row makes a reflowable widget wrap to that width."""
    label = make_label(width=200)
    root = ExampleNode("root", style=Pack(direction=ROW), children=[label])
    root.style.layout(ExampleViewport(500, 600))

    assert label.layout.content_width == 200
    assert label.layout.content_height == 40  # two lines at width 200
    # An explicit width is the basis; max-content is not consulted.
    label._impl.measure_text_width.assert_not_called()
    label._impl.measure_text_height.assert_called_with(200)


def test_row_with_flex_wraps_to_allocated_width():
    """A flex reflowable widget in a row wraps to the width flex gives it."""
    label = make_label(flex=1)
    root = ExampleNode("root", style=Pack(direction=ROW), children=[label])
    root.style.layout(ExampleViewport(500, 600))

    assert label.layout.content_width == 500
    assert label.layout.content_height == 20  # one line at full width
    label._impl.measure_text_height.assert_called_with(500)


def test_row_reflowable_without_max_content_falls_back_to_min_content():
    """If a backend can't report a max-content width, the row falls back to min-content.

    Defensive: a reflowable widget whose backend returns None for the max-content width
    collapses to its min-content floor rather than erroring.
    """
    label = make_label()
    label._impl.measure_text_width = Mock(return_value=None)
    root = ExampleNode("root", style=Pack(direction=ROW), children=[label])
    root.style.layout(ExampleViewport(500, 600))

    assert label.layout.content_width == MIN_WORD_WIDTH
    label._impl.measure_text_height.assert_called_with(MIN_WORD_WIDTH)
