# EP001 output files

The final MP4 and thumbnail are kept out of normal Git history. The MP4 is supplied as a separate download in the daily report and can also be uploaded as a GitHub Actions artifact after the runner completes.

Current pilot metadata is recorded in `render_report.json`. The current caption track is archived as `captions.srt.gz.b64`; restore it with:

```bash
base64 -d captions.srt.gz.b64 | gzip -d > captions.srt
```

No 1080p or 4K export is allowed.