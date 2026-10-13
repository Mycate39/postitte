#!/usr/bin/env bash
# Désinstalle Postitte. Les notes sont conservées sauf avec --purge.
set -euo pipefail

pkill -f "$HOME/.local/bin/postitte" 2>/dev/null || true

rm -f "$HOME/.local/bin/postitte" \
      "$HOME/.local/share/applications/postitte.desktop" \
      "$HOME/.config/autostart/postitte.desktop" \
      "$HOME/.local/share/icons/hicolor/scalable/apps/postitte.svg"

if [ "${1:-}" = "--purge" ]; then
    rm -rf "$HOME/.local/share/postitte"
    echo "Postitte et toutes les notes ont été supprimés."
else
    echo "Postitte a été désinstallé. Vos notes restent dans ~/.local/share/postitte/"
    echo "(relancez avec --purge pour les effacer aussi)."
fi
