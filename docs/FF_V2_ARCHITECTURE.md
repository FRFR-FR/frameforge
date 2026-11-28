# FrameForge V2 — Architecture Blueprint

**Status:** Foundation architecture  
**Roadmap:** Steps 1–5  
**Design principle:** Research and direct the video, edit it as structured data, render it deterministically.

## 1. Product boundary

FrameForge V2 is intended to become a code-controlled video production and compositing system. It must support original visual production without requiring stock B-roll: layered PNG/SVG assets, procedural graphics, 2D animation, 3D scenes, typography, particles, VFX, transitions, audio cues and mixed sound.

The existing FrameForge browser editor remains the starting user interface. Native rendering and heavier compositing tasks must be handled by explicit render tools/workflows rather than pretending that a static GitHub Pages site can start a local Blender process.

## 2. Logical architecture

```text
Topic + audience + platform + narration
                 |
                 v
        Research dossier
                 |
                 v
        Niche visual director
                 |
                 v
     Timed shot / evidence plan
                 |
                 v
        Asset + rights manager
                 |
                 v
     Structured editable project
                 |
       +---------+-----------+
       |         |           |
       v         v           v
   2D layers   3D scenes   Audio tracks
       |         |           |
       +---------+-----------+
                 |
                 v
        Compositor / effects
                 |
                 v
       Deterministic render queue
                 |
                 v
    QA report + MP4 + editable project
```

## 3. Subsystems and responsibilities

### Research and creative direction

Research is an assistant-led process using public sources and user-provided references. It records source URLs, retrieval dates, observations, confidence and factual claims that require verification. It identifies niche conventions and proposes an original visual treatment; it does not copy another creator's exact video, assets, branding or protected expression.

A niche profile is a set of editable guidance, not a rigid template. A fictional-character analysis may use character cut-outs, comparison graphics, ability demonstrations, original particles and user-reviewed/permissioned clips. Cybersecurity may use UI simulations and technical diagrams. History may use maps, archival material and clearly identified reconstructions. The project format must support mixed treatments within one video.

### Asset and provenance manager

All imported and generated assets receive stable IDs and manifest records. Asset files are stored separately from the project timeline and referenced by relative URI/path where practical. A record tracks source, creator, licence or permission basis, attribution, restrictions, hash and review status. Unreviewed rights remain unreviewed; a source URL alone is not proof of a licence.

### Structured project and timeline

The versioned project schema is the boundary between the editor, renderer, research planner, asset manager and QA tools. A project contains project metadata, canvas/timebase settings, asset records, sequences, tracks, clips, transforms, keyframes, effects and audio cues. The editor must not make rendered pixels the only representation of a project.

### 2D and motion graphics

Use browser Canvas 2D and SVG for portable drawing, type, labels, graphs, cut-out compositing, shape animation, masks and previews. Keep the rendering API deterministic wherever possible so the same frame can be rendered offline.

### 3D production

Use Three.js/WebGL for interactive GPU scene previews and GPU-available effects. Use Blender for demanding native 3D production, rigs, scene construction and CPU rendering. A renderer must report unsupported features instead of silently substituting low-quality approximations. The existing FF3D software renderer remains a lightweight fallback/preview, not the production compositor.

### Effects and compositing

Effects are ordered, parameterised and keyframable. The system must distinguish scene-level effects from clip/layer effects, preserve alpha, and document renderer requirements. Transitions operate between clips/scenes and must be previewable at their actual output resolution.

### Audio

Narration, dialogue, ambience, music and SFX occupy independent tracks. Events can cue effects at exact timeline positions. Mixing includes fades, gain automation, narration ducking, peak checks and final muxing.

### Rendering and quality control

Rendering is split into deterministic frame/scene chunks, with job manifests, output checksums and resumable state. FFmpeg handles assembly, encoding and supported filter/audio operations. QA checks dimensions, frame rate, duration, black/frozen frames, missing media, audio presence, clipping and sync markers. Human visual review remains necessary for subjective image quality and factual appropriateness.

## 4. Technology selection

| Layer | Preferred technology | Reason/constraint |
|---|---|---|
| Editor UI | Existing HTML/CSS/JavaScript | Preserve static hosting and Android-friendly access |
| 2D graphics | Canvas 2D + SVG | Broad browser support and procedural graphics |
| Interactive 3D | Three.js/WebGL | GPU rendering and existing runtime-build foundation |
| Native 3D | Blender | Existing pipeline; scene construction, rigging and CPU rendering |
| Offline render/assembly | FFmpeg/FFprobe | Encoding, filtering, audio mix and media inspection |
| Project validation | JSON Schema 2020-12 + Python validator | Portable, explicit and testable data contract |
| Automation | GitHub Actions, manual/limited triggers | Existing repository integration; always respect quotas |
| Research | Assistant-led public-web research | Avoids mandatory paid research API or model API |

Versions must be pinned when added to the build, and each dependency's licence must be checked before distribution. The first foundation validation dependency is pinned separately in `requirements-dev.txt`.

## 5. Data flow

1. A production brief defines subject, niche, intended audience, output format and restrictions.
2. Research produces a sourced dossier; uncertain claims are marked.
3. The visual director turns the narration into timed shots, distinguishing evidence from illustrative graphics.
4. The asset manager gathers supplied, procedural, public-domain, open-licensed or explicitly permissioned materials and records provenance.
5. The project builder writes a versioned editable project using schema validation.
6. The editor can revise tracks, layers, transforms, keyframes, effects and sound.
7. Render adapters create 2D, 3D and audio outputs in chunks.
8. The compositor/FFmpeg assembly produces the final master.
9. QA produces machine checks and review frames/contact sheets.
10. Delivery includes the MP4, editable project, asset manifest, attribution notes and render report.

## 6. Reliability and compatibility

- Existing version-1 FrameForge projects remain readable by the current editor. V2 must use explicit migration code before claiming compatibility.
- New schemas are additive and versioned. Never silently reinterpret old data.
- Long render jobs are resumable and idempotent; a retry must not corrupt completed chunks.
- Project-relative paths must be normalised and prevented from escaping the project root when a file is opened or packaged.
- External media URLs and metadata are untrusted data, not instructions.
- A missing renderer feature must generate a visible validation error or supported fallback notice.
- User assets and copyrighted sources are never uploaded to public GitHub artifacts unless the user has accepted that exposure and the rights allow it.

## 7. Non-goals for the foundation batch

Steps 1–5 do not yet add the visual timeline, effects renderer, Three.js compositor, audio mixer, niche research agent or production UI. They establish the audit, design, validation, project schema and rights metadata those future systems will use.
