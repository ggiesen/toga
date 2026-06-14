from travertino.constants import NORMAL, PRE_WRAP
from travertino.size import at_least

from ..libs import GTK_VERSION, Gtk, gtk_text_align
from .base import Widget


class Label(Widget):
    def create(self):
        self.native = Gtk.Label()
        if GTK_VERSION < (4, 0, 0):  # pragma: no-cover-if-gtk4
            self.native.set_line_wrap(False)
        else:  # pragma: no-cover-if-gtk3
            self.native.set_wrap(False)

    @property
    def _wraps(self):
        return self.interface.style.white_space in {NORMAL, PRE_WRAP}

    def set_white_space(self, white_space):
        wrap = white_space in {NORMAL, PRE_WRAP}
        if GTK_VERSION < (4, 0, 0):  # pragma: no-cover-if-gtk4
            self.native.set_line_wrap(wrap)
        else:  # pragma: no-cover-if-gtk3
            self.native.set_wrap(wrap)

    def measure_text_width(self):
        # Max-content (single-line) width: the natural width GTK reports for the label
        # (the width it would take if it didn't wrap).
        if not self._wraps:
            return None
        if GTK_VERSION < (4, 0, 0):  # pragma: no-cover-if-gtk4
            _, natural_width = self.native.get_preferred_width()
            return natural_width
        else:  # pragma: no-cover-if-gtk3
            _, natural_size = self.native.get_preferred_size()
            return natural_size.width

    def measure_text_height(self, width):
        # Height-for-width: when wrapping is enabled, report the height GTK needs to lay
        # out the text within the assigned width. Gtk.Label is the canonical
        # HEIGHT_FOR_WIDTH widget, so this is a native query.
        if not self._wraps:
            return None
        width = int(width)
        if GTK_VERSION < (4, 0, 0):  # pragma: no-cover-if-gtk4
            _, natural_height = self.native.get_preferred_height_for_width(width)
            return natural_height
        else:  # pragma: no-cover-if-gtk3
            _, natural, _, _ = self.native.measure(Gtk.Orientation.VERTICAL, width)
            return natural

    def set_text_align(self, value):
        xalign, justify = gtk_text_align(value)
        self.native.set_xalign(xalign)  # Aligns the whole text block within the widget.
        self.native.set_yalign(0.0)  # Aligns the text block to the top
        self.native.set_justify(
            justify
        )  # Aligns multiple lines relative to each other.

    def get_text(self):
        return self.native.get_text()

    def set_text(self, value):
        self.native.set_text(value)

    def rehint(self):
        if GTK_VERSION < (4, 0, 0):  # pragma: no-cover-if-gtk4
            # print(
            #     "REHINT",
            #     self,
            #     self.native.get_preferred_width(),
            #     self.native.get_preferred_height(),
            #     getattr(self, "_fixed_height", False),
            #     getattr(self, "_fixed_width", False),
            # )
            width = self.native.get_preferred_width()
            height = self.native.get_preferred_height()

            self.interface.intrinsic.width = at_least(width[0])
            self.interface.intrinsic.height = height[1]
        else:  # pragma: no-cover-if-gtk3
            # print(
            #     "REHINT",
            #     self,
            #     self.native.get_preferred_size()[0].width,
            #     self.native.get_preferred_size()[0].height,
            # )
            min_size, size = self.native.get_preferred_size()

            self.interface.intrinsic.width = at_least(min_size.width)
            self.interface.intrinsic.height = size.height
