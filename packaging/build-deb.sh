#!/usr/bin/env bash
# Construit le paquet Debian/Ubuntu :  packaging/build-deb.sh
# Résultat : dist/postitte_<version>_all.deb
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VERSION="$(sed -n 's/^__version__ = "\(.*\)"$/\1/p' "$ROOT/postitte.py")"
BUILD="$(mktemp -d)"
PKG="$BUILD/postitte"
trap 'rm -rf "$BUILD"' EXIT

install -Dm755 "$ROOT/postitte.py" "$PKG/usr/bin/postitte"
install -Dm644 "$ROOT/data/postitte.svg" "$PKG/usr/share/icons/hicolor/scalable/apps/postitte.svg"
mkdir -p "$PKG/usr/share/applications" "$PKG/etc/xdg/autostart"
sed -e "s|@BIN@|/usr/bin/postitte|g" -e "s|@ARGS@||" \
    "$ROOT/data/postitte.desktop" > "$PKG/usr/share/applications/postitte.desktop"
sed -e "s|@BIN@|/usr/bin/postitte|g" -e "s|@ARGS@|--autostart|" \
    "$ROOT/data/postitte.desktop" > "$PKG/etc/xdg/autostart/postitte.desktop"
chmod 644 "$PKG/usr/share/applications/postitte.desktop" "$PKG/etc/xdg/autostart/postitte.desktop"

mkdir -p "$PKG/DEBIAN"
echo "/etc/xdg/autostart/postitte.desktop" > "$PKG/DEBIAN/conffiles"
cat > "$PKG/DEBIAN/control" <<EOF
Package: postitte
Version: $VERSION
Architecture: all
Maintainer: Mycate39 <andeolchenaux509@gmail.com>
Depends: python3, python3-gi, gir1.2-gtk-3.0
Section: utils
Priority: optional
Installed-Size: $(du -sk "$PKG/usr" "$PKG/etc" | awk '{s += $1} END {print s}')
Homepage: https://github.com/Mycate39/postitte
Description: Post-it éditables directement sur le bureau
 Postitte affiche des notes autocollantes sur le bureau Ubuntu. On écrit
 directement dedans ; elles sont enregistrées automatiquement et l'application
 se met à jour depuis GitHub.
EOF

mkdir -p "$ROOT/dist"
dpkg-deb --root-owner-group --build "$PKG" "$ROOT/dist/postitte_${VERSION}_all.deb"
