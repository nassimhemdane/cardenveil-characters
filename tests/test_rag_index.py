"""Check mechanical chunking, stale-vector invalidation and compact embedding integrity."""

import base64
import importlib
from copy import deepcopy
from pathlib import Path

import pytest


def module(monkeypatch):
    """Load the build helper without changing the canonical character model."""
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1] / 'web'))
    return importlib.import_module('rag_index')


def character():
    """Keep the ninth capability distinctive to catch whole-character truncation regressions."""
    return {'id':'hero','identity':{'nom':'Hero'},'stats':{'force':18,'agilite':12,'esprit':8,'social':6},
            'catalog':{'difficulty':3,'loreSummary':'Un mage invincible de feu.'},
            'totem':{'nom':'Totem','description':'Protège les alliés.'},
            'capacities':[{'name':f'Capacité {i}','description':f'Capacité mécanique numéro {i}.',
              'value':{'main':'2d6','bonus':''},'usage':'Action','save':'Acrobaties'} for i in range(9)]}


def test_every_ability_is_separately_retrievable(monkeypatch):
    """Never drop late abilities or embed lore as if it were a mechanical fact."""
    m=module(monkeypatch)
    index=m.build_rag_index([character()])
    assert len(index['documents'])==10
    assert any(d['id']=='hero:capacity-9' for d in index['documents'])
    assert not any('invincible' in d['text'] for d in index['documents'])
    assert index['characters'][0]['stats']['force']==18


def test_vector_reuse_and_staleness(monkeypatch):
    """Reuse unchanged passages when only statistics change; invalidate modified text."""
    m=module(monkeypatch);c=character();doc=m.make_documents([c])[0]
    packed=m.quantize([1.0]+[0.0]*767)
    store={'model':m.EMBEDDING_MODEL,'dimensions':768,'vectors':{doc['hash']:packed}}
    first=m.build_rag_index([c],store)
    assert first['embeddedDocuments']==1
    changed=deepcopy(c);changed['stats']['force']=20
    second=m.build_rag_index([changed],store)
    assert second['embeddedDocuments']==1 and second['version']!=first['version']
    changed['totem']['description']='Un autre effet.'
    assert m.build_rag_index([changed],store)['embeddedDocuments']==0
    store['model']='incompatible'
    assert m.build_rag_index([c],store)['embeddedDocuments']==0


def test_quantization_rejects_invalid_vectors(monkeypatch):
    """Store compact signed vectors with finite values and the correct dimension count."""
    m=module(monkeypatch)
    packed=m.quantize([1,-1]+[0]*766)
    assert len(base64.b64decode(packed['data']))==768
    for bad in ([1], [0]*768, [float('nan')]*768):
        with pytest.raises(ValueError):m.quantize(bad)
