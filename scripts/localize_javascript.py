"""Apply authored English UI translations while keeping application logic shared.

This is deterministic and offline. Long phrases are replaced before individual labels.
"""
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
DIRECTORY = ROOT / 'web/i18n'


def main():
    replacements = {}
    for line in (DIRECTORY / 'javascript.en.tsv').read_text(encoding='utf-8').splitlines():
        if line.strip():
            before, after = line.split('\t', 1)
            replacements[before] = after
    # One pass prevents short labels from altering text already translated by longer entries.
    pattern = re.compile('|'.join(
        (r'(?<!\w)' if k[0].isalnum() else '') + re.escape(k) + (r'(?!\w)' if k[-1].isalnum() else '')
        for k in sorted(replacements, key=len, reverse=True)))
    metadata = {}
    for name in ['app.js', 'catalogue.js', 'print.js', 'rules.js', 'gm.js', 'rules-chat.js']:
        source = (ROOT / 'web/public' / name).read_text(encoding='utf-8')
        output = pattern.sub(lambda m: replacements[m[0]], source)
        output = output.replace("localeCompare(b,'fr')", "localeCompare(b,'en')").replace(",'fr')", ",'en')")
        if name == 'app.js':
            labels = {'athletisme':'Athletics','resilience':'Resilience','acrobaties':'Acrobatics','discretion':'Stealth',
                      'escamotage':'Sleight of Hand','arcanes':'Arcana','culture':'Knowledge','survie':'Survival',
                      'tromperie':'Deception','representation':'Performance','perspicacite':'Insight','dressage':'Animal Handling',
                      'objectif':'Goal','liens':'Bonds','traitsSpeciaux':'Special traits','personnalite':'Personality',
                      'reputation':'Reputation','education':'Education','croyances':'Beliefs','cicatrices':'Scars',
                      'pulsion':'Drive','maniesEtTics':'Habits and tics','xpDisponibles':'Available XP'}
            output = output.replace("const pretty=s=>String", 'const fieldNames=' + json.dumps(labels) + ';\nconst pretty=s=>fieldNames[s]||String')
        if name == 'print.js':
            output = output.replace('const label=k=>', "Object.assign(names,{acrobaties:'Acrobatics',escamotage:'Sleight of Hand',arcanes:'Arcana',culture:'Knowledge',survie:'Survival',nature:'Nature',tromperie:'Deception',dressage:'Animal Handling'});\nconst label=k=>")
            output = output.replace("includes('inventaire')", "includes('inventory')")
        if name == 'catalogue.js':
            output = output.replace("['soin', 'soigne', 'soigner', 'soignez', 'guerison', 'regagne']", "['heal', 'healing', 'restore', 'regain']")
            output = output.replace("['protege', 'proteger', 'protegez', 'bouclier', 'reduit les degats']", "['protect', 'shield', 'reduce damage']")
            output = output.replace("['distance', 'arc', 'arbalete']", "['ranged', 'bow', 'crossbow']")
            output = output.replace("['invoque', 'invoquer', 'invoquez', 'invocation', 'invocateur']", "['summon', 'summoning', 'summoner']")
            output = output.replace("['entrave', 'immobilis', 'ralenti', 'controle', 'repousse']", "['restrain', 'immobiliz', 'slow', 'control', 'push']")
            output = output.replace("['furtif', 'invisible', 'invisibilite', 'discretion']", "['stealth', 'invisible', 'invisibility', 'hidden']")
            output = output.replace("w==='arc'?/\\barc\\b/", "w==='bow'?/\\bbow\\b/")
            output = output.replace('sans|pas|sauf|eviter|ni', 'without|not|except|avoid|neither|no').replace('debut|facile|simple', 'beginner|easy|simple')
        if name == 'rules.js':
            output = output.replace("['de','des','du','la','le','les','un','une','et','en','comment']", "['the','a','an','and','of','in','how','to']")
            output = output.replace("displayed${Math.min(shown, matches.length) > 1 ? 's' : ''}", "displayed")
        if name == 'gm.js':
            output = output.replace("'gm-session'", "'gm-session-en'").replace("'gm-pending'", "'gm-pending-en'")
        target = DIRECTORY / 'en' / name
        target.parent.mkdir(exist_ok=True)
        target.write_text(output, encoding='utf-8')
        metadata[name] = hashlib.sha256(source.encode()).hexdigest()
    (DIRECTORY / 'js-sources.json').write_text(json.dumps(metadata, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
