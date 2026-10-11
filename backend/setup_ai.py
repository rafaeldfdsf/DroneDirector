"""Download pinned model weights once; video inference itself is completely offline."""
import json
import logging
import time
import urllib.request
from pathlib import Path

import config
from services.ai_scorer import (CLIP_REVISION, HEAD_FILENAME, HEAD_SHA256, HEAD_URL,
                                LAION_REVISION, MODEL_NAME, VISION_FILENAME,
                                VISION_SHA256, VISION_URL, LocalAestheticScorer, file_sha256)


def download_verified(url: str, destination: Path, digest: str) -> None:
    if destination.is_file() and file_sha256(destination) == digest:
        print(f'Já instalado: {destination.name}', flush=True)
        return
    partial = destination.with_suffix(destination.suffix + '.part')
    for attempt in range(3):
        try:
            request = urllib.request.Request(url, headers={'User-Agent': 'DroneDirector-local-setup/0.2'})
            with urllib.request.urlopen(request, timeout=60) as response, partial.open('wb') as output:
                received = 0
                last_report = time.monotonic()
                while chunk := response.read(1024 * 1024):
                    output.write(chunk)
                    received += len(chunk)
                    if time.monotonic() - last_report > 3:
                        print(f'{destination.name}: {received / 1024**2:.1f} MB recebidos', flush=True)
                        last_report = time.monotonic()
            if file_sha256(partial) != digest:
                raise ValueError('O download não passou a verificação SHA-256.')
            partial.replace(destination)
            print(f'Instalado e verificado: {destination.name}', flush=True)
            return
        except Exception:
            partial.unlink(missing_ok=True)
            if attempt == 2:
                raise
            print('O download falhou. A tentar novamente…', flush=True)


def main() -> None:
    config.AI_MODELS_DIR.mkdir(parents=True, exist_ok=True)
    download_verified(VISION_URL, config.AI_MODELS_DIR / VISION_FILENAME, VISION_SHA256)
    download_verified(HEAD_URL, config.AI_MODELS_DIR / HEAD_FILENAME, HEAD_SHA256)
    # Validate model load before declaring the installation ready.
    LocalAestheticScorer(config.AI_MODELS_DIR)
    from services.prompt_scorer import PROMPT_FILES, PROMPT_MODEL, PROMPT_REVISION, prompt_directory, LocalPromptScorer
    for name, digest in PROMPT_FILES.items():
        destination = prompt_directory() / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        download_verified(f'https://huggingface.co/{PROMPT_MODEL}/resolve/{PROMPT_REVISION}/{name}', destination, digest)
    LocalPromptScorer(prompt_directory()).encode('Um rio rodeado de vegetação')
    (config.AI_MODELS_DIR / 'manifest.json').write_text(json.dumps({
        'model': MODEL_NAME, 'clipRevision': CLIP_REVISION, 'aestheticRevision': LAION_REVISION,
        'visionSha256': VISION_SHA256, 'headSha256': HEAD_SHA256,
        'sourceUrls': [VISION_URL, HEAD_URL], 'inference': 'local CPU, no network'}, indent=2), encoding='utf-8')
    print('IA local pronta. Os vídeos e frames nunca são enviados para estes servidores.', flush=True)


if __name__ == '__main__':
    try:
        main()
    except Exception:
        logging.exception('Não foi possível instalar o modelo de IA local.')
        raise SystemExit(1)
