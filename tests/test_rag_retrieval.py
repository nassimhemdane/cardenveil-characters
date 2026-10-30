"""Regression tests for numerical priority, exclusions and capability-level retrieval."""

from test_gemini_pages import run_harness

HARNESS = '''<pre id="result">RUNNING</pre><script type="module">
import {retrieve,parseIntent,statisticalProfile} from '/web/rag-retrieval.js';
import {validateRecommendations,validateRagRecommendations} from '/web/recommendations-core.js';
try{
 const assert=(value,label)=>{if(!value)throw Error(label);};
 const make=(id,force,agility,spirit,social,difficulty=3)=>({id,name:id,stats:{force,agilite:agility,esprit:spirit,social},difficulty,classes:[]});
 const index={version:'synthetic',dimensions:2,characters:[make('strong',20,10,6,6),make('bait',6,10,20,6),make('agile',8,20,6,6),make('social',8,8,6,20),make('too-hard',20,20,20,20,5)],
  documents:[{id:'s:1',characterId:'strong',title:'Frappe',text:'Frappe une cible avec une arme.'},
   {id:'b:1',characterId:'bait',title:'Force',text:'Force physique fort force physique fort force physique.'},
   {id:'a:1',characterId:'agile',title:'Bond',text:'Bond mobile pour fuir.'},
   {id:'soc:1',characterId:'social',title:'Discours',text:'Persuasion sociale.'},
   {id:'h:1',characterId:'too-hard',title:'Frappe',text:'Force physique forte.'}]};
 let result=retrieve(index,'Je veux un personnage fort et physique, difficulté maximum 4/5');
 assert(result.candidates[0].id==='strong','stats beat evocative text');
 assert(!result.candidates.some(c=>c.id==='too-hard'),'difficulty hard filter');
 assert(retrieve(index,'Je veux un personnage agile et mobile, difficulté maximum 4/5').candidates[0].id==='agile','agility priority');
 assert(retrieve(index,'Un mage, difficulté max 4').candidates[0].id==='bait','spirit for mage');
 assert(retrieve(index,'Un diplomate charismatique, difficulté max 4').candidates[0].id==='social','social priority');
 assert(parseIntent('Je veux peu de force mais beaucoup de magie').preferences.force===-1,'negative preference');
 assert(!parseIntent('Je veux un personnage fort en magie').preferences.force,'strong in magic is not physical force');
 assert(parseIntent('difficulté 3/5 maximum').maxDifficulty===3,'trailing difficulty ceiling');
 assert(retrieve(index,'Difficulté maximum 3/5').candidates.length>0,'difficulty-only request');
 assert(retrieve(index,'Force minimum 18, difficulté max 4').candidates.every(c=>c.stats.force>=18),'numeric constraint');
 assert(retrieve(index,'Foudre introuvable, difficulté max 0.5').candidates.length===0,'honest no-match');
 assert(retrieve(index,'Un mage qui soigne').candidates.length===0,'high spirit alone cannot invent healing');
 assert(retrieve(index,'Un personnage mobile utilisant la foudre').candidates.length===0,'high agility alone cannot invent lightning');
 assert(statisticalProfile({force:10,agilite:10,esprit:10,social:10})==='polyvalent','no invented official class');
 for(const c of result.candidates){assert(c.facts.includes('Force '+c.stats.force),'statistics in evidence');}
 const semantic={version:'semantic',dimensions:2,characters:[make('near',10,10,10,10),make('far',10,10,10,10)],documents:[
  {id:'near:9',characterId:'near',title:'Late ability',text:'Retire une condition et rend des points de vie.',vector:{data:'fwA=',norm:127}},
  {id:'far:1',characterId:'far',title:'Other',text:'Fait exploser une roche.',vector:{data:'AIE=',norm:127}}]};
 result=retrieve(semantic,'Je veux soutenir mon équipe',[1,0]);
 assert(result.mode==='stats+embeddings+bm25' && result.candidates[0].id==='near','vector retrieval without matching keywords');
 const reversed={explanation:'Classement',matches:result.candidates.slice().reverse().map(c=>({character_id:c.id,comment:'Correspondance',evidence:c.passages[0].text}))};
 assert(validateRecommendations(reversed,result.candidates).matches[0].character_id==='near','model cannot reorder server ranking');
 const grounded=validateRagRecommendations({explanation:'Test',matches:[{character_id:'near',comment:'Soutient le groupe.',source_id:'near:9'}]},result.candidates);
 assert(grounded.matches[0].evidence===semantic.documents[0].text,'server copies evidence from actual source');
 let rejected=false;try{validateRagRecommendations({explanation:'Test',matches:[{character_id:'near',comment:'Wrong.',source_id:'far:1'}]},result.candidates);}catch{rejected=true;}
 assert(rejected,'reject a source belonging to another character');
 document.querySelector('#result').textContent='PASS';
}catch(error){document.querySelector('#result').textContent='FAIL '+error.message;}
</script>'''


def test_rag_numerical_priority(tmp_path):
    """Rank facts over prose and preserve numerical constraints through model validation."""
    run_harness(tmp_path,HARNESS)
