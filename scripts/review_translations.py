"""Apply reviewed terminology and report mechanical differences, entirely offline."""
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
DIRECTORY = ROOT / 'web/i18n'


def formula_translation(original):
    """Translate compact formula fields directly, retaining their operators and dice."""
    if len(original) > 110 or not re.search(r'Mod\.?\s*(?:Esprit|Social|Force|Agilité)', original, re.I):
        return None
    terms = {'esprit':'Spirit', 'social':'Social', 'force':'Force', 'agilité':'Agility',
             'dégâts de base':'Base Damage', 'dégats de base':'Base Damage',
             'nombre d\'effets':'number of effects', 'nombre':'number', 'effets':'effects',
             'valeur blackjack':'Blackjack value', 'aléatoire':'random', 'charges':'charges',
             'charge':'charge', 'par':'per', 'contendants':'bludgeoning', 'contondants':'bludgeoning',
             'tranchant':'slashing', 'nécrotiques':'necrotic', 'nécrotique':'necrotic',
             'psychiques':'psychic', 'psychique':'psychic', 'psy':'psychic',
             'arcanique':'arcane', 'soins':'healing', 'soin':'healing', 'feu':'fire',
             'glace':'ice', 'foudre':'lightning', 'poison':'poison', 'pv':'HP',
             'infligé':'dealt', 'subit':'taken', 'tours':'turns', 'tour':'turn', 'à':'to',
             'ballons':'balloons', 'nb':'number of'}
    doubled = 'doublé' in original.lower()
    original = re.sub(r'\s+doublé', '', original, flags=re.I)
    value = re.sub(r'Mod\.?\s*(Esprit|Social|Force|Agilité)',
                   lambda m: {'esprit':'Spirit','social':'Social','force':'Strength','agilité':'Agility'}[m[1].lower()]+' Mod', original, flags=re.I)
    pattern = re.compile('|'.join(r'(?<![A-Za-zÀ-ÿ])'+re.escape(t)+r'(?![A-Za-zÀ-ÿ])' for t in sorted(terms, key=len, reverse=True)), re.I)
    value = pattern.sub(lambda m: terms[m[0].lower()], value)
    value = value.replace('xtours', 'x turns').replace('xtour', 'x turn')
    value = re.sub(r'(?<=\d),(?=\d)', '.', value)
    # Unknown prose must go through editorial translation, never a partial replacement.
    if re.search(r'\b(?:vous|votre|des|une|pour|sur|les|dans|avec|fois|de)\b', value, re.I):
        return None
    result = re.sub(r'(?<=\))(?=[A-Za-z])', ' ', raw_power(value))
    return result + ('; use twice the Spirit Mod for the number of dice' if doubled else '')


def raw_power(value):
    # Existing parenthesized definitions are atomic, so they are never wrapped twice.
    pattern = re.compile(
        r'Raw\s+(?:(Spirit|Strength|Agility|Social)\s+)?Power(?:\s*\([^)]*\))?'
        r'|(?:(Spirit|Strength|Agility|Social)\s+Mod(?:ifier)?\.?|Mod(?:ifier)?\.?\s+(Spirit|Strength|Agility|Social))\s*(?:in\s+)?(?:[×x*]\s*)?(?:1\s*)?d6', re.I)

    def replace(match):
        attribute = next((g.title() for g in match.groups() if g), None)
        if attribute:
            return f'Raw {attribute} Power ({attribute} Mod d6)'
        return 'Raw Power (contextual Mod d6)'

    result = pattern.sub(replace, value)
    return re.sub(r'(Raw (?:Spirit|Strength|Agility|Social) Power \([^)]*\))\s*\(Raw Power \([^)]*\)\)', r'\1', result)


def review_characters():
    path = DIRECTORY / 'characters.en.json'
    translations = json.loads(path.read_text(encoding='utf-8'))
    source = json.loads((ROOT / 'web/public/data/characters.json').read_text(encoding='utf-8'))
    names = {c['identity']['nom'] for c in source}
    for name in names:
        translations[name] = name
    # Resolve ability/totem references against the same translated titles as the sheet.
    titles = {}
    for character in source:
        for title in [character['totem']['nom'], *[a['name'] for a in character['capacities']]]:
            if title in translations and len(title) > 4 and '<' not in title:
                titles[title] = translations[title]
    references = re.compile('|'.join(r'(?<!\w)'+re.escape(s)+r'(?!\w)' for s in sorted(titles, key=len, reverse=True))) if titles else None
    for original, translated in list(translations.items()):
        if original in names:
            continue
        translated = formula_translation(original) or raw_power(translated)
        translated = re.sub(r'\bStrength damage\b', 'force damage', translated, flags=re.I)
        if re.search(r'd6\s+force\b', original, re.I):
            translated = re.sub(r'(d6\)?\s+)Strength\b', r'\1Force', translated, flags=re.I)
        if references and original not in titles:
            translated = references.sub(lambda m: titles[m[0]], translated)
        translations[original] = translated
    overrides = DIRECTORY / 'reviewed-overrides.en.json'
    if overrides.exists():
        translations.update({k: raw_power(v) for k, v in json.loads(overrides.read_text(encoding='utf-8')).items()})
    glossary = json.loads((DIRECTORY / 'glossary.json').read_text(encoding='utf-8'))
    translations.update({key: value for key, value in glossary.items() if key in translations})
    path.write_text(json.dumps(translations, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def report():
    translations = json.loads((DIRECTORY / 'characters.en.json').read_text(encoding='utf-8'))
    suspects = []
    def numbers(text):
        text = re.sub(r'(?<!m)[²³]', '', text)
        return sorted(re.findall(r'\d+(?:[.,]\d+)?', re.sub(r'<[^>]*>', '', text).replace(',', '.').replace('³','3').replace('²','2')))
    for original, translated in translations.items():
        # Raw Power definitions introduce explanatory d6s, not changes to the mechanics.
        clean = re.sub(r'Raw (?:Spirit |Strength |Agility |Social )?Power\s*\([^)]*\)', '', translated)
        original_clean = re.sub(r'Mod(?:ificateur)?\.?\s*(?:d[’\x27]\s*)?(?:Esprit|Esp|Force|Agilité|Social)\s*(?:doublé\s*)?(?:en\s*)?(?:[×x*]\s*)?(?:1\s*)?d6', '', original, flags=re.I)
        if numbers(original_clean) != numbers(clean):
            suspects.append({'source': original, 'translation': translated, 'reason': 'numerical comparison'})
        if original == translated and len(original.split()) > 5 and re.search(r'\b(?:vous|une|des|pour|dans|avec)\b', original, re.I):
            suspects.append({'source': original, 'translation': translated, 'reason': 'unchanged French prose'})
    (DIRECTORY / 'review-report.json').write_text(json.dumps(suspects, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'{len(translations)} translations; {len(suspects)} entries to inspect')


if __name__ == '__main__':
    review_characters()
    report()
