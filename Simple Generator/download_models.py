from pathlib import Path

from huggingface_hub import snapshot_download

models = Path(__file__).resolve().parent / "models"
assets = [
    ("stable-diffusion-v1-5/stable-diffusion-v1-5", "sd15",
     ["model_index.json", "text_encoder/config.json", "unet/config.json", "vae/config.json",
      "scheduler/*.json", "tokenizer/*"]),
    ("lllyasviel/sd-controlnet-canny", "controlnet-canny",
     ["config.json", "diffusion_pytorch_model.safetensors"]),
    ("Helsinki-NLP/opus-mt-zh-en", "translate",
     ["*.json", "*.spm", "pytorch_model.bin"]),
]
for repo, folder, files in assets:
    snapshot_download(repo_id=repo, local_dir=models / folder, allow_patterns=files)
