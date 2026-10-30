"""Make one real explanation call using the ranked evaluation's lightning/mobility case."""

import argparse
import json
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    """Require free-tier confirmation; validate real IDs and source ownership before reporting success."""
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--confirm-free-tier',action='store_true')
    if not parser.parse_args().confirm_free_tier:
        raise SystemExit('Free-tier confirmation required')
    from dotenv import dotenv_values
    report=json.loads((ROOT/'gemini-output/rag-evaluation/report.json').read_text(encoding='utf-8'))[1]
    index=json.loads((ROOT/'web/public/data/rag-index.json').read_text(encoding='utf-8'))
    docs={d['id']:d for d in index['documents']}
    characters={c['id']:c for c in index['characters']}
    candidates=[]
    for entry in report['matches']:
        c=characters[entry['id']]
        candidates.append({**c,'sources':[{'id':s['id'],'title':docs[s['id']]['title'],'text':docs[s['id']]['text']} for s in entry['sources']]})
    system=(ROOT/'web/recommendations-core.js').read_text(encoding='utf-8').split('export const SYSTEM = `',1)[1].split('`;',1)[0]
    schema={'type':'object','required':['matches','explanation'],'properties':{
        'explanation':{'type':'string'},'matches':{'type':'array','maxItems':6,'items':{
            'type':'object','required':['character_id','comment','source_id'],
            'properties':{k:{'type':'string'} for k in ('character_id','comment','source_id')}}}}}
    payload={'systemInstruction':{'parts':[{'text':system}]},
        'contents':[{'role':'user','parts':[{'text':json.dumps({'request':report['message'],'candidates':candidates},ensure_ascii=False)}]}],
        'generationConfig':{'temperature':.1,'maxOutputTokens':2300,'responseMimeType':'application/json','responseJsonSchema':schema}}
    key=dotenv_values(ROOT/'.env')['GEMINI_API_KEY']
    request=urllib.request.Request('https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-lite:generateContent',
        data=json.dumps(payload,ensure_ascii=False).encode(),method='POST',
        headers={'Content-Type':'application/json','x-goog-api-key':key.strip()})
    with urllib.request.urlopen(request,timeout=60) as response:
        data=json.load(response)
    candidate=data['candidates'][0]
    if candidate['finishReason']!='STOP':
        raise ValueError('Incomplete generation: '+candidate['finishReason'])
    result=json.loads(''.join(p.get('text','') for p in candidate['content']['parts'] if not p.get('thought')))
    known={c['id']:c for c in candidates};seen=set()
    assert len(result['matches'])<=6
    for match in result['matches']:
        assert match['character_id'] in known and match['character_id'] not in seen
        assert 0<len(match['comment'])<=700
        assert any(s['id']==match['source_id'] for s in known[match['character_id']]['sources'])
        seen.add(match['character_id'])
    order={c['id']:i for i,c in enumerate(candidates)}
    result['matches'].sort(key=lambda m:order[m['character_id']])
    (ROOT/'gemini-output/rag-evaluation/generation-example.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    for match in result['matches']:
        print(match['character_id'],match['comment'])
    print('Real generation verified:',len(result['matches']),'matches, valid source IDs, no invented character.')


if __name__=='__main__':
    main()
