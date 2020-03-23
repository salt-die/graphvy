from kivy.animation import Animation
from kivy.lang import Builder
from kivy.uix.floatlayout import FloatLayout
from kivy.properties import NumericProperty, StringProperty

from kivymd.app import MDApp
from kivymd.uix.behaviors import BackgroundColorBehavior
from kivymd.uix.tab import MDTabsBase

from graph_canvas import GraphCanvas
from constants import *


KV = '''
#:import TOOL_ICONS constants.TOOL_ICONS
#:import TOOLS constants.TOOLS
#:import PANEL_WIDTH constants.PANEL_WIDTH

FloatLayout:
    GraphCanvas:
        id: graph_canvas
        adjacency_list: adjacency_list

    MDFloatingActionButton:
        id: panel_button
        icon:'forwardburger'
        md_bg_color: app.theme_cls.primary_color
        on_press: app.animate_panel()
        x: dp(20)
        y: dp(20)

    MDFloatingActionButtonSpeedDial:
        id: tool_select
        data: dict(zip(TOOL_ICONS,TOOLS))
        hint_animation: True
        icon: 'toolbox-outline'
        callback: app.select_tool

    BoxLayout:
        size_hint: PANEL_WIDTH, 1
        size_hint_max_x: 400
        pos_hint: {'x': app._anim_progress, 'y': 0}
        orientation: "vertical"

        MDToolbar:
            id: header
            title: "Graphvy"
            right_action_items: [['play-circle-outline', lambda _: graph_canvas.pause_callback()],\
                                 ['play-box-outline', lambda _: graph_canvas.pause_layout()],\
                                 ['backburger', lambda _: app.animate_panel(-PANEL_WIDTH)]]

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


class PanelTabBase(FloatLayout, MDTabsBase, BackgroundColorBehavior):
    title = StringProperty('')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, md_bg_color=TAB_BACKGROUND, **kwargs)


class Graphvy(MDApp):
    _anim_progress = NumericProperty(-PANEL_WIDTH)

    def build(self):
        return Builder.load_string(KV)

    def on_start(self):
        for node in self.root.ids.graph_canvas.nodes.values():
            self.root.ids.adjacency_list.add_widget(node.make_list_item())

    def on_tab_switch(self, tabs, tab, label, text):
        self.root.ids.header.title = tab.title

    def animate_panel(self, x=0):
        if x == 0:
            self.root.ids.header.title = 'Graphvy'
        Animation(_anim_progress=x, duration=.7, t='out_cubic').start(self)

    def select_tool(self, instance):
        self.root.ids.graph_canvas.tool = self.root.ids.tool_select.data[instance.icon]


Graphvy().run()