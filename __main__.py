from kivy.animation import Animation
from kivy.lang import Builder
from kivy.uix.floatlayout import FloatLayout
from kivy.properties import NumericProperty, StringProperty

from kivymd.app import MDApp
from kivymd.uix.behaviors import BackgroundColorBehavior
from kivymd.uix.button import MDFloatingActionButton, MDFloatingActionButtonSpeedDial
from kivymd.uix.tab import MDTabsBase

from graph_canvas import GraphCanvas
from constants import *


KV = '''
#:import TOOL_ICONS constants.TOOL_ICONS
#:import TOOLS constants.TOOLS

FloatLayout:
    GraphCanvas:
        id: graph_canvas

    PanelButton:
        id: panel_button
        icon:'forwardburger'
        md_bg_color: app.theme_cls.primary_color
        x: dp(20)
        y: dp(20)

    MDFloatingActionButtonSpeedDial:
        id: tool_select
        data: dict(zip(TOOL_ICONS,TOOLS))
        hint_animation: True
        icon: 'toolbox-outline'
        callback: app.select_tool

    BoxLayout:
        size_hint: .3, 1
        pos_hint: {'x': app._anim_progress, 'y': 0}
        orientation: "vertical"

        MDToolbar:
            id: header
            title: "Graphvy"
            right_action_items: [['backburger', lambda _: app.hide_panel()]]

        MDTabs:
            id: side_panel
            on_tab_switch: app.on_tab_switch(*args)

            PanelTabBase:
                title: 'File'
                text: 'file-outline'

            PanelTabBase:
                title: 'Adjacency List'
                text: 'ray-start-arrow'

                ScrollView:
                    MDList:
                        id: adjacency_list

            PanelTabBase:
                title: 'Filters'
                text: 'filter-outline'

'''


class PanelButton(MDFloatingActionButton):
    callback = None

    def on_touch_up(self, touch):
        if super().on_touch_up(touch):
            self.callback()
            return True


class PanelTabBase(FloatLayout, MDTabsBase, BackgroundColorBehavior):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, md_bg_color=TAB_BACKGROUND, **kwargs)
    title = StringProperty('')


class Graphvy(MDApp):
    _anim_progress = NumericProperty(0)

    def build(self):
        root = Builder.load_string(KV)
        root.ids.panel_button.callback = self.show_panel
        return root

    def on_start(self):
        gc = self.root.ids.graph_canvas
        adjacency_list = self.root.ids.adjacency_list

        for node in gc.nodes.values():
            adjacency_list.add_widget(node.make_list_item())
        self.hide_panel()

    def on_tab_switch(self, tabs, tab, label, text):
        self.root.ids.header.title = tab.title

    def hide_panel(self):
        anim = Animation(_anim_progress=-.3, duration=.7, t='out_cubic')
        anim.start(self)

    def show_panel(self):
        self.root.ids.header.title = 'Graphvy'
        anim = Animation(_anim_progress=0, duration=.7, t='out_cubic')
        anim.start(self)

    def select_tool(self, instance):
        self.root.ids.graph_canvas.tool = self.root.ids.tool_select.data[instance.icon]

    def highlight_node(self, node):
        canvas = self.root.ids.graph_canvas
        vertex = canvas.G.vertex(node)
        G.highlighted = G.nodes[vertex]


Graphvy().run()