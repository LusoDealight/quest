# Quest

Todo list gamifiée, installable sur PC et mobile (PWA) : sujets et jalons à 10 / 25 / 50 XP, 7 rangs, tour de progression et minuteur focus / pause.

- `index.html` : l'application complète (HTML, CSS et JS dans un seul fichier).
- `jeu.html` : la Tour (Ville + étage 1 en 3D low-poly : prairie, hameau, 7 quêtes, mini-boss, Roi des slimes, escalier caché derrière la cascade). Ouverte uniquement pendant une pause du minuteur ; l'énergie de combat vient des cycles de focus (3 par cycle). Lit l'état de la todo list (`quest.v1`) et garde le sien dans `quest.game.v1`.
- `manifest.webmanifest`, `sw.js`, `icon-*.png` : ce qui la rend installable et utilisable hors ligne.

Les données restent dans le navigateur (localStorage). Une sauvegarde texte est disponible dans Réglages.

- `vendor/three.module.min.js` : Three.js r170 (licence MIT, voir `vendor/three-LICENSE.txt`), le moteur 3D, embarqué pour que le jeu marche hors ligne.
