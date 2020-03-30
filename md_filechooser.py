"""
Modified MDFileManager from https://github.com/HeaTTheatR/KivyMD/blob/master/kivymd/uix/filemanager.py.

Modifications to allow preferred colors and sizing.  Slightly different if loading or saving.
"""
from collections import ChainMap
from itertools import chain
import os

from kivy.clock import Clock
from kivy.metrics import dp
from kivy.lang import Builder
from kivy.properties import (BooleanProperty,
                             ListProperty,
                             ObjectProperty,
                             OptionProperty,
                             StringProperty)
from kivy.uix.modalview import ModalView
from kivymd.uix.behaviors import BackgroundColorBehavior

KV = """
#: import SELECTED_COLOR constants.SELECTED_COLOR
#: import NODE_COLOR constants.NODE_COLOR

<FileChooser>
    id: fc
    auto_dismiss: False
    pos_hint: {'center_x':.5, 'center_y':.5}
    md_bg_color: SELECTED_COLOR

    RelativeLayout:

        BoxLayout:
            orientation: 'vertical'
            spacing: dp(5)

            MDToolbar:
                id: toolbar
                md_bg_color: NODE_COLOR
                specific_text_color: HIGHLIGHTED_NODE
                title: root.current_path
                right_action_items: [['close-box', lambda x: root.exit_chooser(1)]]
                left_action_items: [['chevron-up', lambda x: root.up()]]

            RecycleView:
                id: rv
                key_viewclass: 'viewclass'
                key_size: 'height'
                bar_width: dp(4)
                bar_color: NODE_COLOR
                RecycleBoxLayout:
                    padding: dp(10)
                    default_size: None, dp(48)
                    default_size_hint: 1, None
                    size_hint_y: None
                    height: self.minimum_height
                    orientation: 'vertical'

            BoxBG:
                spacing: dp(5)
                padding: dp(5)
                size_hint: 1, .3
                size_hint_max_y: dp(60)

                MDTextField:
                    id: file_name
                    on_text_validate: fc.select_file()
                    color_mode: 'custom'
                    line_color_focus: HIGHLIGHTED_NODE
                    hint_text: 'File name:'
                    write_tab: False
                    helper_text: "File doesn't exist"
                    helper_text_mode: 'on_error'
                    on_text: fc.reset_error()
                    on_focus: fc.reset_error()

                MDRaisedButton:
                    id: accept
                    text: 'Load'
                    width: dp(120)
                    pos_hint: {'center_y': .5}
                    md_bg_color: HIGHLIGHTED_NODE
                    text_color: NODE_COLOR
                    on_release: fc.select_file()

                MDFlatButton:
                    text: 'Cancel'
                    width: dp(120)
                    pos_hint: {'center_y': .5}
                    md_bg_color: SELECTED_COLOR
                    text_color: NODE_COLOR
                    on_release: fc.exit_chooser(1)

<DirContents@BoxLayout>
    icon: ''
    select: lambda *args: None
    name: ''
    orientation: 'vertical'

    ModifiedOneLineIconListItem:
        text: root.name
        on_release: root.select(root.name, from_name=True)

        IconLeftWidget:
            icon: root.icon
            theme_text_color: "Custom"
            text_color: NODE_COLOR

    MDSeparator

<BoxBG@BoxLayout+BackgroundColorBehavior>
    md_bg_color: NODE_COLOR

<ModifiedOneLineIconListItem@ContainerSupport+BaseListItem>
    _txt_left_pad: dp(72)
    _txt_top_pad: dp(16)
    _txt_bot_pad: dp(15)
    _num_lines: 1
    theme_text_color: 'Custom'
    text_color: NODE_COLOR
    height: dp(48)

    BoxLayout:
        id: _left_container
        size_hint: None, None
        x: root.x + dp(16)
        y: root.y + root.height / 2 - self.height / 2
        size: dp(48), dp(48)
"""


class FileChooser(BackgroundColorBehavior, ModalView):
    exit_chooser = ObjectProperty(lambda x: None)
    select_path = ObjectProperty(lambda *args: None)
    ext = ListProperty()
    search = OptionProperty('all', options=['all', 'files', 'dirs'])
    current_path = StringProperty(os.getcwd())
    use_access = BooleanProperty(True)
    is_open = False

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        toolbar_label = self.ids.toolbar.children[1].children[0]
        toolbar_label.font_style = 'Subtitle1'

    def dismiss(self, *args, **kwargs):
        self.is_open = False
        self.ids.file_name.text = ''
        super().dismiss(*args, **kwargs)

    def show(self, path=None, save=None, ext=None):
        """Forms the body of a directory tree.
        :param path: The path to the directory that will be opened in the file manager.
        """
        if path is None:
            path = os.getcwd()

        if save is not None:
            self.ids.accept.text = 'Save' if save else 'Load'

        if ext is not None:
            self.ext = ext

        dirs, files = self.get_content(path)
        if dirs is None and files is None:  # directory is unavailable
            return

        self.current_path = path
        manager_list = []

        default = {'viewclass': 'DirContents', 'select': self.select_dir_or_file}
        self.ids.rv.data = [ChainMap({'name': name, 'icon': icon}, default) for name, icon in chain(dirs, files)]

        if not self.is_open:
            self.is_open = True
            self.open()
            def focus(dt):
                self.ids.file_name.focus = True
            Clock.schedule_once(focus, 0)  # The focus animation will get interrupted if we don't schedule it.

    def count_ext(self, path):
        _, ext = os.path.splitext(path)
        return ext and (ext.lower() in self.ext or ext.upper() in self.ext)

    def get_access_string(self, path):
        if self.use_access:
            access_data = {'r': os.R_OK, 'w': os.W_OK, 'x': os.X_OK}
            return ''.join(key for key, value in access_data.items() if os.access(path, value))
        return ''

    def get_content(self, path):
        """Returns two lists of tuples -- [[(dir, icon), ...], [(file, icon), ...]]"""

        try:
            dirs = []
            files = []

            for content in os.listdir(path):
                if content.startswith('.'):  # Skip hidden content
                    continue

                if os.path.isdir(os.path.join(path, content)):
                    if self.search != 'files':
                        access_string = self.get_access_string(os.path.join(path, content))
                        icon = 'folder-lock' if 'r' not in access_string else 'folder'
                        dirs.append((content, icon))
                elif self.search != 'dirs':
                    if not self.ext or self.count_ext(content):
                        files.append((content, 'file-outline'))

            return sorted(dirs), sorted(files)
        except OSError:
            return None, None

    def select_dir_or_file(self, path, from_name=False):
        """Called by tap on the name of the directory or file."""
        if from_name:
            path = f'/{path}' if self.current_path == '/' else f'{self.current_path}/{path}'

        if os.path.isfile(path):
            self.current_path, self.ids.file_name.text = os.path.split(path)
            self.ids.file_name.focus = True
        else:
            self.current_path = path

        self.show(self.current_path)

    def up(self):
        """Go up a level in the directory tree."""
        self.select_dir_or_file(os.path.abspath(os.path.join(self.current_path, os.path.pardir)))

    def select_file(self, *args):
        is_save = self.ids.accept.text == 'Save'
        file = os.path.join(self.current_path, self.ids.file_name.text)
        if not is_save and not os.path.isfile(file):
            self.ids.file_name.error = True
            self.ids.file_name.focus = True
            return
        self.select_path(file, is_save)
        self.dismiss()

    def reset_error(self):
        self.ids.file_name.error = False


Builder.load_string(KV)