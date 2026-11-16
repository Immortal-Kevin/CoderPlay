# Pixel watermark verification. No metadata is consulted.
import sys,json
from pathlib import Path
from PIL import Image
from finalize import detect
manifest=json.loads((Path(__file__).parent/'watermark_manifest.json').read_text(encoding='utf-8'))
result=detect(Image.open(sys.argv[1]),manifest)
print(json.dumps(result,ensure_ascii=False,indent=2))
sys.exit(0 if result['payload_match'] and result['crc_pass'] else 1)
