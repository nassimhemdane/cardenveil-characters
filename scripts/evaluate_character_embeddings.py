"""Run four bounded, real query-embedding evaluations against the built character corpus."""

import argparse
import html
import json
import re
import sys
import tempfile
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
QUERIES = [
    'Je veux un combattant physique avec beaucoup de force, difficulté maximum 4/5.',
    'Je veux un personnage mobile utilisant la foudre, difficulté maximum 4/5.',
    'Je veux un mage avec un esprit élevé qui soigne ses alliés, difficulté maximum 4/5.',
    'Je veux un diplomate charismatique qui contrôle les ennemis, difficulté maximum 4/5.',
]


def main():
    """Generate at most four query vectors; reuse them and save source-backed rankings."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--confirm-free-tier', action='store_true')
    args = parser.parse_args()
    if not args.confirm_free_tier:
        raise SystemExit('Free-tier confirmation required')
    sys.path.insert(0, str(ROOT / 'web'))
    from rag_index import EMBEDDING_MODEL, DIMENSIONS
    output = ROOT / 'gemini-output/rag-evaluation'
    output.mkdir(parents=True, exist_ok=True)
    path = output / 'query-vectors.json'
    if not path.exists():
        from dotenv import dotenv_values
        key = dotenv_values(ROOT / '.env').get('GEMINI_API_KEY')
        payload = {'requests': [{'model': f'models/{EMBEDDING_MODEL}', 'taskType': 'RETRIEVAL_QUERY',
            'outputDimensionality': DIMENSIONS, 'content': {'parts': [{'text': q}]}} for q in QUERIES]}
        request = urllib.request.Request(
            f'https://generativelanguage.googleapis.com/v1beta/models/{EMBEDDING_MODEL}:batchEmbedContents',
            data=json.dumps(payload, ensure_ascii=False).encode(), method='POST',
            headers={'Content-Type': 'application/json', 'x-goog-api-key': key.strip()})
        with urllib.request.urlopen(request, timeout=60) as response:
            data = json.load(response)
        assert len(data['embeddings']) == len(QUERIES)
        path.write_text(json.dumps({'model': EMBEDDING_MODEL, 'dimensions': DIMENSIONS,
            'queries': [{'message': q, 'vector': v['values']} for q, v in zip(QUERIES, data['embeddings'], strict=True)]})+'\n', encoding='utf-8')
    sys.path.insert(0, str(ROOT / 'tests'))
    from test_gemini_pages import run_harness
    harness = '''<pre id="result">RUNNING</pre><pre id="evaluation"></pre><script type="module">
import {retrieve} from '/web/rag-retrieval.js';
try{
 const index=await (await fetch('/web/public/data/rag-index.json')).json();
 const queries=await (await fetch('/gemini-output/rag-evaluation/query-vectors.json')).json();
 if(index.model!==queries.model || index.dimensions!==queries.dimensions || index.embeddedDocuments!==(index.embeddingRequiredDocuments??index.documents.length))throw Error('Incomplete or incompatible index');
 const report=queries.queries.map(q=>{
   const started=performance.now(),result=retrieve(index,q.message,q.vector);
   return {message:q.message,mode:result.mode,milliseconds:performance.now()-started,
     matches:result.candidates.map(c=>({id:c.id,stats:c.stats,score:c.score,attributeScore:c.attributeScore,
       relevance:c.relevance,difficulty:c.difficulty,sources:c.passages.map(p=>({id:p.id,title:p.title}))}))};
 });
 document.querySelector('#evaluation').textContent=JSON.stringify(report);
 document.querySelector('#result').textContent='PASS';
}catch(e){document.querySelector('#result').textContent='FAIL '+e.message;}
</script>'''
    with tempfile.TemporaryDirectory() as temporary:
        result = run_harness(Path(temporary), harness)
    match = re.search(r'<pre id="evaluation">(.*?)</pre>', result, re.S)
    report = json.loads(html.unescape(match[1]))
    (output / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    for row in report:
        print(row['message'])
        for c in row['matches'][:3]:
            print(c['id'], c['stats'], 'source:', c['sources'][0]['title'], 'score:', round(c['score'], 3))
        print('Retrieval milliseconds:', round(row['milliseconds'], 1))


if __name__ == '__main__':
    main()
