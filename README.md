# Postitte

Des post-it posés sur le bureau Ubuntu. On écrit directement dedans, sans fenêtre d'édition séparée.

## Installation

1. Téléchargez le fichier **`postitte_X.Y.Z_all.deb`** de la [dernière release](https://github.com/Mycate39/postitte/releases/latest).
2. Double-cliquez dessus. Le Centre d'applications s'ouvre : cliquez sur **Installer**.

Si le double-clic ne fonctionne pas, ouvrez un terminal et lancez :

```bash
cd ~/Téléchargements   # ou ~/Downloads si Ubuntu est en anglais
sudo apt install ./postitte_*_all.deb
```

Postitte apparaît dans le menu des applications et démarre automatiquement à chaque ouverture de session.

### Sans paquet (pour développer)

```bash
git clone https://github.com/Mycate39/postitte.git
cd postitte
./install.sh
```

Postitte s'installe alors pour votre utilisateur uniquement (`~/.local`).

## Utilisation

| Action | Comment |
|---|---|
| Écrire | Cliquez dans la note et tapez, tout est enregistré automatiquement |
| Déplacer | Glissez la barre du haut |
| Redimensionner | Glissez le coin ◢ en bas à droite |
| Nouvelle note | Bouton **+**, `Ctrl+N`, ou relancez « Postitte » depuis le menu |
| Couleur | Bouton **●** |
| Premier plan / bureau | Bouton 📌 (activé : la note reste au-dessus des fenêtres) |
| Taille du texte | `Ctrl` + molette, `Ctrl` `+` / `-`, `Ctrl+0` pour réinitialiser |
| Supprimer | Bouton **✕** (confirmation demandée si la note contient du texte) |

Les notes sont enregistrées dans `~/.local/share/postitte/notes.json`.

## Mises à jour

Au démarrage, puis toutes les 6 heures, Postitte vérifie s'il existe une nouvelle [release GitHub](https://github.com/Mycate39/postitte/releases). Si oui, une fenêtre propose de l'installer et un bouton **⬆** apparaît sur les notes. Cliquez sur **Mettre à jour** : Postitte télécharge la nouvelle version, l'installe et redémarre. Si vous l'avez installé avec le `.deb`, Ubuntu vous demande votre mot de passe. Vos notes ne sont pas touchées.

### Publier une nouvelle version

Commitez vos modifications, puis :

```bash
./release.sh 1.1.0
```

Le script met à jour `__version__` dans `postitte.py`, crée le tag `v1.1.0` et pousse le tout sur GitHub. Le workflow [.github/workflows/release.yml](.github/workflows/release.yml) vérifie le code, construit le paquet `.deb` avec [packaging/build-deb.sh](packaging/build-deb.sh), teste son installation et publie la release. Les applications installées la proposent ensuite.

Si vous créez la release à la main sur GitHub, le tag doit correspondre à `__version__`. Sinon, l'application proposerait la même mise à jour en boucle.

## Désinstallation

- Installé avec le `.deb` : supprimez Postitte depuis le Centre d'applications, ou lancez `sudo apt remove postitte`.
- Installé avec `install.sh` : lancez `./uninstall.sh` (ajoutez `--purge` pour effacer aussi les notes).

Dans le premier cas, les notes restent dans `~/.local/share/postitte/`.

## Remarque sur Wayland

Sous Wayland (session par défaut d'Ubuntu), GNOME ne laisse pas une application choisir la position de ses fenêtres ni les garder sous les autres. Postitte passe donc automatiquement par XWayland, et cela fonctionne sans réglage.
