# Personnages Mixamo → glTF léger

1. `python3 fbx6glb.py "Perso.fbx" sortie.glb 1024` : FBX 6.1 Mixamo (mesh, squelette, skin, texture diffuse réduite) vers GLB.
   Les FBX 7.x (modèles « Ch… ») passent par le FBXLoader de three.js puis GLTFExporter.
2. `python3 anim7.py clips.glb idle="sword and shield idle.fbx" walk=... ` : cuit les animations FBX 7.x en un seul GLB de clips,
   partagé par tous les personnages (mêmes noms d'os `mixamorig:*`).
3. `gltf-transform optimize in.glb out.glb --compress meshopt --texture-compress webp --texture-size 512 --flatten false`
   (ajouter `--simplify true --simplify-ratio 0.2` pour les modèles lourds).

Le jeu adapte la hauteur des hanches à chaque personnage et met marche et course sur place (`persoClips` dans jeu.html).
