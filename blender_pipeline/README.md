# BROWN — Blender CPU Prototype (Final Film Render Blocked)

**This folder currently contains a short procedural prototype, not the complete BROWN Book One film. It is not approved for final delivery.** The current scene is 90 seconds, uses block-built characters and a small rigid-weighted skeleton, and focuses on one vehicle ambush. It does not adapt all 72 chapters, provide the full cast, or deliver the required dialogue/action coverage. See [QUALITY_REBUILD_SPEC.md](QUALITY_REBUILD_SPEC.md) for the mandatory rebuild plan.

It does not generate images and does not need a GPU. Blender Cycles is explicitly configured for **CPU rendering**.

## Production settings

| Setting | Value |
|---|---:|
| Format | Vertical 9:16 |
| Resolution | 720 × 1280 |
| Frame rate | 30 FPS |
| Duration | 90 seconds |
| Frame count | 2,700 |
| Renderer | Blender Cycles |
| Device | CPU only |
| Samples | 128 with denoising |
| Video | H.264 / MP4 |
| Crew | Six characters in one vehicle |
| Pre-impact drive | 180 blocks by 20 seconds |
| Final approach | 188 blocks |
| Explosion | 43.5 seconds |

The values live in `brown_scene_config.json`. The scene-building code reads the render and scene settings from that file.

## What is built

- Six individual, consistently coloured characters: **Kesh, Amel, Kaylen, Biko, Tovin and Lark**. There is one crew vehicle; the old invented second vehicle and excess crowd are not used.
- Each character has a Blender armature, one unified skinned body mesh, named limb bones, vertex groups and an Armature modifier. There are exactly two eyes, two pupils, two brows, two ears, one nose and one mouth per character. Facial shape keys support blinking, mouth movement and brow expression.
- Kesh's hands use inverse-kinematics constraints connected to the physical steering wheel. The wheel turns with the drive motion.
- The vehicle has four rolling wheels, seats, windshield/side glass, dashboard, steering column, rear passenger door, lights, mirrors and collision/property metadata.
- Kaylen holds an actual three-dimensional smartphone. Its message is modelled as text on the handset's screen, not composited as a video caption.
- Lark reaches for and opens the passenger door. Characters have controlled reaction poses before the impact, then connected-rig impulse motion and damped joint movement through the blast.
- The blast has an expanding fireball, animated point light, dust, smoke, debris and a short camera jolt.
- Ten tracked cameras and timeline camera cuts provide chase, cabin, phone, approach, blast, wreckage, crawl and epilogue coverage.
- The same Kaylen rig appears in the closing forest scene.

The body parts are vertices in one rigged mesh per character, weighted to named bones. They are not independent floating character objects.

## Run the project

Install a current Blender release with the bundled glTF 2.0 exporter. Blender is open source. Run the commands from the repository root.

### 1. Audit and build the editable project

```bash
blender --background --python blender_pipeline/brown_scene_cpu.py -- --mode audit
```

This creates the scene, checks all 2,700 timeline frames for finite rig/vehicle transforms, validates the project settings and writes the editable `.blend`, the rigged `.glb` interchange file and an audit JSON report under:

```
output/brown_blender_cpu/
```

### 2. Render every frame

```bash
blender --background --python blender_pipeline/brown_scene_cpu.py -- --mode render
```

The render command writes every frame at the settings above and encodes the resulting MP4. It is a CPU-intensive render. Do not close the process while it is rendering. For a long render, use a desktop/workstation plugged into power with sufficient free RAM and disk space.

### 3. Open and edit

Open `output/brown_blender_cpu/BROWN_Book_One_Blender_CPU.blend` in Blender. The Outliner is organised into collections for character rigs, character meshes, vehicle, props, effects, cameras, lighting, environment and epilogue. Select a character armature and enter Pose Mode to adjust the skeleton; use the Timeline/Dope Sheet/Graph Editor to inspect and revise animation. Custom properties on the scene, characters, phone, vehicle and hitboxes describe their intended roles and settings.

The accompanying `BROWN_Book_One_Blender_CPU.glb` is an interchange export containing the model hierarchy, skins, materials, cameras and animation supported by glTF. It can be imported into compatible 3D applications. The editable `.blend` remains the authoritative project.

## GitHub Actions render

The repository contains a manually started workflow at **Actions → BROWN Blender CPU Production → Run workflow**. Select `audit` to build and validate the project, or `render` to run the full 2,700-frame CPU render. The job uploads the Blender project, GLB, audit report and MP4 as a workflow artifact.

The hosted runner has a fixed job-time limit. For a render that exceeds that limit, use the local Blender command above or configure a self-hosted GitHub Actions runner with adequate CPU, RAM and disk space.

## Important technical boundaries

- The browser version of FrameForge is a static website. A web page hosted on GitHub Pages cannot launch a native Blender process on a user's device. The BROWN production scene is therefore authored and rendered by Blender, with FrameForge linking to the pipeline and keeping the lightweight software renderer available for quick previews.
- The blast performance is a **connected, keyframed ragdoll-style impulse**: character roots follow ballistic trajectories and the rig joints receive damped rotational motion. It preserves the unified skinned body and avoids loose limbs. It is not a baked Bullet rigid-body ragdoll simulation. A real-time physical ragdoll solver would require an additional simulation-and-bake validation pass before being described as physics-driven.
- The script performs a structural and all-frame transform audit. That is not a substitute for visually reviewing rendered frames. The rendered MP4 must still be checked at the camera cuts and around the drive, phone message, door opening, blast, crawl and epilogue before publication.
- The provided audit has not been run in this chat because a native Blender process is not available in this execution environment. The workflow is supplied so the script can be run in Blender and any Blender-version/runtime errors can be caught there. No unrendered output is represented as a finished MP4.

## Files

- `brown_scene_cpu.py` — procedural scene, rigs, camera setup, animation, audit and render script.
- `brown_scene_config.json` — production settings and review requirements.
- `BROWN_Blender_CPU_Audit.json` — generated by the audit/build run.
- `BROWN_Book_One_Blender_CPU.blend` — editable native Blender project.
- `BROWN_Book_One_Blender_CPU.glb` — glTF interchange export.
- `BROWN_Book_One_Blender_CPU_90s.mp4` — 30 FPS H.264 render.

