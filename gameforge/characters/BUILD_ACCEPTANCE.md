# GAMEFORGE character lab — build acceptance

This branch runs the isolated Loomglass character-generation build for the GAMEFORGE engine.

## Build deliverables
- Ten original procedural characters with distinct silhouettes and materials.
- One editable Blender gallery project.
- Ten skinned GLB exports with humanoid armatures and idle animation.
- Ten individual 1280×720 preview renders and one 1280×720 gallery render.
- A machine-readable audit rejecting missing rigs, meshes, skin weights, animations, GLBs or previews.

## Scope boundary
This is the first character-generation production gate, not a claim that the entire character system is finished. Runtime retargeting, locomotion libraries, facial-expression authoring and in-game animation QA remain follow-on integration work. The branch is intentionally isolated from the engine foundation so the build can be inspected without changing game runtime or export settings.
