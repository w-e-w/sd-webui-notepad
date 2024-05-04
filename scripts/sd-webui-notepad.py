from modules import scripts, ui_common, errors
from pathlib import Path
import gradio as gr
import datetime

title = 'Notepad'
script_base_dir = Path(scripts.basedir())
notepad_path = script_base_dir / 'notepads'
new_entry = 'New Notepad'


character_translation_table = str.maketrans('"*/:<>?\\|\t\n\v\f\r', '＂＊／：＜＞？＼￨     ')


def sanitize(input_str):
    return Path(input_str).name.translate(character_translation_table).strip()


class NotepadUser:
    max_history = 5
    default_username = 'local'

    def __init__(self, request: gr.Request):
        self.user = sanitize(self.default_username if request.username is None else request.username)
        self.notepad_dir = script_base_dir / 'notepads' / self.user
        self.notepads = None

    def refresh_notepad(self, notepad_name):
        # get notepad version
        return [n.stem[1:] for n in sorted((self.notepad_dir / notepad_name).glob('.*.txt'), reverse=True)]

    def refresh_notepads(self):
        # get all notepad version
        if self.notepads is None:
            self.notepads = {}
            for n in sorted(list(self.notepad_dir.glob('*/*.txt')), key=lambda x: x.stem, reverse=True):
                if (name := n.parent.stem) in self.notepads:
                    self.notepads[name].append(n.stem[1:])
                else:
                    self.notepads[name] = [n.stem[1:]]

    def get_notepad_path(self, notepad_name, version=None):
        if version is None or not (version := sanitize(version)):
            version = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')

        if new_entry == (notepad_name := sanitize(notepad_name)):
            notepad_name = ''

        if not notepad_name:
            notepad_name = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')

        return self.notepad_dir / notepad_name / f'.{version}.txt'

    def read_notepad(self, notepad_name, version):
        with open(self.get_notepad_path(notepad_name, version), encoding='utf-8') as f:
            return f.read()

    def write_notepad(self, notepad_name, text):
        notepad_versions = self.refresh_notepad(notepad_name)
        current_notepad = self.read_notepad(notepad_name, notepad_versions[0]) if notepad_versions else ''
        if text != current_notepad:
            new_notepad_path = self.get_notepad_path(notepad_name)
            new_notepad_path.parent.mkdir(parents=True, exist_ok=True)
            with open(new_notepad_path, 'w', encoding='utf-8') as f:
                f.write(text)

            if len(notepad_versions) >= self.max_history:
                print(f'remove history {self.get_notepad_path(notepad_name, notepad_versions[-1])}')
                self.get_notepad_path(notepad_name, notepad_versions[-1]).unlink()

            self.refresh_notepads()
            for k, v in self.notepads.items():
                return (
                    gr.update(value=k, choices=[new_entry] + list(self.notepads)),
                    gr.update(value=v[0], choices=v),
                )
        return gr.update(), gr.update()

    def rename_notepad(self, notepad_name, new_notepad_name):
        if new_notepad_name is not None and (new_notepad_name := sanitize(new_notepad_name)):
            notepad_name = sanitize(notepad_name)
            (self.notepad_dir / sanitize(notepad_name)).rename(self.notepad_dir / sanitize(new_notepad_name))
            self.refresh_notepads()
            return gr.update(value=new_notepad_name, choices=[new_entry] + list(self.notepads))
        return gr.update()

    def remove_notepad(self, notepad_name):
        if notepad_name:
            notepad = self.notepad_dir / sanitize(notepad_name)
            for n in notepad.glob('.*.txt'):
                n.unlink()
            notepad.rmdir()
            return self.get_latest()
        return gr.update(), gr.update(), gr.update()

    def get_latest(self):
        self.refresh_notepads()
        for k, v in self.notepads.items():
            return (
                gr.update(value=k, choices=[new_entry] + list(self.notepads)),
                gr.update(value=v[0], choices=v),
                gr.update(value=self.read_notepad(k, v[0])),
            )
        return (
            gr.update(value='', choices=[]),
            gr.update(value='', choices=[]),
            gr.update(value='')
        )

    def refresh(self, notepad_name):
        notepad_name = sanitize(notepad_name)
        self.refresh_notepads()
        return gr.update(choices=[new_entry] + list(self.notepads)), gr.update(choices=self.notepads.get(notepad_name, []))


def on_load(request: gr.Request):
    try:
        # [notepad_name, history, notepad]
        user_notepads = NotepadUser(request)
        return user_notepads.get_latest()
    except Exception as e:
        gr.Error(str(e))
        errors.report(f"Error notepad on_load", exc_info=True)
        return (gr.update(), ) * 3


def save_notepad(notepad_name, notepad, request: gr.Request):
    try:
        user_notepads = NotepadUser(request)
        return user_notepads.write_notepad(notepad_name, notepad)
    except Exception as e:
        gr.Error(str(e))
        errors.report(f"Error notepad save_notepad", exc_info=True)
        return (gr.update(), ) * 2


def rename_notepad(notepad_name, new_name, request: gr.Request):
    try:
        user_notepads = NotepadUser(request)
        return user_notepads.rename_notepad(notepad_name, new_name)
    except Exception as e:
        gr.Error(str(e))
        errors.report(f"Error notepad rename_notepad", exc_info=True)
        return gr.update()


def remove_notepad(notepad_name, request: gr.Request):
    try:
        user_notepads = NotepadUser(request)
        return user_notepads.remove_notepad(notepad_name)
    except Exception as e:
        gr.Error(str(e))
        errors.report(f"Error notepad remove_notepad", exc_info=True)
        return (gr.update(), ) * 3


def read_notepad(notepad_name, request: gr.Request):
    try:
        if notepad_name := sanitize(notepad_name):
            user_notepads = NotepadUser(request)
            notepad_version = user_notepads.refresh_notepad(notepad_name)
            if notepad_version:
                version = notepad_version[0]
                return gr.update(value=version, choices=notepad_version), gr.update(value=user_notepads.read_notepad(notepad_name, version))
        return gr.update(value='', choices=[]), gr.update()
    except Exception as e:
        gr.Error(str(e))
        errors.report(f"Error notepad read_notepad", exc_info=True)
        return (gr.update(), ) * 2


def read_notepad_version(notepad_name, version, request: gr.Request):
    try:
        if notepad_name := sanitize(notepad_name):
            user_notepads = NotepadUser(request)
            notepad_version = user_notepads.refresh_notepad(notepad_name)
            version = sanitize(version)
            if notepad_version:
                if version not in notepad_version:
                    version = notepad_version[0]
                return gr.update(value=version, choices=notepad_version), gr.update(value=user_notepads.read_notepad(notepad_name, version))
        return gr.update(value='', choices=[]), gr.update()
    except Exception as e:
        gr.Error(str(e))
        errors.report(f"Error notepad read_notepad_version", exc_info=True)
        return (gr.update(), ) * 2


def refresh(notepad_name, request: gr.Request):
    try:
        user_notepads = NotepadUser(request)
        return user_notepads.refresh(notepad_name)
    except Exception as e:
        gr.Error(str(e))
        errors.report(f"Error notepad refresh", exc_info=True)
        return (gr.update(), ) * 2


class Notepad(scripts.Script):
    def title(self):
        return title

    def show(self, is_img2img):
        if not is_img2img:
            return scripts.AlwaysVisible

    def ui(self, is_img2img):
        with gr.Blocks(analytics_enabled=False) as ui:
            with gr.Accordion(label=title, open=False):
                with gr.Row():
                    notepad_name = gr.Dropdown(label='Notepad', allow_custom_value=True)
                    version = gr.Dropdown(label='Notepad history')
                    refresh_button = ui_common.ToolButton(value=ui_common.refresh_symbol, tooltip='Refresh Notepads')
                    save_button = ui_common.ToolButton(value='💾', tooltip='Refresh Notepads')
                    rename_button = ui_common.ToolButton(value='📝', tooltip='Rename Notepads')
                    delete_button = ui_common.ToolButton(value='🗑️', tooltip='Delete Notepads')
                notepad = gr.Textbox(label=title, lines=5)

            components = [notepad_name, version, refresh_button, notepad, save_button, rename_button, delete_button]
            [setattr(c, 'do_not_save_to_config', True) for c in components]

        ui.load(fn=on_load, outputs=[notepad_name, version, notepad], show_progress='hidden')
        save_button.click(fn=save_notepad, inputs=[notepad_name, notepad], outputs=[notepad_name, version], show_progress='hidden')
        refresh_button.click(fn=refresh, inputs=[notepad_name], outputs=[notepad_name, version])
        rename_button.click(fn=rename_notepad, inputs=[notepad_name, notepad_name], outputs=[notepad_name], _js='notepadConfirmRename', show_progress='hidden')
        delete_button.click(fn=remove_notepad, inputs=[notepad_name], outputs=[notepad_name, version, notepad], _js='notepadConfirmDelete', show_progress='hidden')
        notepad_name.blur(fn=read_notepad, inputs=[notepad_name], outputs=[version, notepad], show_progress='hidden')
        version.blur(fn=read_notepad_version, inputs=[notepad_name, version], outputs=[version, notepad], show_progress='hidden')
