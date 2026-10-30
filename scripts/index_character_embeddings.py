"""Incrementally embed mechanical passages through the standard (non-Batch-job) API."""

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'web'))
from rag_index import DIMENSIONS, EMBEDDING_MODEL, make_documents, quantize


def main():
    """Require explicit free-tier confirmation and checkpoint every successful request."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--confirm-free-tier', action='store_true')
    parser.add_argument('--limit', type=int, default=1000)
    parser.add_argument('--batch-size', type=int, default=40)
    parser.add_argument('--pause-seconds', type=int, default=35,
                        help='Explicit pacing between requests; no automatic error retries')
    args = parser.parse_args()
    if not args.confirm_free_tier:
        raise SystemExit('Confirm the local key belongs to the free-tier project before calling Google.')
    if not 1 <= args.batch_size <= 50 or args.limit < 1 or not 0 <= args.pause_seconds <= 60:
        raise SystemExit('Invalid limits')
    from dotenv import dotenv_values
    key = dotenv_values(ROOT / '.env').get('GEMINI_API_KEY')
    if not key:
        raise SystemExit('GEMINI_API_KEY missing locally')
    characters = json.loads((ROOT / 'web/public/data/characters.json').read_text(encoding='utf-8'))
    documents = make_documents(characters)
    path = ROOT / 'web/rag/embeddings.json'
    stored = json.loads(path.read_text(encoding='utf-8')) if path.exists() else {
        'model': EMBEDDING_MODEL, 'dimensions': DIMENSIONS, 'vectors': {}}
    if stored['model'] != EMBEDDING_MODEL or stored['dimensions'] != DIMENSIONS:
        raise SystemExit('Incompatible existing index; do not mix embedding spaces.')
    pending = list({d['hash']: d for d in documents if d.get('embeddingRequired',True) and d['hash'] not in stored['vectors']}.values())[:args.limit]
    print(f'{len(documents)} passages; {len(pending)} uncached passages to embed.', flush=True)
    for start in range(0, len(pending), args.batch_size):
        if start and args.pause_seconds:
            print(f'Pacing: waiting {args.pause_seconds}s before the next batch.', flush=True)
            time.sleep(args.pause_seconds)
        batch = pending[start:start+args.batch_size]
        payload = {'requests': [{'model': f'models/{EMBEDDING_MODEL}', 'taskType': 'RETRIEVAL_DOCUMENT',
            'title': d['title'], 'outputDimensionality': DIMENSIONS,
            'content': {'parts': [{'text': d['text'][:6000]}]}} for d in batch]}
        request = urllib.request.Request(
            f'https://generativelanguage.googleapis.com/v1beta/models/{EMBEDDING_MODEL}:batchEmbedContents',
            data=json.dumps(payload, ensure_ascii=False).encode(), method='POST',
            headers={'Content-Type': 'application/json', 'x-goog-api-key': key.strip()})
        try:
            with urllib.request.urlopen(request, timeout=90) as response:
                result = json.load(response)
        except urllib.error.HTTPError as error:
            # No keys, request bodies or upstream secrets in console output; no hidden retries.
            print(f'Stopped: Google HTTP {error.code}; successful batches remain cached.', flush=True)
            try:
                details = json.loads(error.read()).get('error', {}).get('details', [])
                for detail in details:
                    if detail.get('@type', '').endswith('RetryInfo'):
                        print('Suggested retry delay:', detail.get('retryDelay'), flush=True)
                    if detail.get('@type', '').endswith('QuotaFailure'):
                        for violation in detail.get('violations', []):
                            print('Quota:', violation.get('quotaId'), 'limit:', violation.get('quotaValue'), flush=True)
            except (ValueError, TypeError):
                pass
            return 1
        vectors = result.get('embeddings', [])
        if len(vectors) != len(batch):
            raise ValueError('Incomplete embedding response')
        for doc, vector in zip(batch, vectors, strict=True):
            stored['vectors'][doc['hash']] = quantize(vector['values'])
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix('.json.tmp')
        temporary.write_text(json.dumps(stored, separators=(',', ':'))+'\n', encoding='utf-8')
        temporary.replace(path)
        print(f'{min(start+len(batch), len(pending))}/{len(pending)} indexed', flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
