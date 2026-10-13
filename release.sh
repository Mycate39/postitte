#!/usr/bin/env bash
# Publie une nouvelle version de Postitte :  ./release.sh 1.1.0
# Met à jour __version__, commite, pousse sur GitHub et crée la release,
# que les applications installées proposent ensuite en mise à jour.
set -euo pipefail

version="${1:?Usage : ./release.sh <version>   (ex. ./release.sh 1.1.0)}"
version="${version#v}"
cd "$(dirname "$0")"

if ! [[ "$version" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    echo "Version invalide : « $version » (format attendu : 1.2.3)." >&2
    exit 1
fi
if [ -n "$(git status --porcelain)" ]; then
    echo "Des modifications ne sont pas commitées. Commitez-les d'abord :" >&2
    git status --short >&2
    exit 1
fi
if git rev-parse -q --verify "refs/tags/v$version" >/dev/null; then
    echo "Le tag v$version existe déjà." >&2
    exit 1
fi

command -v gh >/dev/null || { echo "Installez GitHub CLI (gh) : https://cli.github.com" >&2; exit 1; }

sed -i "s/^__version__ = \".*\"$/__version__ = \"$version\"/" postitte.py
python3 -m py_compile postitte.py 2>/dev/null || python -m py_compile postitte.py
rm -rf __pycache__
bash -n install.sh

git commit -qm "Version $version" postitte.py
git tag "v$version"
git push -q origin HEAD "v$version"
gh release create "v$version" --title "Postitte v$version" --generate-notes

echo "Version $version publiée : les applications installées vont la proposer."
