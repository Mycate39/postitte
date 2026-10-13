#!/usr/bin/env python3
"""Postitte — des post-it éditables directement sur le bureau Ubuntu."""

import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import threading
import urllib.request
import uuid

__version__ = "1.1.0"

# Sous Wayland, GNOME interdit à une fenêtre de choisir sa position ou de
# rester sous les autres. En passant par XWayland, tout fonctionne.
os.environ.setdefault("GDK_BACKEND", "x11")

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gdk, Gio, GLib, Gtk  # noqa: E402

APP_ID = "io.github.postitte"
DATA_DIR = os.path.join(GLib.get_user_data_dir(), "postitte")
DATA_FILE = os.path.join(DATA_DIR, "notes.json")
# Installé par le paquet .deb (/usr/bin) ou par install.sh (~/.local/bin) ?
INSTALLED_FROM_DEB = os.path.realpath(__file__).startswith("/usr/")
INSTALLED_BIN = ("/usr/bin/postitte" if INSTALLED_FROM_DEB
                 else os.path.join(os.path.expanduser("~"), ".local", "bin", "postitte"))

GITHUB_REPO = "Mycate39/postitte"
LATEST_RELEASE_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
UPDATE_CHECK_DELAY = 5            # secondes après le démarrage
UPDATE_CHECK_INTERVAL = 6 * 3600  # puis toutes les 6 heures

# nom -> (couleur du corps, couleur de l'en-tête)
COLORS = {
    "jaune": ("#fff59d", "#fbe86a"),
    "orange": ("#ffcc80", "#ffb74d"),
    "rose": ("#f8bbd0", "#f48fb1"),
    "violet": ("#e1bee7", "#ce93d8"),
    "bleu": ("#b3e5fc", "#81d4fa"),
    "vert": ("#c5e1a5", "#aed581"),
}
DEFAULT_COLOR = "jaune"
DEFAULT_FONT_SIZE = 12
DEFAULT_SIZE = (240, 240)


def build_css():
    css = """
    window.note { border: 1px solid rgba(0, 0, 0, 0.18); }
    .note-header { padding: 2px 4px; }
    .note-header button {
        padding: 0 6px; min-height: 22px; min-width: 22px;
        border: none; border-radius: 4px; box-shadow: none;
        background: transparent; color: rgba(0, 0, 0, 0.6);
    }
    .note-header button:hover, .note-header button:checked {
        background: rgba(0, 0, 0, 0.10);
    }
    textview, textview text { color: #2b2b2b; font-family: "Ubuntu", sans-serif; }
    .note-grip { color: rgba(0, 0, 0, 0.35); padding: 0 4px 2px 0; }
    .swatch {
        min-width: 22px; min-height: 22px; padding: 0; border-radius: 11px;
        border: 1px solid rgba(0, 0, 0, 0.25); background-image: none;
    }
    """
    for name, (body, header) in COLORS.items():
        css += f"""
        window.note-{name}, window.note-{name} textview,
        window.note-{name} textview text {{ background-color: {body}; }}
        window.note-{name} .note-header {{ background-color: {header}; }}
        .swatch-{name} {{ background-color: {body}; }}
        """
    return css.encode()


# --- Mises à jour -------------------------------------------------------

def parse_version(text):
    parts = []
    for part in text.strip().lstrip("vV").split("."):
        digits = ""
        for char in part:
            if not char.isdigit():
                break
            digits += char
        parts.append(int(digits or 0))
    return tuple((parts + [0, 0, 0])[:3])


def _github_request(url, api=True):
    headers = {"User-Agent": f"Postitte/{__version__}"}
    if api:
        headers["Accept"] = "application/vnd.github+json"
    return urllib.request.Request(url, headers=headers)


def _download(url, dest, api=True):
    with urllib.request.urlopen(_github_request(url, api), timeout=60) as resp,             open(dest, "wb") as f:
        shutil.copyfileobj(resp, f)


def fetch_latest_release():
    with urllib.request.urlopen(_github_request(LATEST_RELEASE_URL), timeout=15) as resp:
        release = json.load(resp)
    debs = [a["browser_download_url"] for a in release.get("assets", [])
            if a["name"].endswith(".deb")]
    notes = (release.get("body") or "").strip()
    if notes.startswith("### Installation"):
        # Consignes d'installation pour la page GitHub, inutiles dans l'app.
        _, _, rest = notes.partition("\n## ")
        notes = "## " + rest if rest else ""
    return {
        "version": release["tag_name"].lstrip("vV"),
        "notes": notes,
        "tarball": release["tarball_url"],
        "deb": debs[0] if debs else None,
    }


def download_and_install(info):
    """Installe la release : via son paquet .deb si Postitte a été installé
    ainsi, sinon via le install.sh de son code source."""
    with tempfile.TemporaryDirectory(prefix="postitte-") as tmp:
        if INSTALLED_FROM_DEB:
            if not info["deb"]:
                raise RuntimeError("Cette version ne contient pas de paquet .deb.")
            package = os.path.join(tmp, "postitte.deb")
            _download(info["deb"], package, api=False)
            os.chmod(tmp, 0o755)  # dpkg tourne en root mais lit via le dossier
            command = ["pkexec", "dpkg", "-i", package]
        else:
            archive = os.path.join(tmp, "release.tar.gz")
            _download(info["tarball"], archive)
            extract_dir = os.path.join(tmp, "src")
            with tarfile.open(archive) as tar:
                if hasattr(tarfile, "data_filter"):
                    tar.extractall(extract_dir, filter="data")
                else:
                    tar.extractall(extract_dir)
            # GitHub place tout dans un dossier « <utilisateur>-<dépôt>-<commit> ».
            (top,) = os.listdir(extract_dir)
            command = ["bash", os.path.join(extract_dir, top, "install.sh"), "--update"]

        result = subprocess.run(command, capture_output=True, text=True)
        if result.returncode in (126, 127) and command[0] == "pkexec":
            raise RuntimeError("Mise à jour annulée : le mot de passe n'a pas été confirmé.")
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or result.stdout.strip()
                               or f"L'installation a échoué (code {result.returncode})")


class UpdateDialog(Gtk.Dialog):
    def __init__(self, app, info, parent):
        super().__init__(title="Mise à jour de Postitte", transient_for=parent)
        self.app = app
        self.info = info
        self.set_keep_above(True)
        self.set_default_size(420, -1)

        box = self.get_content_area()
        box.set_spacing(10)
        box.set_border_width(14)

        title = Gtk.Label(xalign=0)
        title.set_markup(
            f"<b>Postitte {GLib.markup_escape_text(info['version'])} est disponible</b>\n"
            f"Version installée : {__version__}"
        )
        box.add(title)

        if info["notes"]:
            notes = Gtk.Label(label=info["notes"], xalign=0, yalign=0,
                              wrap=True, selectable=True)
            scrolled = Gtk.ScrolledWindow()
            scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
            scrolled.set_max_content_height(220)
            scrolled.set_propagate_natural_height(True)
            scrolled.add(notes)
            box.add(scrolled)

        status_box = Gtk.Box(spacing=8)
        self.spinner = Gtk.Spinner()
        self.status = Gtk.Label(xalign=0, wrap=True)
        status_box.pack_start(self.spinner, False, False, 0)
        status_box.pack_start(self.status, True, True, 0)
        box.add(status_box)

        self.later_btn = self.add_button("Plus tard", Gtk.ResponseType.CANCEL)
        self.update_btn = self.add_button("Mettre à jour", Gtk.ResponseType.ACCEPT)
        self.update_btn.get_style_context().add_class("suggested-action")
        self.connect("response", self._on_response)
        self.show_all()

    def _on_response(self, _dialog, response):
        if response != Gtk.ResponseType.ACCEPT:
            self.destroy()
            return
        self.later_btn.set_sensitive(False)
        self.update_btn.set_sensitive(False)
        self.spinner.start()
        self.status.set_text("Téléchargement et installation…")
        threading.Thread(target=self._install_worker, daemon=True).start()

    def _install_worker(self):
        try:
            download_and_install(self.info)
        except Exception as err:  # réseau, archive, script d'installation…
            GLib.idle_add(self._on_failed, str(err))
        else:
            GLib.idle_add(self.app.restart)

    def _on_failed(self, message):
        self.spinner.stop()
        self.status.set_text(f"La mise à jour a échoué :\n{message}")
        self.later_btn.set_label("Fermer")
        self.later_btn.set_sensitive(True)
        self.update_btn.set_label("Réessayer")
        self.update_btn.set_sensitive(True)
        return False


class NoteWindow(Gtk.Window):
    def __init__(self, app, data):
        super().__init__(application=app, title="Postitte")
        self.app = app
        self.data = data

        self.set_decorated(False)
        self.set_skip_taskbar_hint(True)
        self.set_skip_pager_hint(True)
        self.set_type_hint(Gdk.WindowTypeHint.UTILITY)
        self.stick()  # visible sur tous les espaces de travail
        self.set_icon_name("postitte")
        self.get_style_context().add_class("note")

        self.set_default_size(data["width"], data["height"])
        self.move(data["x"], data["y"])

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.add(root)
        root.pack_start(self._build_header(), False, False, 0)

        self.textview = Gtk.TextView()
        self.textview.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        for side in ("left", "right", "top", "bottom"):
            getattr(self.textview, f"set_{side}_margin")(10)
        self.textview.get_buffer().set_text(data["text"])
        self.textview.get_buffer().connect("changed", self._on_text_changed)
        self.textview.connect("scroll-event", self._on_scroll)
        self.font_provider = Gtk.CssProvider()
        self.textview.get_style_context().add_provider(
            self.font_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION + 1
        )

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.add(self.textview)
        root.pack_start(scrolled, True, True, 0)
        root.pack_start(self._build_footer(), False, False, 0)

        self.connect("configure-event", self._on_configure)
        self.connect("key-press-event", self._on_key_press)

        self.apply_color(data["color"])
        self.apply_font_size()
        self.apply_pin()

    # --- Construction ---------------------------------------------------

    def _build_header(self):
        events = Gtk.EventBox()
        events.get_style_context().add_class("note-header")
        events.connect("button-press-event", self._on_header_press)
        events.connect("realize", lambda w: self._set_cursor(w, "move"))

        box = Gtk.Box(spacing=2)
        events.add(box)

        add_btn = Gtk.Button(label="+", tooltip_text="Nouvelle note (Ctrl+N)")
        add_btn.connect("clicked", lambda _b: self.app.new_note(near=self))
        box.pack_start(add_btn, False, False, 0)

        color_btn = Gtk.MenuButton(label="●", tooltip_text="Couleur")
        color_btn.set_popover(self._build_color_popover(color_btn))
        box.pack_start(color_btn, False, False, 0)

        box.pack_start(Gtk.Box(), True, True, 0)  # espace extensible

        self.update_btn = Gtk.Button(label="⬆", tooltip_text="Mise à jour disponible")
        self.update_btn.set_no_show_all(True)
        self.update_btn.connect("clicked", lambda _b: self.app.show_update_dialog())
        box.pack_start(self.update_btn, False, False, 0)

        self.pin_btn = Gtk.ToggleButton(label="📌")
        self.pin_btn.set_active(self.data["on_top"])
        self.pin_btn.connect("toggled", self._on_pin_toggled)
        box.pack_start(self.pin_btn, False, False, 0)

        close_btn = Gtk.Button(label="✕", tooltip_text="Supprimer la note")
        close_btn.connect("clicked", self._on_delete_clicked)
        box.pack_start(close_btn, False, False, 0)
        return events

    def _build_color_popover(self, relative_to):
        popover = Gtk.Popover(relative_to=relative_to)
        box = Gtk.Box(spacing=6, margin=6)
        for name in COLORS:
            swatch = Gtk.Button(tooltip_text=name.capitalize())
            swatch.get_style_context().add_class("swatch")
            swatch.get_style_context().add_class(f"swatch-{name}")
            swatch.connect("clicked", self._on_color_chosen, name, popover)
            box.pack_start(swatch, False, False, 0)
        box.show_all()
        popover.add(box)
        return popover

    def _build_footer(self):
        box = Gtk.Box()
        grip = Gtk.EventBox(tooltip_text="Redimensionner")
        label = Gtk.Label(label="◢")
        label.get_style_context().add_class("note-grip")
        grip.add(label)
        grip.connect("button-press-event", self._on_grip_press)
        grip.connect("realize", lambda w: self._set_cursor(w, "se-resize"))
        box.pack_end(grip, False, False, 0)
        return box

    @staticmethod
    def _set_cursor(widget, name):
        window = widget.get_window()
        window.set_cursor(Gdk.Cursor.new_from_name(window.get_display(), name))

    # --- Apparence ------------------------------------------------------

    def apply_color(self, name):
        ctx = self.get_style_context()
        for other in COLORS:
            ctx.remove_class(f"note-{other}")
        ctx.add_class(f"note-{name}")
        self.data["color"] = name

    def apply_font_size(self):
        size = self.data["font_size"]
        self.font_provider.load_from_data(f"textview {{ font-size: {size}pt; }}".encode())

    def change_font_size(self, delta):
        size = self.data["font_size"] + delta if delta else DEFAULT_FONT_SIZE
        self.data["font_size"] = max(7, min(48, size))
        self.apply_font_size()
        self.app.schedule_save()

    def apply_pin(self):
        on_top = self.data["on_top"]
        self.set_keep_above(on_top)
        self.set_keep_below(not on_top)
        self.pin_btn.set_tooltip_text(
            "Remettre sur le bureau" if on_top else "Garder au premier plan"
        )

    # --- Événements -----------------------------------------------------

    def _on_header_press(self, _widget, event):
        if event.button == 1 and event.type == Gdk.EventType.BUTTON_PRESS:
            self.begin_move_drag(event.button, int(event.x_root), int(event.y_root), event.time)
        return False

    def _on_grip_press(self, _widget, event):
        if event.button == 1:
            self.begin_resize_drag(
                Gdk.WindowEdge.SOUTH_EAST, event.button,
                int(event.x_root), int(event.y_root), event.time,
            )
        return True

    def _on_configure(self, *_args):
        x, y = self.get_position()
        w, h = self.get_size()
        if (x, y, w, h) != (self.data["x"], self.data["y"], self.data["width"], self.data["height"]):
            self.data.update(x=x, y=y, width=w, height=h)
            self.app.schedule_save()
        return False

    def _on_text_changed(self, buffer):
        start, end = buffer.get_bounds()
        self.data["text"] = buffer.get_text(start, end, True)
        self.app.schedule_save()

    def _on_color_chosen(self, _button, name, popover):
        popover.popdown()
        self.apply_color(name)
        self.app.schedule_save()

    def _on_pin_toggled(self, button):
        self.data["on_top"] = button.get_active()
        self.apply_pin()
        self.app.schedule_save()

    def _on_scroll(self, _widget, event):
        if not event.state & Gdk.ModifierType.CONTROL_MASK:
            return False
        if event.direction == Gdk.ScrollDirection.UP:
            self.change_font_size(+1)
        elif event.direction == Gdk.ScrollDirection.DOWN:
            self.change_font_size(-1)
        elif event.direction == Gdk.ScrollDirection.SMOOTH:
            _ok, _dx, dy = event.get_scroll_deltas()
            if dy:
                self.change_font_size(-1 if dy > 0 else +1)
        return True

    def _on_key_press(self, _widget, event):
        if not event.state & Gdk.ModifierType.CONTROL_MASK:
            return False
        key = Gdk.keyval_name(event.keyval)
        if key in ("n", "N"):
            self.app.new_note(near=self)
        elif key in ("plus", "equal", "KP_Add"):
            self.change_font_size(+1)
        elif key in ("minus", "KP_Subtract"):
            self.change_font_size(-1)
        elif key in ("0", "KP_0"):
            self.change_font_size(0)
        else:
            return False
        return True

    def _on_delete_clicked(self, _button):
        if self.data["text"].strip():
            dialog = Gtk.MessageDialog(
                transient_for=self, modal=True,
                message_type=Gtk.MessageType.QUESTION,
                buttons=Gtk.ButtonsType.NONE,
                text="Supprimer cette note ?",
            )
            dialog.format_secondary_text("Son contenu sera définitivement perdu.")
            dialog.add_buttons("Annuler", Gtk.ResponseType.CANCEL,
                               "Supprimer", Gtk.ResponseType.ACCEPT)
            dialog.set_keep_above(True)
            response = dialog.run()
            dialog.destroy()
            if response != Gtk.ResponseType.ACCEPT:
                return
        self.app.remove_note(self)


class PostitteApp(Gtk.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID,
                         flags=Gio.ApplicationFlags.HANDLES_COMMAND_LINE)
        self.notes = []
        self.loaded = False
        self._save_id = 0
        self.update_info = None
        self.update_dialog = None

    def do_startup(self):
        Gtk.Application.do_startup(self)
        provider = Gtk.CssProvider()
        provider.load_from_data(build_css())
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

    def do_command_line(self, command_line):
        args = command_line.get_arguments()[1:]
        if not self.loaded:
            self.loaded = True
            for data in self.load():
                self._open(data)
            if not self.notes or "--new" in args:
                self.new_note()
            GLib.timeout_add_seconds(UPDATE_CHECK_DELAY, self._check_once)
            GLib.timeout_add_seconds(UPDATE_CHECK_INTERVAL, self._check_periodic)
        elif "--autostart" not in args:
            # Relancer l'application alors qu'elle tourne déjà = nouvelle note.
            self.new_note()
        return 0

    def do_shutdown(self):
        self.save_now()
        Gtk.Application.do_shutdown(self)

    # --- Notes ----------------------------------------------------------

    def _open(self, data):
        window = NoteWindow(self, data)
        self.notes.append(window)
        window.show_all()
        if self.update_info:
            window.update_btn.show()
        return window

    def new_note(self, near=None):
        if near is not None:
            x, y = near.get_position()
            x, y = x + 30, y + 30
        else:
            offset = 30 * (len(self.notes) % 10)
            x, y = 120 + offset, 120 + offset
        data = {
            "id": uuid.uuid4().hex,
            "text": "",
            "x": x, "y": y,
            "width": DEFAULT_SIZE[0], "height": DEFAULT_SIZE[1],
            "color": near.data["color"] if near is not None else DEFAULT_COLOR,
            "font_size": DEFAULT_FONT_SIZE,
            "on_top": False,
        }
        window = self._open(data)
        window.present()
        window.textview.grab_focus()
        self.schedule_save()

    def remove_note(self, window):
        self.notes.remove(window)
        self.save_now()
        window.destroy()

    # --- Mises à jour ----------------------------------------------------

    def _check_once(self):
        self.check_for_updates()
        return False

    def _check_periodic(self):
        self.check_for_updates()
        return True

    def check_for_updates(self):
        threading.Thread(target=self._check_worker, daemon=True).start()

    def _check_worker(self):
        try:
            info = fetch_latest_release()
        except Exception as err:  # hors ligne, pas encore de release, limite d'API…
            print(f"Postitte : vérification des mises à jour impossible : {err}",
                  file=sys.stderr)
            return
        if parse_version(info["version"]) > parse_version(__version__):
            GLib.idle_add(self._on_update_found, info)

    def _on_update_found(self, info):
        is_new = self.update_info is None or self.update_info["version"] != info["version"]
        self.update_info = info
        for window in self.notes:
            window.update_btn.show()
        if is_new:
            self.show_update_dialog()
        return False

    def show_update_dialog(self):
        if self.update_dialog is not None:
            self.update_dialog.present()
            return
        parent = self.notes[0] if self.notes else None
        self.update_dialog = UpdateDialog(self, self.update_info, parent)
        self.update_dialog.connect("destroy", self._on_update_dialog_destroyed)

    def _on_update_dialog_destroyed(self, _dialog):
        self.update_dialog = None

    def restart(self):
        """Relance la version fraîchement installée une fois ce processus terminé."""
        self.save_now()
        subprocess.Popen(
            ["sh", "-c", 'while kill -0 "$1" 2>/dev/null; do sleep 0.2; done; exec "$2" --autostart',
             "postitte-restart", str(os.getpid()), INSTALLED_BIN],
            start_new_session=True,
        )
        self.quit()
        return False

    # --- Persistance ----------------------------------------------------

    @staticmethod
    def load():
        try:
            with open(DATA_FILE, encoding="utf-8") as f:
                notes = json.load(f)
        except FileNotFoundError:
            return []
        except (OSError, ValueError) as err:
            print(f"Postitte : impossible de lire {DATA_FILE} : {err}", file=sys.stderr)
            return []
        result = []
        for note in notes:
            data = {
                "id": uuid.uuid4().hex, "text": "", "x": 120, "y": 120,
                "width": DEFAULT_SIZE[0], "height": DEFAULT_SIZE[1],
                "color": DEFAULT_COLOR, "font_size": DEFAULT_FONT_SIZE, "on_top": False,
            }
            data.update(note)
            if data["color"] not in COLORS:
                data["color"] = DEFAULT_COLOR
            result.append(data)
        return result

    def schedule_save(self):
        if not self._save_id:
            self._save_id = GLib.timeout_add(500, self._on_save_timeout)

    def _on_save_timeout(self):
        self._save_id = 0
        self.save_now()
        return False

    def save_now(self):
        if self._save_id:
            GLib.source_remove(self._save_id)
            self._save_id = 0
        os.makedirs(DATA_DIR, exist_ok=True)
        tmp = DATA_FILE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump([w.data for w in self.notes], f, ensure_ascii=False, indent=2)
        os.replace(tmp, DATA_FILE)


if __name__ == "__main__":
    sys.exit(PostitteApp().run(sys.argv))
