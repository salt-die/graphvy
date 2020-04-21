from kivy.properties import ObjectProperty, StringProperty
from kivy.uix.behaviors import ToggleButtonBehavior
from kivy.uix.modalview import ModalView

from kivymd.uix.behaviors import BackgroundColorBehavior, HoverBehavior
from kivymd.uix.button import MDFloatingActionButton, MDIconButton, MDRectangleFlatIconButton
from kivymd.uix.list import OneLineListItem
from kivymd.uix.menu import MDDropdownMenu
from kivymd.uix.tooltip import MDTooltip

from ..constants import HIGHLIGHTED_NODE, NODE_COLOR, SELECTED_COLOR


class AdjacencyListItem(OneLineListItem, BackgroundColorBehavior, HoverBehavior):
    __slots__ = 'node'

    def __init__(self, node, *args, **kwargs):
        self.node = node

        super().__init__(*args,
                         md_bg_color=SELECTED_COLOR,
                         theme_text_color='Custom',
                         text_color=NODE_COLOR, **kwargs)
        self.update_text()

        self.bind(on_release=self._on_release)

    def on_enter(self, *args):
        adjacency_list = self.node.canvas.adjacency_list
        if not adjacency_list.is_hidden and adjacency_list.is_selected:
            self.node.canvas.highlighted = self.node

    def on_leave(self, *args):
        pass

    def _on_release(self, *args):
        self.node.canvas.touch_down_dict[self.node.canvas.tool]()

    def update_text(self):
        self.text = f'{self.node.vertex}: {", ".join(map(str, self.node.vertex.out_neighbors()))}'


class ToolIcon(MDIconButton, ToggleButtonBehavior, MDTooltip):
    label = StringProperty()
    app = ObjectProperty()

    def on_enter(self, *args):
        if self.app.is_file_selecting:  # Prevents tooltips from covering files in the filechooser.
            return
        super().on_enter(*args)

    def on_state(self, instance, value):
        self.text_color = HIGHLIGHTED_NODE if value == 'down' else NODE_COLOR


class MenuItemHoverBehavior(HoverBehavior):
    def on_enter(self, *args):
        self.md_bg_color = HIGHLIGHTED_NODE


class MenuItem(MDRectangleFlatIconButton, MenuItemHoverBehavior):
    def on_leave(self, *args):
        self.md_bg_color = SELECTED_COLOR


class HoverListItem(OneLineListItem, MenuItemHoverBehavior, BackgroundColorBehavior):
    def on_leave(self, *args):
        self.md_bg_color = 0, 0, 0, 0

    def on_touch_up(self, touch):  # We dispatch 'on_release' even if the touch didn't start on item.
        self.last_touch = touch
        self._do_release()

        if self.collide_point(*touch.pos):
            self.dispatch('on_release')
            return True
        return


class BurgerButton(MDFloatingActionButton, MenuItemHoverBehavior):
    def on_leave(self, *args):
        self.md_bg_color = NODE_COLOR


class RandomGraphDialogue(ModalView, BackgroundColorBehavior):
    graph_canvas = ObjectProperty()

    def new_random_graph(self, nodes, edges):
        if nodes.text.isnumeric() and edges.text.isnumeric():
            self.graph_canvas.load_graph(random=(int(nodes.text), int(edges.text)))
            self.dismiss()
        else:
            nodes.error = not nodes.text.isnumeric()
            edges.error = not edges.text.isnumeric()

    def check_if_digit(self, widget):
        if widget.text:
            widget.error = not widget.text[-1].isdigit()
            if widget.error:
                widget.text = widget.text[:-1]


class ColoredMenu(MDDropdownMenu):
    """Displays properties we can use to color nodes or edges."""

    def create_menu_items(self):
        self.menu.ids.box.clear_widgets()

        for data in self.items:
            item = HoverListItem(text=data.get("text", ""), theme_text_color='Custom', text_color=NODE_COLOR)
            if self.callback:
                item.bind(on_release=self.callback)
            self.menu.ids.box.add_widget(item)