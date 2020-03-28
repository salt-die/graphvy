"""
Modified MDFileManager from https://github.com/HeaTTheatR/KivyMD/blob/master/kivymd/uix/filemanager.py.

Modifications to allow preferred colors and sizing.  Slightly different if loading or saving.
"""
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

<BodyManager@BoxLayout>
    icon: 'folder'
    path: ''
    background_normal: ''
    background_down: ''
    dir_or_file_name: ''
    events_callback: lambda x: None
    orientation: 'vertical'

    ModifiedOneLineIconListItem:
        text: root.dir_or_file_name
        on_release: root.events_callback(root.path)

        IconLeftWidget:
            icon: root.icon
            theme_text_color: "Custom"
            text_color: NODE_COLOR

    MDSeparator

<FileChooser>
    id: fm
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
                left_action_items: [['chevron-left', lambda x: root.back()]]

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
                    on_text_validate: fm.select_file()
                    color_mode: 'custom'
                    line_color_focus: HIGHLIGHTED_NODE
                    hint_text: 'File name:'
                    write_tab: False
                    helper_text: "File doesn't exist"
                    helper_text_mode: 'on_error'
                    on_text: fm.reset_error()
                    on_focus: fm.reset_error()

                MDRaisedButton:
                    id: accept
                    text: 'Load'
                    width: dp(120)
                    pos_hint: {'center_y': .5}
                    md_bg_color: HIGHLIGHTED_NODE
                    text_color: NODE_COLOR
                    on_release: fm.select_file()

                MDFlatButton:
                    text: 'Cancel'
                    width: dp(120)
                    pos_hint: {'center_y': .5}
                    md_bg_color: SELECTED_COLOR
                    text_color: NODE_COLOR
                    on_release: fm.exit_chooser(1)

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
    icon = StringProperty("check")
    exit_chooser = ObjectProperty(lambda x: None)
    select_path = ObjectProperty(lambda *args: None)
    ext = ListProperty()
    search = OptionProperty('all', options=['all', 'files', 'dirs'])
    current_path = StringProperty(os.getcwd())
    use_access = BooleanProperty(True)
    is_open = False

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.history = []  # directory navigation history
        # If False - do not add a directory to the history -
        # The user moves down the tree.
        self.history_flag = True
        toolbar_label = self.ids.toolbar.children[1].children[0]
        toolbar_label.font_style = 'Subtitle1'

    def dismiss(self, *args, **kwargs):
        self.is_open = False
        self.ids.file_name.text = ''
        super().dismiss(*args, **kwargs)

    def show(self, path=None, saving=None, ext=None):
        """Forms the body of a directory tree.
        :param path: The path to the directory that will be opened in the file manager.
        """
        if path is None:
            path = os.getcwd()

        if saving is not None:
            self.ids.accept.text = 'Save' if saving else 'Load'

        if ext is not None:
            self.ext = ext

        dirs, files = self.get_content(path)

        self.current_path = path
        manager_list = []

        if dirs == [] and files == []:  # selected directory
            pass
        elif not dirs and not files:  # directory is unavailable
            return

        is_dir = True
        for name in chain(dirs, (None,), files):
            if name is None:
                is_dir = False
                continue

            _path = path + name if path == '/' else f'{path}/{name}'

            if is_dir:
                access_string = self.get_access_string(_path)
                icon = 'folder-lock' if 'r' not in access_string else 'folder'
            else:
                icon = 'file-outline'

            manager_list.append({'viewclass': 'BodyManager',
                                 'path': _path,
                                 'icon': icon,
                                 'dir_or_file_name': name,
                                 'events_callback': self.select_dir_or_file})

        self.ids.rv.data = manager_list
        if not self.is_open:
            self.is_open = True
            self.open()
            def focus(dt):
                self.ids.file_name.focus = True
            Clock.schedule_once(focus, 0)  # The focus animation will get interrupted if we don't schedule it.

    def count_ext(self, path):
        ext = os.path.splitext(path)[1]
        return ext and (ext.lower() in self.ext or ext.upper() in self.ext)

    def get_access_string(self, path):
        if self.use_access:
            access_data = {'r': os.R_OK, 'w': os.W_OK, 'x': os.X_OK}
            return ''.join(key if os.access(path, value) else '-' for key, value in access_data.items())
        return ''

    def get_content(self, path):
        """Returns a list of the type [[Folder List], [file list]]."""

        try:
            files = []
            dirs = []

            if self.history_flag:
                self.history.append(path)
            else:
                self.history_flag = True

            for content in os.listdir(path):
                if os.path.isdir(os.path.join(path, content)):
                    if self.search in ('all', 'dirs'):
                        dirs.append(content)
                else:
                    if self.search in ('all', 'files'):
                        if self.ext:
                            try:
                                if self.count_ext(content):
                                    files.append(content)
                            except IndexError:
                                pass
                        else:
                            files.append(content)
            return dirs, files
        except OSError:
            self.history.pop()
            return None, None

    def select_dir_or_file(self, path):
        """Called by tap on the name of the directory or file."""
        if os.path.isfile(path):
            self.current_path, self.ids.file_name.text = os.path.split(path)
            self.ids.file_name.focus = True
        else:
            self.current_path = path
        self.show(self.current_path)

    def back(self):
        """Returning to the branch down in the directory tree."""

        if len(self.history) == 1:
            path, end = os.path.split(self.history[0])
            if end == "":
                self.dismiss()
                self.exit_chooser(1)
                return
            self.history[0] = path
        else:
            self.history.pop()
            path = self.history[-1]
        self.history_flag = False
        self.select_dir_or_file(path)

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