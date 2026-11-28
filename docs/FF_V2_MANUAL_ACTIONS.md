# FrameForge V2 manual GitHub Actions operations

**FrameForge V2 Manual Operations (Cost-Capped)** runs only after an explicit workflow dispatch. It has no schedule, push-triggered render, persistent worker or watchdog.

## Inputs and hard limits

- **validate** checks a V2 project JSON and media-rights manifest.
- **merge-export** accepts browser chunk ZIPs under render-input/, requires a matching project/job signature, caps chunk input at 100 MB and defaults to 240 frames (10 seconds at 24 FPS). The configurable maximum is hard-capped at 480 frames. Export is limited to a maximum of 921,600 pixels per frame (720p landscape or portrait) at 24/30 FPS.
- **qa-review-package** accepts a video under render-input/ up to 100 MB and 30 seconds, with each video dimension at or below 1280 pixels. Outputs are confined to artifacts/manual-ops/ and packaging stops when technical QA fails.
- Total output is capped at 100 MB. Workflow artifacts expire after three days.

## Operation

Prepare a small project and manifest in the repository, or place small chunk ZIPs or a short video under render-input/. Do not commit private project media to a public repository. Open GitHub Actions → **FrameForge V2 Manual Operations (Cost-Capped)** → **Run workflow**. Choose the operation and provide repository-relative paths. The helper rejects paths outside the checkout, render inputs outside render-input/ and outputs outside artifacts/manual-ops/. Failed validation, incomplete chunk sets, limit violations or failed QA do not create a delivery package.

## Cost and availability safeguards

Only standard GitHub-hosted Ubuntu CPU runners are used: no GPU, larger runner class, paid external API, alternate render fallback, schedule or automatic retry. Job timeout is 20 minutes and concurrency allows one active manual job. GitHub account/repository quota, availability, terms and artifact limits still apply; no workflow can guarantee an unlimited free allocation. If GitHub refuses or limits a run, the workflow does not switch to billable infrastructure. Larger jobs belong on a local computer with Python and FFmpeg.

The pilot workflow is separately scoped to the two short demos and uses the same standard CPU runner policy, 20-minute timeout and three-day artifact retention.
