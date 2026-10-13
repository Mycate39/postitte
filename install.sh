#!/usr/bin/env bash
# Installe Postitte pour l'utilisateur courant (aucun fichier système modifié).
set -euo pipefail

# --update : appelé par l'application elle-même, qui se relance ensuite.
UPDATE=0
[ "${1:-}" = "--update" ] && UPDATE=1

SRC="$(cd "$(dirname "$0")" && pwd)"
BIN="$HOME/.local/bin/postitte"
APPS="$HOME/.local/share/applications"
AUTOSTART="$HOME/.config/autostart"

if ! python3 -c 'import gi; gi.require_version("Gtk", "3.0"); from gi.repository import Gtk' 2>/dev/null; then
    echo "Installation des dépendances GTK (mot de passe sudo demandé)…"
    sudo apt-get install -y python3-gi gir1.2-gtk-3.0
fi

install -Dm755 "$SRC/postitte.py" "$BIN"
install -Dm644 "$SRC/data/postitte.svg" "$HOME/.local/share/icons/hicolor/scalable/apps/postitte.svg"

mkdir -p "$APPS" "$AUTOSTART"
sed -e "s|@BIN@|$BIN|g" -e "s|@ARGS@||" "$SRC/data/postitte.desktop" > "$APPS/postitte.desktop"
sed -e "s|@BIN@|$BIN|g" -e "s|@ARGS@|--autostart|" "$SRC/data/postitte.desktop" > "$AUTOSTART/postitte.desktop"

update-desktop-database "$APPS" 2>/dev/null || true
gtk-update-icon-cache -q "$HOME/.local/share/icons/hicolor" 2>/dev/null || true

if [ "$UPDATE" = 1 ]; then
    echo "Postitte a été mis à jour."
    exit 0
fi

echo "Postitte est installé."
echo " • Lancez-le depuis le menu des applications (« Postitte »)."
echo " • Il démarrera automatiquement à chaque ouverture de session."

"$BIN" --autostart >/dev/null 2>&1 &
disown
