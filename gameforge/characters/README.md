# GAMEFORGE — Loomglass 10-character generation test

This is an isolated character-generation lab for the `gameforge-engine-foundation` project. It uses the repository's native **Blender CPU** workflow and adds no dependency to the game's runtime or export builds.

## Visual direction: Loomglass

Loomglass is a new art-direction experiment made for GAMEFORGE: rounded sculptural body masses are interrupted by folded, chamfered ceramic planes; satin-metal fittings and emissive inlay seams trace each silhouette; expressive glassy eyes and asymmetric crown/mantle signatures distinguish the cast. The result aims for a tactile, collectible-fantasy look rather than a generic low-poly or realistic human style.

The visual system is an original combination developed for this project. It is not possible to prove that no other 3D game has ever used a similar visual idea, so this is not presented as a historical first.

## Cast

| Character | Role | Shape signature |
|---|---|---|
| Aster | Wayfinder | orbit halo and swept compass crest |
| Bront | Oathkeeper | paired horns, shield gorget and furnace heart |
| Nyx | Verdantist | leaf crown, vine arc and folded leaf mantle |
| Pika | Spark-runner | comet plume and diagonal runner sash |
| Orin | Memory-keeper | archive aureole, visor and book clasp |
| Sola | Cloud courier | split sky-wings and wind collar |
| Vey | Forge-singer | asymmetrical forge pauldron and hammer prop |
| Luma | Tidecaller | tidal circlet and layered fin mantle |
| Koro | Dusk ranger | shadow hood, crescent ring and bow silhouette |
| Miri | Seed-tender | seven-petal crest and seed charms |

## Build and review

```bash
blender --background --factory-startup --python-exit-code 1 \
  --python gameforge/characters/build_character_test.py -- \
  --output-dir output/gameforge_character_test --samples 48
```

The generator produces ten standalone skinned GLB actors, an editable Blender gallery, ten individual 1280×720 previews, a 1280×720 lineup image, and an automated audit report. All meshes are procedurally built in Blender; no AI image generation or external character models are used.

Each actor has a 17-bone humanoid rig, one unified weighted mesh, a short idle animation clip, authored materials, and GAMEFORGE metadata. The preview renders use Cycles CPU rendering and denoising.

The GitHub Actions workflow is restricted to this branch and this character-lab path. It does not invoke GAMEFORGE Android or Windows exports.
