

## Imported VFX-first workflow

Production VFX now prioritises externally authored assets with a verified free-use licence. The workflow imports the source footage at render time, records the creator and licence, and keeps the downloaded media outside the Git repository. It does not replace a requested professional VFX element with a hand-drawn Canvas imitation.

See [the imported VFX-first policy](docs/FF_V2_IMPORTED_VFX_POLICY.md), [the external VFX source manifest](assets/external-vfx-manifest.json), and the [FrameForge V2 Imported VFX Portrait Test workflow](.github/workflows/ff-v2-vfx-demo.yml).

For portrait effects, the production pipeline creates a genuine transparent subject cut-out first. Subject-only colour grading is applied to that alpha layer, while the original photograph remains a separate, ungraded background layer. The delivery artifact includes the transparent cut-out and credits/licence information.
