import os

from kivy.animation import Animation
from kivy.lang import Builder

from kivy.properties import NumericProperty
from kivymd.app import MDApp

from .constants import *

from .graph_canvas.graph_canvas import GraphCanvas
from .ui.colored_drop_down_item import ColoredDropdownItem
from .ui.md_filechooser import FileChooser
from .ui.ui_widgets import ToolIcon, MenuItem, BurgerButton, RandomGraphDialogue, ColoredMenu


class Graphvy(MDApp):
    _anim_progress = NumericProperty(-PANEL_WIDTH)
    is_file_selecting = False

    def on_start(self):
        self.root.ids.grab.state = 'down'

        # Setting the text_color_active/_normal properties in kv lang appears to be bugged
        for child in self.root.ids.tabs.tab_bar.layout.children:
            child.text_color_active = HIGHLIGHTED_NODE
            child.text_color_normal = SELECTED_COLOR

        self.file_chooser = FileChooser(exit_chooser=self.exit_chooser,
                                        select_path=self.select_path,
                                        size_hint=(.8, .8))

        self.prop_menu = ColoredMenu(caller=self.root, position='auto', width_mult=2, background_color=SELECTED_COLOR)

        self.root.bind(width=self._resize)

    def on_tab_switch(self, tabs, tab, label, text):
        self.root.ids.header.title = tab.title
        self.root.ids.adjacency_list.is_selected = tab.title == 'Adjacency List'

    def animate_panel(self, x=0):
        if x == 0:
            self.root.ids.header.title = 'Graphvy'
            self.root.ids.adjacency_list.is_hidden = False
        else:
            self.root.ids.adjacency_list.is_hidden = True
        Animation(_anim_progress=x, duration=.7, t='out_cubic').start(self)

    def _resize(self, *args):
        if self._anim_progress:
            self._anim_progress = -self.root.ids.side_panel.width / self.root.width

    def select_tool(self, tool):
        self.root.ids.graph_canvas.tool = tool

    def erdos_reset(self):
        dialogue = RandomGraphDialogue(graph_canvas=self.root.ids.graph_canvas)
        dialogue.open()

    def exit_chooser(self, *args):
        self.is_file_selecting = False
        self.file_chooser.dismiss()

    def select_path(self, path, is_save):
        self.is_file_selecting = False
        gc = self.root.ids.graph_canvas

        if os.path.splitext(path)[1] == '.py':
            with open(path, 'r') as code:
                code = code.read()

            l = {}
            exec(code, None, l)
            gc.load_rule(l['rule'])
            return

        gc.G.save(path, fmt='gt') if is_save else gc.load_graph(G=path)

    def show_file_chooser(self, dir_, save, ext):
        self.is_file_selecting = True
        self.file_chooser.show(path=os.path.join(os.getcwd(), 'graphvy', dir_), save=save, ext=[ext])

    def open_property_menu(self, instance, nodes=True):
        gc = self.root.ids.graph_canvas

        def callback(instance):
            property_name = instance.text
            if property_name == 'default':
                return gc.set_node_colormap() if nodes else gc.set_edge_colormap()

            if nodes:
                property_map = gc.G.vp[property_name]
                attr = 'node_states'
                set_map = gc.set_node_colormap
            else:
                property_map = gc.G.ep[property_name]
                attr = 'edge_states'
                set_map = gc.set_edge_colormap

            # Check if property states are explicitly set by graph rule; if not, use states min and max values.
            if (gc.rule is not None
                and (states := getattr(gc.rule_callback, attr, None))
                and (n_states := states.get(property_name))):
                set_map(property_map, *n_states)
            else:
                array = property_map.get_array()
                set_map(property_map, array.min(), array.max())

        self.prop_menu.caller = instance
        self.prop_menu.callback = callback

        properties = gc.G.vp if nodes else gc.G.ep
        self.prop_menu.items = [{'text': property_} for property_ in properties if property_ not in ('pos', 'pinned')]

        self.prop_menu.set_menu_properties(1)
        self.prop_menu.open()


Graphvy().run()
