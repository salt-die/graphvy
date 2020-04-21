"""Slightly altered MDDropdownItem for consistent colors."""

from kivy.lang import Builder
from kivy.properties import StringProperty
from kivy.uix.behaviors import ButtonBehavior

from kivymd.uix.behaviors import RectangularRippleBehavior
from kivymd.uix.boxlayout import MDBoxLayout

Builder.load_string("""
#:import NODE_COLOR constants.NODE_COLOR

<_Triangle@Widget>:
    canvas:
        Color:
            rgba: NODE_COLOR
        Triangle:
            points:
                [ \
                self.right-14, self.y+7, \
                self.right-7, self.y+7, \
                self.right-7, self.y+14 \
                ]

<ColoredDropdownItem>
    orientation: "vertical"
    adaptive_size: True
    spacing: "5dp"
    padding: "5dp", "5dp", "5dp", 0

    MDBoxLayout:
        adaptive_size: True
        spacing: "10dp"
        Label:
            id: label_item
            size_hint: None, None
            size: self.texture_size
            color: NODE_COLOR
        _Triangle:
            size_hint: None, None
            size: "20dp", "20dp"
    MDSeparator:
""")


class ColoredDropdownItem(RectangularRippleBehavior, ButtonBehavior, MDBoxLayout):
    text = StringProperty()
    current_item = StringProperty()

    def on_text(self, instance, value):
        self.ids.label_item.text = value

    def set_item(self, name_item):
        self.ids.label_item.text = name_item
        self.current_item = name_item