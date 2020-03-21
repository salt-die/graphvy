from kivy.animation import Animation
from kivy.lang import Builder
from kivy.uix.floatlayout import FloatLayout
from kivy.properties import NumericProperty, StringProperty

from kivymd.app import MDApp
from kivymd.uix.behaviors import BackgroundColorBehavior
from kivymd.uix.button import MDFloatingActionButton
from kivymd.uix.list import OneLineListItem
from kivymd.uix.tab import MDTabsBase

import graph_tool as gt
from graph_canvas import GraphCanvas


KV = '''
FloatLayout:
    GraphCanvas

    PanelButton:
        id: panel_button
        icon:'forwardburger'
        md_bg_color: app.theme_cls.primary_color
        pos_hint: {'x': .01, 'y': .9}

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


class PanelTabBase(FloatLayout, MDTabsBase, BackgroundColorBehavior):
    title = StringProperty('')


class SidePanel(MDApp):
    _anim_progress = NumericProperty(0)

    def build(self):
        root = Builder.load_string(KV)
        root.ids.panel_button.callback = self.show_panel
        return root

    def on_start(self):
        for i in range(20):
            self.root.ids.adjacency_list.add_widget(OneLineListItem(text=f'{i}: {i + 1}, {i + 2}'))

    def on_tab_switch(self, tabs, tab, label, text):
        self.root.ids.header.title = tab.title

    def hide_panel(self):
        anim = Animation(_anim_progress=-.3, duration=.7, t='out_cubic')
        anim.start(self)

    def show_panel(self):
        self.root.ids.header.title = 'Graphvy'
        anim = Animation(_anim_progress=0, duration=.7, t='out_cubic')
        anim.start(self)


SidePanel().run()