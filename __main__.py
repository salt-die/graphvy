from kivy.animation import Animation
from kivy.lang import Builder
from kivy.uix.behaviors import ToggleButtonBehavior
from kivy.uix.floatlayout import FloatLayout
from kivy.properties import BooleanProperty, NumericProperty, StringProperty, ListProperty

from kivymd.app import MDApp
from kivymd.uix.button import MDIconButton, MDRectangleFlatIconButton, MDFloatingActionButton
from kivymd.uix.behaviors import BackgroundColorBehavior, HoverBehavior
from kivymd.uix.list import MDList
from kivymd.uix.tab import MDTabsBase
from kivymd.uix.tooltip import MDTooltip

from graph_canvas import GraphCanvas
from constants import *


KV = '''
#:import PANEL_WIDTH constants.PANEL_WIDTH
#:import NODE_COLOR constants.NODE_COLOR
#:import HIGHLIGHTED_NODE constants.HIGHLIGHTED_NODE
#:import SELECTED_COLOR constants.SELECTED_COLOR

FloatLayout:
    GraphCanvas:
        id: graph_canvas
        adjacency_list: adjacency_list

    BurgerButton:
        icon:'forwardburger'
        text_theme_color: 'Custom'
        text_color: 0, 0, 0, 1
        md_bg_color: NODE_COLOR
        on_release: app.animate_panel()
        x: dp(10) - side_panel.width/root.width - side_panel.right
        y: dp(20)

    BoxLayout:
        id: side_panel
        size_hint: PANEL_WIDTH, 1
        size_hint_min_x: 100
        size_hint_max_x: 300
        pos_hint: {'x': app._anim_progress, 'y': 0}
        orientation: 'vertical'

        MDToolbar:
            id: header
            title: 'Graphvy'
            md_bg_color: NODE_COLOR
            specific_text_color: HIGHLIGHTED_NODE

        MDTabs:
            id: tabs
            on_tab_switch: app.on_tab_switch(*args)
            background_color: NODE_COLOR
            color_indicator: HIGHLIGHTED_NODE

            PanelTabBase:
                title: 'File'
                text: 'file-outline'

                MenuItem:
                    icon: 'eraser'
                    text: 'New graph'
                    top: self.parent.top
                    on_release: app.reset()

                MenuItem:
                    icon: 'graph-outline'
                    text: 'Load graph...'
                    top: self.parent.top - self.height
                    on_release: app.load_graph()

                MenuItem:
                    icon: 'floppy'
                    text: 'Save graph...'
                    top: self.parent.top - self.height * 2
                    on_release: app.save_graph()

                MenuItem:
                    icon: 'language-python'
                    text: 'Load rule...'
                    top: self.parent.top - self.height * 3
                    on_release: app.load_rule()

            PanelTabBase:
                title: 'Adjacency List'
                text: 'ray-start-arrow'

                ScrollView:
                    HideableList:
                        id: adjacency_list
                        is_hidden: True

            PanelTabBase:
                title: 'Filters'
                text: 'filter-outline'

        MDToolbar:
            md_bg_color: NODE_COLOR
            specific_text_color: HIGHLIGHTED_NODE
            left_action_items: [['play-circle-outline', lambda _: graph_canvas.pause_callback()],\
                                ['play-box-outline', lambda _: graph_canvas.pause_layout()]]
            right_action_items: [['backburger', lambda _: app.animate_panel(-side_panel.width/root.width)]]

    BoxLayout:
        orientation: 'vertical'
        x: dp(10) + dp(4) + side_panel.right
        y: dp(96)
        size: self.minimum_size
        spacing: dp(10)

        ToolIcon:
            id: grab
            icon: 'drag-variant'
            label: 'Grab'

        ToolIcon:
            icon: 'selection-drag'
            label: 'Select'

        ToolIcon:
            icon: 'pin'
            label: 'Pin'

        ToolIcon:
            icon: 'map-marker-path'
            label: 'Show Path'

        ToolIcon:
            icon: 'plus-circle-outline'
            label: 'Add Node'

        ToolIcon:
            icon: 'minus-circle-outline'
            label: 'Delete Node'

        ToolIcon:
            icon: 'vector-polyline-plus'
            label: 'Add Edge'

        ToolIcon:
            icon: 'vector-polyline-minus'
            label: 'Delete Edge'

<ToolIcon>:
    group: 'tools'
    allow_no_selection: False
    tooltip_text: self.label
    tooltip_text_color: NODE_COLOR
    tooltip_bg_color: SELECTED_COLOR
    theme_text_color: 'Custom'
    text_color: NODE_COLOR
    on_press: app.select_tool(self.label)

<PanelTabBase>:
    md_bg_color: SELECTED_COLOR

<MenuItem>:
    width: self.parent.width
    theme_text_color: 'Custom'
    text_color: NODE_COLOR
'''


class HideableList(MDList):
    """List items with hover behavior are properly disabled when list is hidden."""
    is_hidden = BooleanProperty(True)


class ToolIcon(MDIconButton, ToggleButtonBehavior, MDTooltip):
    label = StringProperty()

    def on_state(self, instance, value):
        self.text_color = HIGHLIGHTED_NODE if value == 'down' else NODE_COLOR


class PanelTabBase(FloatLayout, MDTabsBase, BackgroundColorBehavior):
    title = StringProperty()


class MenuItem(MDRectangleFlatIconButton, HoverBehavior):
    def on_enter(self, *args):
        self.md_bg_color = HIGHLIGHTED_NODE

    def on_leave(self, *args):
        self.md_bg_color = self.parent.md_bg_color


class BurgerButton(MDFloatingActionButton, HoverBehavior):
    def on_enter(self, *args):
        self.md_bg_color = HIGHLIGHTED_NODE

    def on_leave(self, *args):
        self.md_bg_color = NODE_COLOR


class Graphvy(MDApp):
    _anim_progress = NumericProperty(-PANEL_WIDTH)

    def build(self):
        return Builder.load_string(KV)

    def on_start(self):
        for node in self.root.ids.graph_canvas.nodes.values():
            self.root.ids.adjacency_list.add_widget(node.make_list_item())
        self.root.ids.grab.state = 'down'

        # Setting the text_color_active/_normal properties in kv lang appears to be bugged
        for child in self.root.ids.tabs.tab_bar.layout.children:
            child.text_color_active = HIGHLIGHTED_NODE
            child.text_color_normal = SELECTED_COLOR

        self.root.bind(width=self._resize)

    def on_tab_switch(self, tabs, tab, label, text):
        self.root.ids.header.title = tab.title

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
            self.root.canvas.ask_update()

    def select_tool(self, tool):
        self.root.ids.graph_canvas.tool = tool

    def reset(self):
        print('reset')

    def load_graph(self):
        print('load graph')

    def save_graph(self):
        print('save graph')

    def load_rule(self):
        print('load rule')


Graphvy().run()