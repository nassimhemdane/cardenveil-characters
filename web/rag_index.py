"""Build a mechanical character corpus; lore never participates in retrieval scoring."""

import base64
import hashlib
import json
import math
import re
import unicodedata
from collections import Counter

EMBEDDING_MODEL = 'gemini-embedding-001'
DIMENSIONS = 768
STOP = set('je tu il elle nous vous ils elles un une des le la les du de d a au aux et ou en pour par avec qui que quoi veux voudrais personnage personnages jouer capacite capacites plutot tres sur dans mon mes ses son tout comme'.split())
THEMES = {
    'foudre': r'\b(?:foudre|electri\w*|eclair\w*|tonnerre|foudroy\w*|fulmin\w*)\b',
    'feu': r'\b(?:feu|flamme\w*|brul\w*|incendi\w*|inciner\w*|lave)\b',
    'glace': r'\b(?:glace|givre\w*|gele\w*|gelant\w*|glacial\w*|froid\w*)\b',
    'poison': r'\b(?:poison\w*|empoison\w*|toxiqu\w*|venin)\b',
    'soin': r'\b(?:soin\w*|soign\w*|gueri\w*|regener\w*|healer)\b|(?:regagn|rend|recuper)\w*[^.!?]{0,50}(?:\bpv\b|points? de vie)',
}


def terms(text):
    """Mirror the small French lexical normalizer used by the query engine."""
    text = ''.join(c for c in unicodedata.normalize('NFD', text.lower()) if not unicodedata.combining(c))
    return [re.sub(r'(?:er|es|ent|ant|e)$', '', w) if len(w) > 4 else w
            for w in re.findall(r'[a-z0-9]+', text) if len(w) > 2 and w not in STOP]


def digest(value):
    """Use deterministic hashes to invalidate stale documents and retrieval caches."""
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def make_documents(characters):
    """Create one independently retrievable passage per capacity and per nonempty totem."""
    documents = []
    for c in characters:
        entries = [('totem', c['totem'].get('nom', ''), c['totem'].get('description', ''), '')]
        entries += [(f'capacity-{i}', a['name'], a['description'],
                     f"Valeur : {a['value']['main']} {a['value']['bonus']}. Utilisation : {a['usage']}. Sauvegarde : {a['save']}.")
                    for i, a in enumerate(c['capacities'], 1)]
        for key, title, description, details in entries:
            if not description.strip():
                continue
            text = re.sub(r'\s+', ' ', f'{title} : {description} {details}').strip()
            # Names are displayed as provenance, not embedded as a proxy for play style.
            documents.append({'id': f"{c['id']}:{key}", 'characterId': c['id'],
                              'title': title, 'text': text, 'hash': digest(text)})
    return documents


def quantize(values):
    """Compress a unit embedding to int8, retaining its reconstructed cosine normalizer."""
    if len(values) != DIMENSIONS or not all(math.isfinite(v) for v in values):
        raise ValueError('Invalid embedding dimensions or values')
    maximum = max(abs(v) for v in values)
    if not maximum:
        raise ValueError('Zero embedding')
    integers = [max(-127, min(127, round(v / maximum * 127))) for v in values]
    norm = math.sqrt(sum(v*v for v in integers))
    return {'data': base64.b64encode(bytes(v % 256 for v in integers)).decode(), 'norm': norm}


def build_rag_index(characters, stored=None):
    """Join current numerical data with hash-matched embeddings; ignore stale vectors."""
    stored = stored or {}
    compatible = stored.get('model') == EMBEDDING_MODEL and stored.get('dimensions') == DIMENSIONS
    vectors = stored.get('vectors', {}) if compatible else {}
    documents = make_documents(characters)
    indexed = 0
    frequency = Counter()
    for doc in documents:
        words = terms(doc['text'])
        normalized = ''.join(c for c in unicodedata.normalize('NFD', doc['text'].lower()) if not unicodedata.combining(c))
        doc['features'] = [name for name, pattern in THEMES.items() if re.search(pattern, normalized)]
        doc['termCounts'] = dict(Counter(words))
        doc['length'] = len(words)
        frequency.update(set(words))
        vector = vectors.get(doc['hash'])
        if vector:
            try:
                raw = base64.b64decode(vector['data'], validate=True)
                if len(raw) != DIMENSIONS or not math.isfinite(vector['norm']) or vector['norm'] <= 0:
                    raise ValueError('Invalid stored vector')
            except (ValueError, KeyError, TypeError):
                continue
            doc['vector'] = vector
            indexed += 1
    entries = [{'id': c['id'], 'name': c['identity']['nom'], 'race': c['identity'].get('race', ''), 'stats': c['stats'],
                'difficulty': c.get('catalog', {}).get('difficulty'),
                'classes': c.get('catalog', {}).get('class', [])} for c in characters]
    index = {'schemaVersion': 1, 'model': EMBEDDING_MODEL, 'dimensions': DIMENSIONS,
             'characters': entries, 'documents': documents, 'embeddedDocuments': indexed}
    index['lexical'] = {'averageLength': sum(d['length'] for d in documents) / max(1, len(documents)),
                        'idf': {word: math.log(1 + (len(documents) - count + .5) / (count + .5))
                                for word, count in frequency.items()}}
    index['version'] = digest(index)
    return index
