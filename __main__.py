from kivy.animation import Animation
from kivy.lang import Builder
from kivy.uix.floatlayout import FloatLayout
from kivy.properties import NumericProperty, StringProperty

from kivymd.app import MDApp
from kivymd.uix.behaviors import BackgroundColorBehavior
from kivymd.uix.button import MDFloatingActionButton, MDFloatingActionButtonSpeedDial
from kivymd.uix.list import OneLineListItem
from kivymd.uix.tab import MDTabsBase

from graph_canvas import GraphCanvas


KV = '''
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
        data: {'drag-variant'         : 'Grab',       \
               'selection-drag'       : 'Select',     \
               'pin'                  : 'Pin',        \
               'map-marker-path'      : 'Show Path',  \
               'plus-circle-outline'  : 'Add Node',   \
               'minus-circle-outline' : 'Delete Node',\
               'vector-polyline-plus' : 'Add Edge',   \
               'vector-polyline-minus': 'Delete Edge'}
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
                md_bg_color: 1, 1, 1, 1

            PanelTabBase:
                title: 'Adjacency List'
                text: 'ray-start-arrow'
                md_bg_color: 1, 1, 1, 1

                ScrollView:
                    MDList:
                        id: adjacency_list

            PanelTabBase:
                title: 'Filters'
                text: 'filter-outline'
                md_bg_color: 1, 1, 1, 1

'''


class PanelButton(MDFloatingActionButton):
    callback = None

    def on_touch_up(self, touch):
        if super().on_touch_up(touch):
            self.callback()
            return True


class PanelTabBase(FloatLayout, MDTabsBase, BackgroundColorBehavior):
    title = StringProperty('')


class Graphvy(MDApp):
    _anim_progress = NumericProperty(0)

    def build(self):
        root = Builder.load_string(KV)
        root.ids.panel_button.callback = self.show_panel
        return root

    def on_start(self):
        for i in range(20):
            # This is just a visual test
            self.root.ids.adjacency_list.add_widget(OneLineListItem(text=f'{i}: {i + 1}, {i + 2}'))
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
        print(instance.icon)


Graphvy().run()