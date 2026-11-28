

## 22. Imported VFX-first production path

For production-quality effects, the default is to import externally authored VFX footage or assets rather than drawing fire, particles, rings, smoke or similar effects in the repository's Canvas renderer. See the imported VFX-first policy in [FF_V2_IMPORTED_VFX_POLICY.md](FF_V2_IMPORTED_VFX_POLICY.md).

The revised 10-second portrait demonstration uses:
- A BiRefNet portrait segmentation pass to create a genuine transparent PNG cut-out.
- The original photograph as a separate background layer.
- A red grade and animated opacity applied only to the transparent subject layer. The photograph background is not red-tinted.
- An externally downloaded EmberGen fire-simulation overlay from Pixabay, composited as a real video layer. No repository-authored fire, ember or burst effect is used in this test.
- Source/licence records and the transparent cut-out in the delivery artifact.

The external video binary is downloaded at render time and is not committed to GitHub. The Pixabay API key is read from the `PIXABAY_API_KEY` Actions secret and is never written to the repository or output metadata. The selected source is listed in [assets/external-vfx-manifest.json](../assets/external-vfx-manifest.json).

Do not use a Mixkit item whose individual page shows the Restricted License for monetised or commercial work. The individual asset licence, not only the provider's general free-stock page, determines whether it is suitable.
