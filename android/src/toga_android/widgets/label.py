from decimal import ROUND_UP
from math import ceil

from android.os import Build
from android.text import Layout
from android.util import TypedValue
from android.view import Gravity, View
from android.widget import TextView
from travertino.constants import NORMAL, PRE_WRAP
from travertino.size import at_least

from toga.constants import JUSTIFY
from toga_android.colors import native_color

from .base import Widget, android_text_align


def set_textview_font(textview, font, default_typeface, default_size):
    textview.setTypeface(font.typeface(default=default_typeface))
    textview.setTextSize(TypedValue.COMPLEX_UNIT_PX, font.size(default=default_size))


class TextViewWidget(Widget):
    def cache_textview_defaults(self):
        self._default_text_color = self.native.getCurrentTextColor()
        self._default_text_size = self.native.getTextSize()
        self._default_typeface = self.native.getTypeface()

    def set_font(self, font):
        set_textview_font(
            self.native, font._impl, self._default_typeface, self._default_text_size
        )

    def set_color(self, value):
        if value is None:
            self.native.setTextColor(self._default_text_color)
        else:
            self.native.setTextColor(native_color(value))

    def set_textview_alignment(self, value, vertical_gravity):
        # Justified text wasn't added until API level 26.
        # We only run the test suite on API 31, so we need to disable branch coverage.
        if Build.VERSION.SDK_INT >= 26:  # pragma: no branch
            self.native.setJustificationMode(
                Layout.JUSTIFICATION_MODE_INTER_WORD
                if value == JUSTIFY
                else Layout.JUSTIFICATION_MODE_NONE
            )

        self.native.setGravity(vertical_gravity | android_text_align(value))


class Label(TextViewWidget):
    def create(self):
        self.native = TextView(self._native_activity)
        self.cache_textview_defaults()

    def get_text(self):
        return self.native.getText()

    def set_text(self, value):
        self.native.setText(value)

    @property
    def _wraps(self):
        return self.interface.style.white_space in {NORMAL, PRE_WRAP}

    def rehint(self):
        if self._wraps:
            # When wrapping, the minimum width is the widest unbreakable token. Android
            # can't break within a word, so measure each whitespace-delimited token with
            # the TextView's own paint and take the widest. (A bounded AT_MOST measure
            # can't be used for this: AOSP clamps a 0-width AT_MOST spec to 0, not to
            # the longest word.) The real height is recomputed for the assigned width
            # via measure_text_height().
            paint = self.native.getPaint()
            words = str(self.interface.text).split()
            min_width = max((paint.measureText(word) for word in words), default=0)
            self.interface.intrinsic.width = self.scale_out(
                at_least(ceil(min_width)), ROUND_UP
            )
            # Fallback single-line height, used only if no width is ever assigned.
            self.native.measure(
                View.MeasureSpec.UNSPECIFIED, View.MeasureSpec.UNSPECIFIED
            )
            self.interface.intrinsic.height = self.scale_out(
                self.native.getMeasuredHeight(), ROUND_UP
            )
            return

        # Ask the Android TextView first for its minimum possible height.
        # This is the height with word-wrapping disabled.
        self.native.measure(View.MeasureSpec.UNSPECIFIED, View.MeasureSpec.UNSPECIFIED)
        min_height = self.native.getMeasuredHeight()
        self.interface.intrinsic.height = self.scale_out(min_height, ROUND_UP)
        # Ask it how wide it would be if it had to be the minimum height.
        self.native.measure(
            View.MeasureSpec.UNSPECIFIED,
            View.MeasureSpec.makeMeasureSpec(min_height, View.MeasureSpec.AT_MOST),
        )
        self.interface.intrinsic.width = self.scale_out(
            at_least(self.native.getMeasuredWidth()), ROUND_UP
        )

    def measure_text_width(self):
        # Max-content (single-line) width: measure with an unbounded width spec.
        if not self._wraps:
            return None
        self.native.measure(View.MeasureSpec.UNSPECIFIED, View.MeasureSpec.UNSPECIFIED)
        return self.scale_out(self.native.getMeasuredWidth(), ROUND_UP)

    def measure_text_height(self, width):
        # Height-for-width: measure the wrapped height of the text within the assigned
        # width. The TextView wraps multi-line by default, so a bounded width spec is
        # all that's needed.
        if not self._wraps:
            return None
        native_width = self.scale_in(width)
        self.native.measure(
            View.MeasureSpec.makeMeasureSpec(native_width, View.MeasureSpec.AT_MOST),
            View.MeasureSpec.UNSPECIFIED,
        )
        return self.scale_out(self.native.getMeasuredHeight(), ROUND_UP)

    def set_text_align(self, value):
        self.set_textview_alignment(value, Gravity.TOP)
