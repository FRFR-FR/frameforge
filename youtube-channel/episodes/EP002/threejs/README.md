# EP002 Three.js visual master

ep002_threejs_master.mjs is an original, self-contained Three.js scene module for the supplied Offline Three.js MP4 Studio.

## What is in it

Ten original animated conceptual scenes mapped to the ten narration sections. The first scene is a close cinematic tin-droplet / laser / plasma / EUV sequence. Other scenes explain chip layers, DUV vs EUV, the tin source, multilayer mirrors and vacuum, reticle projection, wafer-stage metrology, the process cycle, High-NA optics and the system ecosystem.

All geometry is generated procedurally in Three.js. It does not download, embed or reuse stock images, stock video, textures, or external models.

## Converter contract

The module:
- imports only three (the supplied converter rewrites this import to its embedded Three.js r175 engine)
- exports mountScene(container, options)
- returns seek(t), resize(w,h), pause() and dispose()
- renders a deterministic frame for every seek time, as required for frame-by-frame export
- accepts output width, height and duration from the converter

Set the converter duration to the measured narration runtime. Default in this module is 699.25 seconds (11:39.25), corresponding to the existing EP002 Echo narration. It allocates ten scene durations using approximate section weights; replace those weights with exact measured Kokoro section durations before final master rendering.

## Required converter adjustment

The uploaded MP4 Studio HTML does not currently offer the required landscape 1280×720 option. Its resolution menu offers vertical 720×1280 and several 1080p choices instead. Before release rendering, patch the menu to include 1280×720 landscape and remove/disable all options above 720p.

## Important

This is a ready-to-render visual scene source, not a rendered MP4. The full episode must still be rendered, combined with the approved Kokoro WAV, SRT captions, chapter labels and channel bug, then checked through ffprobe, complete decoding, frame review and freeze/repeated-shot QC. A 100% 3D-only preview is not automatically a release candidate because the separate relevant-B-roll minimum still applies.
