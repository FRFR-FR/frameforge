# Optional local developer toolchain

**This folder is not required to use GAMEFORGE.** The supported end-user workflow runs on GitHub-hosted runners; see [gameforge/README.md](../gameforge/README.md) and the [GAMEFORGE GitHub Cloud Pipeline](https://github.com/FRFR-FR/frameforge/actions/workflows/gameforge-cloud.yml).

The Windows and Linux installers in this folder are optional convenience scripts for contributors who deliberately want a local development environment. They do not install anything on GitHub, and running them is not part of the cloud build process.

The cloud workflow provisions the tools it needs inside disposable GitHub-hosted jobs. Model weights are cached by GitHub Actions where possible and are not committed to the repository. Speech generation is an opt-in workflow stage because individual voice sources can have different licensing terms; review `gameforge/cutscenes/VOICE_LICENSES.md` first.
