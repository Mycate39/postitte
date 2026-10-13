# Postitte

Des post-it posés sur le bureau Ubuntu. On écrit directement dedans, sans fenêtre d'édition séparée.

## Installation

```bash
git clone https://github.com/Mycate39/postitte.git
cd postitte
./install.sh
```

Postitte s'installe pour votre utilisateur uniquement (`~/.local`), sans droits administrateur. Si Python-GTK manque (rare sur Ubuntu), le script demande le mot de passe pour l'installer. Il se lance ensuite automatiquement à chaque ouverture de session.

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

Au démarrage, puis toutes les 6 heures, Postitte vérifie s'il existe une nouvelle [release GitHub](https://github.com/Mycate39/postitte/releases). Si oui, une fenêtre propose de l'installer et un bouton **⬆** apparaît sur les notes. Cliquez sur **Mettre à jour** : Postitte télécharge la nouvelle version, l'installe et redémarre. Vos notes ne sont pas touchées.

### Publier une nouvelle version

Commitez vos modifications, puis :

```bash
./release.sh 1.1.0
```

Le script met à jour `__version__` dans `postitte.py`, commite, pousse sur GitHub et crée la release `v1.1.0` (il nécessite [GitHub CLI](https://cli.github.com)). Les applications installées la proposent ensuite.

Si vous créez la release à la main sur GitHub, le tag doit correspondre à `__version__`. Sinon, l'application proposerait la même mise à jour en boucle.

## Désinstallation

```bash
./uninstall.sh          # conserve les notes
./uninstall.sh --purge  # supprime aussi les notes
```

## Remarque sur Wayland

Sous Wayland (session par défaut d'Ubuntu), GNOME ne laisse pas une application choisir la position de ses fenêtres ni les garder sous les autres. Postitte passe donc automatiquement par XWayland, et cela fonctionne sans réglage.
