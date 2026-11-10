"""Explicit, resumable editorial translation. Never called by the site build.

Uses only the preinstalled local Ollama model on loopback, with cloud disabled.
No credentials, external endpoint, download or cloud fallback are used.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import re
import time

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'web/i18n'
GLOSSARY = '''You are a French-to-English translator. Translate ALL supplied French prose into natural English. Never return the original French prose. Preserve only markup syntax and technical identifiers, not French words.
Cardenveil terminology, mandatory:
Force=Strength, Agilité=Agility, Esprit=Spirit, Social=Social, avantage=advantage,
Escamotage=Sleight of Hand, Résilience=Resilience, Culture=Knowledge,
compétence maîtrisée=proficient skill, maîtrise d'arme=Weapon Mastery,
Valeur brute=Raw Power (contextual Mod d6), Valeur brute d'Esprit=Raw Spirit Power (Spirit Mod d6).
Raw Power is the sum of a number of d6 equal to the contextual attribute modifier, NOT modifier times a single d6.
Whenever Raw Power appears, include the appropriate formula in parentheses, unless it already immediately follows.
seuil de miss=Miss Threshold, Incantation=Incantation, Précipitation=Rush, Ruée=Dash,
catalyseur=Focus, catalyseurs=Foci, armure=Armor, parade=Parry, déflexion=Deflection,
compétence=Skill, capacité=Ability, maîtrise=Mastery, éveil=Awakening,
cartes cristallisées=Crystallized Cards, couleur (card suit)=Suit, rouge/noir=red/black Color,
Cœurs=Hearts, Carreaux=Diamonds, Trèfles=Clubs, Piques=Spades,
MJ=GM, PNJ=NPC, PV=HP, zone de contrôle=Zone of Control, représentation=Performance,
perspicacité=Insight, dressage=Animal Handling, discrétion=Stealth, tromperie=Deception.
Keep personal character names, creator names, proper place names and Cardenveil unchanged.
Natural English, full translation, never summarize or omit content. No invented mechanics.
Preserve numerical values, dice, units in meters, formulas, markup tags/attributes, placeholders,
technical IDs, URL paths, image references, emoji, Markdown layout and links EXACTLY.
Distinguish personal Turn from global Round. Preserve unresolved initiative contradictions.
Translate modifiers as Strength Mod, Spirit Mod, etc. Retain skill proficiency doubling the modifier.
Only translate user-facing text, not machine field names.
D?fausser/defausser always means DISCARD, not shuffle. Piocher=draw, ?changer=exchange.
Never infer an attribute for generic valeur brute: use exactly Raw Power (contextual Mod d6).
Only explicitly named Spirit raw power becomes Raw Spirit Power (Spirit Mod d6).
Keep numeric digits as digits: do not change 2 to two or 1 to one. Keep tieffelin=Tiefling.
Translate ability names and references consistently, not just their descriptions.'''


def digest(text):
    return hashlib.sha256(text.encode()).hexdigest()


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def generate(prompt, *, json_mode=True):
    import urllib.request
    # Deliberately fixed loopback endpoint: this workflow cannot send content externally.
    payload = {'model': 'qwen3.5:9b-q4_K_M', 'stream': False, 'think': False,
               'messages': [{'role': 'system', 'content': GLOSSARY}, {'role': 'user', 'content': prompt}],
               'keep_alive': '30m', 'options': {'temperature': 0.1, 'num_ctx': 8192, 'num_predict': 6000, 'num_gpu': 29, 'presence_penalty': 0}}
    if json_mode:
        if prompt.startswith('Translate every string'):
            entries = json.loads(prompt.split('\n', 1)[1])
            payload['format'] = {'type':'object','properties':{key:{'type':'string','minLength':1} for key in entries},
                                 'required':list(entries),'additionalProperties':False}
        else:
            payload['format'] = {'type':'object','properties':{'markdown':{'type':'string'}},'required':['markdown']}
    for attempt in range(3):
        try:
            request = urllib.request.Request('http://127.0.0.1:11435/api/chat',
                data=json.dumps(payload).encode(), headers={'Content-Type': 'application/json'})
            with urllib.request.urlopen(request, timeout=1800) as response:
                result = json.load(response)
            text = result['message']['content']
            cache = ROOT / '.local-models/translation-cache'
            cache.mkdir(exist_ok=True)
            (cache / (digest(prompt) + '.json')).write_text(json.dumps({'prompt':prompt,'response':text},ensure_ascii=False),encoding='utf-8')
            if result.get('done_reason') == 'length':
                raise ValueError('Translation exceeded output limit')
            return json.loads(text) if json_mode else text
        except Exception as error:
            if attempt == 2:
                raise RuntimeError(f'Local translation failed: {type(error).__name__}') from None
            time.sleep(2 ** attempt)
    raise AssertionError('unreachable')


def translate_batch(values):
    entries = {f's{i}': value for i, value in enumerate(values)}
    result = generate('Translate every string VALUE from French into English in this JSON object. Return ONLY a JSON object with EXACTLY the same keys, each containing the complete English translation. Never merge or omit entries. Even short labels must be translated. Preserve HTML markup and all digits.\n' + json.dumps(entries, ensure_ascii=False))
    if not isinstance(result, dict) or set(result) != set(entries) or any(not isinstance(v,str) for v in result.values()):
        raise ValueError('Translation object shape mismatch')
    result = [result[key] for key in entries]
    for before, after in zip(values, result):
        if before.strip() and not after.strip():
            raise ValueError('Empty translated value')
        # Numeric mechanics must not change. Decimal punctuation may be localized.
        numbers = lambda s: re.findall(r'\d+(?:[.,]\d+)?', re.sub(r'<[^>]*>', '', s).replace(',', '.'))
        if sorted(numbers(before)) != sorted(numbers(after)) and 'Raw ' not in after:
            review_path = OUT / 'numeric-review.json'
            review = json.loads(review_path.read_text(encoding='utf-8')) if review_path.exists() else {}
            review[before] = after
            write(review_path, review)
    result = [re.sub(r'Raw Power(?:\s*\([^)]*\))?', 'Raw Power (contextual Mod d6)', value) for value in result]
    return dict(zip(values, result))


def batches(values, limit=6500):
    batch, size = [], 0
    for value in values:
        if batch and size + len(value) > limit:
            yield batch
            batch, size = [], 0
        batch.append(value)
        size += len(value)
    if batch:
        yield batch


def translate_dictionary(values, filename):
    path = OUT / filename
    saved = json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}
    todo = sorted(set(values) - saved.keys())
    jobs = list(batches(todo))
    print(f'{filename}: {len(todo)} strings, {len(jobs)} batches', flush=True)
    for index, batch in enumerate(jobs, 1):
        translated = translate_batch(batch)
        saved.update(translated)
        write(path, saved)
        print(f'{filename}: {index}/{len(jobs)} batches saved', flush=True)
    return saved


SKIP = {'id', 'image', 'portrait', 'download', 'printUrl', 'pageUrl', 'creator', 'joueur', 'color', 'forceAgi', 'schemaVersion', 'version'}


def strings(value, key=''):
    if key in SKIP:
        return
    if isinstance(value, dict):
        for name, item in value.items():
            yield from strings(item, name)
    elif isinstance(value, list):
        for item in value:
            yield from strings(item, key)
    elif isinstance(value, str) and re.search(r'[A-Za-zÀ-ÿ]{2}', value) and not value.startswith(('/', 'http:', 'https:', 'data:')):
        yield value


def characters():
    data = json.loads((ROOT / 'web/public/data/characters.json').read_text(encoding='utf-8'))
    translate_dictionary(list(strings(data)), 'characters.en.json')
    write(OUT / 'characters.sources.json', {c['id']: digest(json.dumps(c, ensure_ascii=False, sort_keys=True)) for c in data})


def rules():
    source_dir = ROOT / 'docs/rules/fragmented'
    destination = ROOT / 'docs/rules/en'
    destination.mkdir(exist_ok=True)
    meta_path = destination / 'sources.json'
    meta = json.loads(meta_path.read_text(encoding='utf-8')) if meta_path.exists() else {}
    for path in source_dir.glob('*.md'):
        source = path.read_text(encoding='utf-8')
        if meta.get(path.name) == digest(source) and (destination / path.name).exists():
            continue
        # Whole paragraphs keep mechanics, tables and links in context.
        chunks = ['\n\n'.join(b) for b in batches(source.split('\n\n'), 6500)]
        cache_path = OUT / 'rule-chunks.en.json'
        cache = json.loads(cache_path.read_text(encoding='utf-8')) if cache_path.exists() else {}
        for chunk in chunks:
            key = digest(chunk)
            if key in cache:
                continue
            response = generate('Translate this complete French Markdown fragment INTO ENGLISH. Every French sentence and heading must become English. Return JSON object {"markdown": "..."}. Keep every paragraph, table row, number, emoji, HTML tag and exact Obsidian image/link reference. Do not add a preamble.\n' + chunk)
            translated = response['markdown']
            if len(re.findall(r'\b(?:les|des|une|vous|pour|dans|avec|votre|peut)\b', translated.lower())) > max(5, len(translated.split()) // 30):
                raise ValueError('French prose remains in rule translation: ' + path.name)
            if len(translated) < len(chunk) * .55:
                raise ValueError('Suspiciously short Markdown translation')
            refs = lambda text: re.findall(r'!\[\[[^\]]+\]\]|!\[[^\]]*\]\([^)]*\)', text)
            if refs(chunk) != refs(translated):
                raise ValueError('Image references changed: ' + path.name)
            cache[key] = translated
            write(cache_path, cache)
            print(f'rules: {path.name} chunk saved', flush=True)
        (destination / path.name).write_text('\n\n'.join(cache[digest(c)] for c in chunks) + '\n', encoding='utf-8')
        meta[path.name] = digest(source)
        write(meta_path, meta)


def main():
    OUT.mkdir(exist_ok=True)
    parser = argparse.ArgumentParser()
    parser.add_argument('stage', choices=['characters', 'rules', 'ui'])
    args = parser.parse_args()
    if args.stage == 'ui':
        values = json.loads((OUT / 'ui-pending.json').read_text(encoding='utf-8'))
        translate_dictionary(values, 'ui.en.json')
    else:
        globals()[args.stage]()


if __name__ == '__main__':
    main()
