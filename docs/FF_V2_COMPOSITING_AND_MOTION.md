# FrameForge V2 — compositing and motion graphics (steps 11–15)

This phase connects the V2 multi-track project model to a real browser-native frame compositor. It extends the existing V2 project schema; it does not replace the legacy drawing editor or change the project's schema version.

## Open the workspace

Open the FrameForge app and select **V2 Assets**. Add imported visual assets to the V2 timeline, then select a clip to open its editor. The **V2 Layer Compositor** is below the timeline. It renders the current playhead frame at the main sequence's exact dimensions. The default sequence is 1280 × 720.

## 11. Layer compositing and alpha

- Enabled visual tracks are drawn in ascending track order: the lowest order is the bottom layer and the highest order is drawn last.
- Disabled tracks and clips are excluded. Audio, music, SFX and voiceover tracks are not visual layers.
- Each visual layer is drawn to an isolated transparent offscreen surface, then masked and composited into the output canvas.
- The output is cleared to transparent before every render. Canvas 2D handles the browser's premultiplied-alpha compositing; the renderer does not flatten transparency to black or white.
- Imported raster images, SVG assets and browser-decodable video frames can be resolved from the local IndexedDB asset library.
- **Render frame** re-renders the current playhead. **Download PNG** exports that single frame at the sequence dimensions, with transparency preserved.

The output is deterministic for a fixed project, frame, asset bytes and browser decoding result. Video codec/decoder behaviour can vary by device/browser.

## 12. Transforms, crop and anchor

Select a visual clip to edit:

| Property | Meaning |
|---|---|
| Position X / Y | Pixel offsets from the sequence centre |
| Scale X / Y | Multipliers applied to the layer |
| Rotation | Degrees clockwise |
| Opacity | 0 to 1 |
| Anchor X / Y | Normalized anchor point; 0 is the leading edge, 0.5 is the centre, 1 is the trailing edge |
| Fit | contain preserves the whole source; cover fills the frame and may extend beyond it; stretch fills the frame without preserving aspect ratio |
| Crop | Optional normalized source rectangle with X, Y, width and height values from 0 to 1 |

The same transform evaluation is used for preview frames and for the frame compositor. Transform values are stored on the clip, not baked into the original imported asset.

## 13. Keyframes, easing and parenting

Keyframes are stored in clip-local frame coordinates. The editor converts the global playhead frame into local clip time when adding a keyframe. Re-applying the same property at the same frame replaces that keyframe.

Currently keyframable transform properties are position X/Y, scale X/Y, rotation, opacity and anchor X/Y. Interpolation options are hold/step, linear, ease-in, ease-out, smooth ease-in/out and cubic Bezier. Bezier controls are represented as [x1, y1, x2, y2].

A visual clip can inherit a parent clip's position, scale, rotation and opacity. Audio clips cannot be parents. Self-parenting and parent cycles are rejected.

## 14. Masks, mattes and blend modes

- **Shape masks:** rectangle or ellipse, with optional feathering and inversion.
- **Alpha matte:** uses the source asset's alpha channel.
- **Luma matte:** converts matte RGB values to luminance and uses the resulting luminance as alpha.
- **Feather:** softens the mask edge in output pixels.
- **Blend modes:** normal, multiply, screen, overlay, darken, lighten, color dodge/burn, hard/soft light, difference, exclusion, hue, saturation, color, luminosity, additive and behind.

Matte sources must be imported image/graphic assets. Shape-mask bounds are normalized to the output sequence canvas (not to source-image pixels). If a browser cannot provide pixel access for a luma matte, the renderer reports a warning and does not silently substitute a different matte mode. Unsupported blend modes fall back to normal compositing.

## 15. Typography, SVG and shape graphics

Use **＋ Title**, **＋ Lower third**, **＋ Shape** or **＋ SVG** in the compositor toolbar. These create editable generated clips on the Titles or Graphics track.

- Text includes content, browser font family, font size, colour and optional CSS colour background. Use line breaks to control multiple lines.
- Vector shapes include rectangles, ellipses, lines and polygons.
- Inline SVG is rendered as a vector source and is checked before use. Scripts, event handlers, foreignObject, embedded objects and external resources/references are rejected.
- Generated clips use the same transform, keyframe, parent, mask and blend pipeline as imported image layers.

Fonts are resolved from the fonts available to the browser/device; this phase does not bundle font files. Text remains vector-like Canvas text during rendering and is rasterized only into the requested compositor frame.

## Tests and verification

The V2 Foundation Validation workflow checks JavaScript syntax, 23 Node tests, 14 Python regression tests, the JSON schemas and both example validators.

The Chromium browser smoke test imports a generated PNG, exercises the multi-track editor and local persistence, then verifies:
- a 1280 × 720 frame is drawn,
- a generated shape is composited over an imported image,
- unused canvas pixels retain alpha 0,
- transform controls and a keyframe can be applied,
- a feathered ellipse mask and its inverted form change the composited pixels.

See the current CI links in [FF_V2_PROGRESS.md](FF_V2_PROGRESS.md).

## Boundaries and later work

This is a **single-frame compositor and PNG-frame export**, not the final video renderer. It does not yet create an MP4 or render an entire sequence automatically. The separate FFmpeg/resumable-render phases (steps 41–43) remain outstanding.

Other limitations:
- Canvas 2D is used for this phase; a GPU/WebGL shader framework is a later step.
- Video preview seeks a browser-decoded frame at the current sequence time; there is no real-time V2 audio/video playback engine yet.
- 3D model/scene tracks are represented in the project format but are not yet rendered by this 2D compositor.
- Keyframes currently cover transforms, not arbitrary effect or audio parameters.
- Matte bounds are sequence-relative. More advanced vector/path masks and tracked masks are future enhancements.
- Browser font availability, video codecs, Canvas filter support, memory and storage quotas vary by device. Large sequences can be expensive on a phone.
- Project JSON still does not package imported binary files; keep separate backups of source media.

No paid APIs, paid rendering services, paid stock libraries, remote font providers or image-generation services are required for this phase.
