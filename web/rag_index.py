"""Index every meaningful character field while preserving source categories and provenance."""

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
TECHNICAL = {'id', 'schemaVersion', 'templateId', 'createdAt', 'updatedAt', 'portrait', 'image',
             'download', 'printUrl', 'pageUrl'}
LABELS = {'identity':'Identité', 'nom':'Nom', 'joueur':'Joueur', 'niveau':'Niveau', 'race':'Race',
    'alignement':'Alignement', 'age':'Âge', 'taille':'Taille', 'poids':'Poids', 'yeux':'Yeux',
    'peau':'Peau', 'cheveux':'Cheveux', 'stats':'Caractéristiques', 'force':'Force', 'agilite':'Agilité',
    'esprit':'Esprit', 'social':'Social', 'derived':'Valeurs dérivées', 'pvMax':'PV maximum',
    'pvActuels':'PV actuels', 'mouvement':'Mouvement', 'initiative':'Initiative', 'volonte':'Volonté',
    'skills':'Compétences', 'trained':'Maîtrisée', 'bonus':'Bonus stocké', 'athletisme':'Athlétisme',
    'resilience':'Résilience', 'acrobaties':'Acrobaties', 'discretion':'Discrétion', 'escamotage':'Escamotage',
    'arcanes':'Arcanes', 'investigation':'Investigation', 'perception':'Perception', 'culture':'Culture',
    'survie':'Survie', 'persuasion':'Persuasion', 'tromperie':'Tromperie', 'intimidation':'Intimidation',
    'representation':'Représentation', 'perspicacite':'Perspicacité', 'dressage':'Dressage',
    'narrative':'Narratif', 'background':'Historique', 'objectif':'Objectif', 'liens':'Liens',
    'personnalite':'Personnalité', 'reputation':'Réputation', 'education':'Éducation',
    'croyances':'Croyances', 'cicatrices':'Cicatrices', 'pulsion':'Pulsion',
    'maniesEtTics':'Manies et tics', 'instinct':'Instinct', 'traitsSpeciaux':'Traits spéciaux',
    'catalog':'Métadonnées du catalogue', 'creator':'Créateur', 'class':'Classes déclarées',
    'difficulty':'Difficulté', 'loreSummary':'Résumé narratif', 'gameplaySummary':'Résumé de jeu',
    'notes':'Notes', 'defense':'Défense', 'resources':'Ressources', 'tokens':'Jetons',
    'inventory':'Inventaire', 'inventoryItems':'Objets', 'equipment':'Équipement', 'weapons':'Armes',
    'weaponMasteries':'Maîtrises d’armes', 'elementalMasteries':'Maîtrises élémentaires',
    'feats':'Aptitudes', 'progression':'Progression', 'abilityControls':'Contrôle des capacités',
    'capacities':'Capacités', 'incantation':'Incantation', 'cost':'Coût', 'color':'Couleur',
    'name':'Nom', 'description':'Description', 'prepared':'Préparée'}


def field_leaves(value, path=''):
    """Enumerate all populated scalar paths; retain zero/false, but omit blobs and technical URLs."""
    if isinstance(value, dict):
        for key, child in value.items():
            if key not in TECHNICAL:
                yield from field_leaves(child, f'{path}.{key}'.strip('.'))
    elif isinstance(value, list):
        for i, child in enumerate(value):
            yield from field_leaves(child, f'{path}[{i}]')
    elif value is not None and value != '' and not (isinstance(value, str) and value.startswith('data:')):
        yield path, value


def field_text(path, value):
    """Keep readable labels alongside precise original field paths for faithful citations."""
    label=' / '.join(LABELS.get(part, part) for part in re.split(r'\.|\[\d+\]', path) if part)
    if isinstance(value, bool):
        value = 'oui' if value else 'non'
    return f'{label} [{path}] : {value}.'


def terms(text):
    """Mirror the small French lexical normalizer used by the query engine."""
    text = ''.join(c for c in unicodedata.normalize('NFD', text.lower()) if not unicodedata.combining(c))
    return [re.sub(r'(?:er|es|ent|ant|e)$', '', w) if len(w) > 4 else w
            for w in re.findall(r'[a-z0-9]+', text) if len(w) > 2 and w not in STOP]


def digest(value):
    """Use deterministic hashes to invalidate stale documents and retrieval caches."""
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def make_documents(characters):
    """Retain existing ability embeddings and add typed passages for all other populated fields."""
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
            if key == 'totem':
                paths = ['totem.nom', 'totem.description']
            else:
                prefix = f"capacities[{int(key.split('-')[1])-1}]"
                paths = [f'{prefix}.{p}' for p in ('name','description','value.main','value.bonus','usage','save')]
            documents.append({'id': f"{c['id']}:{key}", 'characterId': c['id'],
                              'title': title, 'text': text, 'hash': digest(text), 'category':'mechanical',
                              'paths': paths, 'embeddingRequired':True})
        narrative = {k:v for k,v in c.get('narrative', {}).items() if k != 'traitsSpeciaux'}
        groups = [
            ('identity-fields','Identité','identity',False,{'identity':c.get('identity',{})}),
            ('values-fields','Statistiques et valeurs','statistics',False,
             {k:c.get(k,{}) for k in ('stats','derived','defense','resources','progression','abilityControls')}),
            ('skills-fields','Compétences','skills',False,{'skills':c.get('skills',{})}),
            ('narrative-fields','Histoire et personnalité','narrative',True,{'narrative':narrative,'notes':c.get('notes','')}),
            ('traits-fields','Traits spéciaux et passifs','mechanical',True,{'narrative':{'traitsSpeciaux':c.get('narrative',{}).get('traitsSpeciaux',[])}}),
            ('catalogue-fields','Présentation du catalogue','catalogue',True,{'catalog':c.get('catalog',{})}),
            ('equipment-fields','Armes et inventaire','equipment',True,
             {k:c.get(k,{}) for k in ('weapons','equipment','inventory','inventoryItems')}),
            ('masteries-fields','Maîtrises, actions et aptitudes','mechanical',True,
             {k:c.get(k,[]) for k in ('weaponMasteries','elementalMasteries','actions','reactions','tokens','feats')}),
            ('ability-fields','Propriétés des capacités et du totem','statistics',False,{
                'capacities':[{k:v for k,v in a.items() if k not in ('description','image')} for a in c.get('capacities',[])],
                'totem':{k:v for k,v in c.get('totem',{}).items() if k not in ('description','image')}}),
        ]
        covered={key for group in groups for key in group[-1]}
        extra={key:value for key,value in c.items() if key not in covered and key not in TECHNICAL}
        groups.append(('extra-fields','Autres informations','reference',True,extra))
        for key, title, category, embed, values in groups:
            leaves=list(field_leaves(values))
            # Bound passages without discarding later fields or cutting a value mid-sentence.
            chunks=[];chunk=[];size=0
            for path, value in leaves:
                line=field_text(path,value)
                if chunk and size+len(line)>4500:
                    chunks.append(chunk);chunk=[];size=0
                # Exceptionally long strings are split into fully searchable segments.
                for start in range(0,len(line),4000):
                    part=line[start:start+4000]
                    if chunk and size+len(part)>4500:
                        chunks.append(chunk);chunk=[];size=0
                    chunk.append((path,part));size+=len(part)
            if chunk:chunks.append(chunk)
            for i, chunk in enumerate(chunks):
                text=' '.join(line for _,line in chunk)
                documents.append({'id':f"{c['id']}:{key}-{i+1}",'characterId':c['id'],'title':title,
                    'text':text,'hash':digest(text),'category':category,'paths':[p for p,_ in chunk],
                    'embeddingRequired':embed})
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
    expected={(c['id'],path) for c in characters for path,value in field_leaves(c)}
    covered={(d['characterId'],path) for d in documents for path in d['paths']}
    if expected - covered:
        raise ValueError(f'Unindexed populated character fields: {sorted(expected-covered)[:10]}')
    indexed = 0
    frequency = Counter()
    for doc in documents:
        words = terms(doc['text'])
        normalized = ''.join(c for c in unicodedata.normalize('NFD', doc['text'].lower()) if not unicodedata.combining(c))
        doc['features'] = [name for name, pattern in THEMES.items() if re.search(pattern, normalized)] if doc['category'] in ('mechanical','equipment') else []
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
            indexed += int(doc['embeddingRequired'])
    entries = [{'id': c['id'], 'name': c['identity']['nom'], 'race': c['identity'].get('race', ''), 'stats': c['stats'],
                'fields':{k:c[k] for k in ('identity','derived','defense','resources','skills','progression','abilityControls','catalog') if k in c},
                'difficulty': c.get('catalog', {}).get('difficulty'),
                'classes': c.get('catalog', {}).get('class', [])} for c in characters]
    index = {'schemaVersion': 1, 'model': EMBEDDING_MODEL, 'dimensions': DIMENSIONS,
             'characters': entries, 'documents': documents, 'embeddedDocuments': indexed,
             'embeddingRequiredDocuments':sum(d['embeddingRequired'] for d in documents),
             'indexedFieldCount':len(expected)}
    index['lexical'] = {'averageLength': sum(d['length'] for d in documents) / max(1, len(documents)),
                        'idf': {word: math.log(1 + (len(documents) - count + .5) / (count + .5))
                                for word, count in frequency.items()}}
    index['version'] = digest(index)
    return index
