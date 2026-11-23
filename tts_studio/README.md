# FrameForge TTS Studio

Free, Colab-first setup for trying **F5-TTS** and **Orpheus TTS** from this repository. This adds a separate `tts_studio/` folder; it does not change FrameForge's animation engine or existing render workflows.

## Important: where installation happens

GitHub is source-code hosting, not a free always-on GPU machine. The notebooks below install the model packages into a **free Google Colab runtime** when you run them. Select **Runtime → Change runtime type → T4 GPU** if that option is available. Free GPU availability and session limits are controlled by Google and are not guaranteed. Model weights are downloaded at runtime and are not committed to this repository.

## Quick start (Android-friendly)

1. Open one of the notebooks below in Colab.
2. Tap **Connect** and choose a GPU runtime if available.
3. Run the cells from top to bottom.
4. Upload a short, clean WAV reference recording when prompted by the F5-TTS notebook. Use audio you have permission to use. F5-TTS uses the reference audio and its exact transcript to condition the voice.
5. In Orpheus, choose an included English speaker such as `tara`, `leah`, or `leo`.
6. Download the generated WAV or MP3 from the final cell.

## Notebooks

- [F5-TTS — F5-TTS v1 Base (English)](https://colab.research.google.com/github/FRFR-FR/frameforge/blob/main/tts_studio/f5_tts_colab.ipynb)
- [Orpheus — English Finetuned Production](https://colab.research.google.com/github/FRFR-FR/frameforge/blob/main/tts_studio/orpheus_colab.ipynb)

Both notebooks use the same short comparison script so you can listen to the voices side by side.

## Model choices

- **F5-TTS:** official `F5TTS_v1_Base` model. It is a strong general-purpose multilingual-capable base model; the notebook conditions generation on a reference voice clip and transcript.
- **Orpheus:** official `canopylabs/orpheus-tts-0.1-finetune-prod` English production fine-tune. The notebook uses the official Python package and a selectable built-in English speaker.

## Free-runtime limitations

- These models are large. They may take several minutes to install and download, and generation may fail if the free runtime has insufficient GPU memory or is not assigned a GPU.
- Colab sessions can disconnect and free GPU access is not guaranteed.
- No paid API, API key, Runway, or AI image-generation service is used.
- This repository contains setup notebooks, not the model weights or generated example recordings. No audio has been rendered merely by committing these files.

## Official project references

- [F5-TTS source and documentation](https://github.com/SWivid/F5-TTS)
- [F5-TTS v1 Base model](https://huggingface.co/SWivid/F5-TTS)
- [Orpheus TTS source and documentation](https://github.com/canopyai/Orpheus-TTS)
- [Orpheus English production model](https://huggingface.co/canopylabs/orpheus-tts-0.1-finetune-prod)

## Usage and rights

Follow each model's current license and model-card terms. Only upload voice recordings you own or are authorized to use. Do not impersonate someone or publish generated speech in a misleading way.
