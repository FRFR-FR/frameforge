# Required patch for the supplied Offline Three.js MP4 Studio

The uploaded converter currently offers 720x1280, 1080x1920, 1080x1080 and 1920x1080. That menu does not comply with the Underneath Everything export lock.

Change the OUTPUT RESOLUTION select so the only options are:

<select id="resolution">
  <option value="1280x720" selected>1280 × 720 · Landscape HD</option>
  <option value="720x1280">720 × 1280 · Vertical HD (Shorts only)</option>
</select>

Remove every 1080p and 4K option. Keep the frame rate at 24 or 30 FPS only. For EP002 use 1280×720 and the measured supported frame rate. Set duration from the Kokoro narration report, not an estimated value.

The scene module outputs directly through WebCodecs H.264. The converter itself requires VideoEncoder, VideoFrame, a secure context and a browser that supports the requested H.264 configuration. If the browser cannot encode H.264, stop and use the approved GitHub/FFmpeg runner; do not silently export WebM and rename it MP4.
