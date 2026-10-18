"""Show safe provider configuration and optionally test a real photograph.

No keys, raw prompts, encoded photographs or provider response bodies are printed.
Run with the project's Python environment: python scripts/check_vision.py
An explicit --image sends that file to configured provider(s); omit for no calls.
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))
from app.vision import analyze_image_file, provider_status

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--image', type=Path, help='Non-sensitive JPEG, PNG or WebP for a real configured-provider call')
args = parser.parse_args()
output = {'configuration': provider_status()}
if args.image:
    result = analyze_image_file(args.image)
    # Deliberately print only verification metadata and actionable safe errors.
    output['image_request'] = {key: result.get(key) for key in ('provider', 'model', 'status', 'image_analyzed', 'relevance', 'attempts', 'errors', 'analyzed_at')}
print(json.dumps(output, indent=2, ensure_ascii=False))
if args.image and not result['image_analyzed']:
    raise SystemExit(1)
