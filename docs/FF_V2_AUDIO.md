# FrameForge V2 audio production

The V2 audio engine adds non-destructive, project-backed audio editing without flattening audio into the visual compositor. It is loaded from `ff-v2-audio.js` and keeps project files at schema version 2.

## Audio tracks and clips

The default sequence includes separate Voiceover, Music and Sound effects tracks. Add an `Audio` track for dialogue, ambience or another independent stem. Import supported audio files in the V2 Assets panel, choose the destination audio track, and select **Add to timeline**.

Track controls support gain, pan, solo, mute and enable/disable. Select an audio clip to expose its decoded waveform, clip gain, pan, mute, fade-in and fade-out controls. The clip's standard V2 start/duration/split controls continue to work, and splitting preserves the source offset. Audio placement and fades use sequence frames; project output uses the configured sample rate (48 kHz by default).

## Waveform and playhead sync

Selecting an audio clip decodes its local asset through the Web Audio API and draws a peak waveform. Tapping/clicking the waveform seeks the shared timeline playhead in frame units. While a rendered mix is previewed, the playhead follows the audio player's current time.

## SFX event cues

The SFX cue editor can place an imported audio asset at the current playhead or attach it to the start/end of a selected visual clip. Cue references are stored in the `extensions.ffv2_audio.cues` project extension and resolve against clip IDs, so moving or trimming a visual clip moves its associated cue event.

## Mixing and automation

Clip gain automation is stored as clip-local frame/gain keyframes and interpolates linearly. Track and clip gain, stereo balance, fades, mute/solo, and optional voiceover-triggered music ducking are evaluated when the master is rendered. The master pass performs a peak scan, applies bounded normalization toward -1 dBFS, and exports a stereo PCM16 WAV.

The **Preview mix** button renders the project audio master, loads it in the local audio player, and synchronizes the project playhead. It is an offline mix-then-preview path, not a live low-latency mixer. Browser AudioContext support and memory/CPU vary by device. The current in-browser master renderer limits projects to 10 minutes by default and checks the PCM WAV 4 GB limit.

## WAV master and FFmpeg mux

Use **Render WAV master** to create/download the project audio. At 48 kHz stereo PCM16, the uncompressed master is approximately 11.52 MB per minute, before the 44-byte WAV header.

The V2 compositor currently renders the selected frame to PNG; it does not yet render a full timeline to MP4. To combine a silent video created by an existing renderer with the WAV master, install FFmpeg and run:

```bash
python tools/mux_ffmpeg.py --video silent-picture.mp4 --audio project-audio-master.wav --output finished.mp4
```

The utility uses the picture's measured duration, maps only its video stream and the supplied WAV, pads/trims audio to the picture duration, targets -16 LUFS integrated loudness and -1.5 dBTP true peak, encodes AAC at 48 kHz stereo, and probes the output to verify both streams and duration. It copies a compatible video stream by default. For legacy WebM/VP9 or another video codec that is not suitable for MP4, choose:

```bash
python tools/mux_ffmpeg.py --video silent-picture.webm --audio project-audio-master.wav --output finished.mp4 --video-codec libx264
```

The full V2 sequence-to-video render and automatic final mux are **not** complete; they depend on the later full-sequence rendering/export roadmap. The mux utility is a tested handoff for an already-rendered silent picture file.

## Project and media portability

Track/clip audio controls and event cues are serialized in V2 project JSON. Imported binary audio files remain in the originating browser's IndexedDB, just like other V2 imported media; keep the source audio files backed up separately when transferring a project to another device.
