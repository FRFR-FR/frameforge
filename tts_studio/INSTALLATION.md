# Installing the TTS engines

These files add reproducible package-install commands to the FrameForge repository.

## F5-TTS

Use Python 3.10 or newer. Install a PyTorch/torchaudio build that matches the machine's CPU/GPU first, then run:

```bash
bash tts_studio/install_f5_tts.sh
```

Or install from the manifest:

```bash
python -m pip install -r tts_studio/requirements-f5.txt
```

The official v1 Base checkpoint is downloaded by the F5-TTS package when inference is run. Its model card lists the checkpoint under the F5-TTS Hugging Face repository. Check the current upstream license and usage terms before commercial use.

## Orpheus TTS

The official vLLM inference path normally requires a compatible CUDA GPU. Run:

```bash
bash tts_studio/install_orpheus.sh
```

Or install from the manifest:

```bash
python -m pip install -r tts_studio/requirements-orpheus.txt
```

The English production checkpoint is downloaded from Hugging Face at runtime.

## Why the weights are not committed here

GitHub repositories are for source and configuration. Model checkpoints are large binary artifacts, may have separate license terms, and should be fetched from their official model hosts. The Colab notebooks in this folder install the packages and download the checkpoints in the temporary runtime. GitHub does not run or permanently host those model processes.

## Free Colab option

Open the notebooks linked in [README.md](README.md). They install the packages in a Colab session, download model weights when needed, and create audio files there. Free GPU access is subject to Colab availability and limits.
