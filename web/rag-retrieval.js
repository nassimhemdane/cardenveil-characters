/** Deterministic hybrid retrieval: numerical attributes outrank descriptive prose. */
export const RAG_VERSION = 'stats-first-v2-identity';
const stats = ['force','agilite','esprit','social'];
const labels = {force:'Force',agilite:'Agilité',esprit:'Esprit',social:'Social'};
const normalize = text => String(text||'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase();
const stop = new Set('je tu il elle nous vous ils elles un une des le la les du de d a au aux et ou en pour par avec qui que quoi veux voudrais personnage personnages jouer capacite capacites plutot tres sur dans mon mes ses son tout comme'.split(' '));
const terms = text => normalize(text).match(/[a-z0-9]+/g)?.filter(w=>w.length>2&&!stop.has(w))
  .map(w=>w.length>4?w.replace(/(?:er|es|ent|ant|e)$/,''):w) || [];
const expressions = {
  force:/\b(force|fort|forte|physique|muscle|musclee|costaud|costaude|guerrier|guerriere|barbare|tank|robuste)\b/g,
  agilite:/\b(agilite|agile|rapide|mobile|mobilite|furtif|furtive|archer|archere|assassin|assassine|discret|discrete)\b/g,
  esprit:/\b(esprit|mage|magicien|magicienne|sorcier|sorciere|mental|mentale|magie|intelligent|intelligente)\b/g,
  social:/\b(social|sociale|charisme|charismatique|diplomate|persuasif|persuasive|barde|negociateur|negociatrice)\b/g
};
const themes={
  foudre:/\b(?:foudre|electri\w*|eclair\w*|tonnerre|foudroy\w*|fulmin\w*)\b/,
  feu:/\b(?:feu|flamme\w*|brul\w*|incendi\w*|inciner\w*|lave)\b/,
  glace:/\b(?:glace|givre\w*|gele\w*|gelant\w*|glacial\w*|froid\w*)\b/,
  poison:/\b(?:poison\w*|empoison\w*|toxiqu\w*|venin)\b/,
  soin:/\b(?:soin\w*|soign\w*|gueri\w*|regener\w*|healer)\b|(?:regagn|rend|recuper)\w*[^.!?]{0,50}(?:\bpv\b|points? de vie)/
};
const features=text=>Object.entries(themes).filter(([,pattern])=>pattern.test(normalize(text))).map(([name])=>name);

const raceWord=word=>({elf:'elfe',elfs:'elfe',elfes:'elfe',efle:'elfe',efles:'elfe',orques:'orc',orque:'orc',orcs:'orc',humaine:'humain',humaines:'humain',naine:'nain',naines:'nain'}[word] || word.replace(/s$/,''));
const raceWords=text=>(normalize(text).match(/[a-z]+/g)||[]).map(raceWord);
const raceQualifiers=new Set(['haut','haute','noir','noire','demi','grand','grande','petit','petite','de','du','et','des']);

export function identityIntent(index,message){
  const known=new Set(index.characters.flatMap(c=>raceWords(c.race)).filter(w=>w.length>=3&&!raceQualifiers.has(w)));
  const raw=normalize(message).match(/[a-z0-9]+/g)||[], words=raw.map(raceWord);
  const required=[],excluded=[];
  for(let i=0;i<words.length;i++){
    if(!known.has(words[i]))continue;
    const prefix=raw.slice(Math.max(0,i-5),i).join(' ').split(/\b(?:mais|et|ou)\b/).pop();
    const negative=/\b(sans|pas|ni|eviter)\b/.test(prefix);
    const destination=negative?excluded:required;
    if(!destination.includes(words[i]))destination.push(words[i]);
    for(const neighbour of [words[i-1],words[i+1]]){
      if(neighbour && raceQualifiers.has(neighbour) && !['de','du','et','des'].includes(neighbour) && !destination.includes(neighbour))destination.push(neighbour);
    }
  }
  const recognized=new Set([...required,...excluded]);
  const boilerplate=new Set('je cherche recherche veux voudrai souhaite recommande moi montre propose donne tous toute le la les un une des de du d au aux personnage personnage race peuple et ou s il te plait plutot'.split(' ').map(raceWord));
  const only=required.length>0 && words.every(w=>recognized.has(w)||boilerplate.has(w));
  return {required,excluded,any:/\bou\b/.test(normalize(message)),only};
}

function matchesIdentity(character,intent){
  const present=new Set(raceWords(character.race));
  const bases=intent.required.filter(w=>!raceQualifiers.has(w));
  const qualifiers=intent.required.filter(w=>raceQualifiers.has(w));
  return (!bases.length || (intent.any?bases.some(w=>present.has(w)):bases.every(w=>present.has(w)))) &&
    qualifiers.every(w=>present.has(w)) && !intent.excluded.some(w=>present.has(w));
}

export function parseIntent(message) {
  const text=normalize(message), preferences={}, constraints=[];
  for(const stat of stats){
    const matches=[...text.matchAll(expressions[stat])];
    for(const match of matches){
      if(stat==='force' && /^forte?$/.test(match[0]) &&
          /^\s+(?:en\s+)?(?:magie|esprit|charisme|agilite|mobilite|social)/.test(text.slice(match.index+match[0].length)))continue;
      const prefix=text.slice(Math.max(0,match.index-45),match.index).split(/[,;]|\b(?:mais|et)\b/).pop();
      const low=/\b(sans|pas|peu|faible|eviter|ni)\b/.test(prefix);
      preferences[stat]=low?-1:1;
    }
    const rule=new RegExp(`\\b${stat}\\s*(>=|<=|>|<|au moins|au plus|minimum|min|max|maximum|superieur a|inferieur a)\\s*(\\d{1,2})`,'g');
    for(const m of text.matchAll(rule))constraints.push({stat,operator:m[1],value:Number(m[2])});
  }
  const difficulty=text.match(/(?:difficulte|complexite)\s*(?:de\s*)?(?:maximum|max|au plus|<=)\s*(\d(?:[.,]\d)?)/) ||
    text.match(/(?:difficulte|complexite)\s*(?:de\s*)?(\d(?:[.,]\d)?)(?:\s*\/\s*5)?\s*(?:maximum|max|au plus)/);
  const maxDifficulty=difficulty?Number(difficulty[1].replace(',','.')):
    (/\b(debutant|debutante|je debute|facile a jouer|simple a jouer)\b/.test(text)?2:null);
  const requiredThemes=[],excludedThemes=[];
  for(const [name,pattern] of Object.entries(themes)){
    const match=pattern.exec(text);if(!match)continue;
    const prefix=text.slice(Math.max(0,match.index-35),match.index).split(/[,;]|\b(?:mais|et)\b/).pop();
    (/\b(sans|pas|eviter|ni)\b/.test(prefix)?excludedThemes:requiredThemes).push(name);
  }
  return {preferences,constraints,maxDifficulty,requiredThemes,excludedThemes};
}

export function statisticalProfile(values) {
  const ordered=stats.map(key=>({key,value:Number(values[key])||0})).sort((a,b)=>b.value-a.value);
  const dominant=ordered.filter(s=>s.value>=ordered[0].value-2).map(s=>s.key);
  const names={force:'physique',agilite:'agile',esprit:'mental',social:'social'};
  return dominant.length>=3?'polyvalent':dominant.map(key=>names[key]).join(' / ');
}

function respects(character,intent){
  if(intent.maxDifficulty!==null && (character.difficulty==null || character.difficulty>intent.maxDifficulty))return false;
  return intent.constraints.every(({stat,operator,value})=>{
    const n=Number(character.stats?.[stat]);
    if(!Number.isFinite(n))return false;
    if(['>=','au moins','minimum','min'].includes(operator))return n>=value;
    if(['<=','au plus','maximum','max'].includes(operator))return n<=value;
    if(['>','superieur a'].includes(operator))return n>value;
    return n<value;
  });
}

function normalizeVector(values,dimensions){
  if(!Array.isArray(values)||values.length!==dimensions||!values.every(Number.isFinite))throw Error('Invalid query embedding');
  const norm=Math.sqrt(values.reduce((sum,v)=>sum+v*v,0));
  if(!norm)throw Error('Zero query embedding');
  return values.map(v=>v/norm);
}

function cosine(query,vector){
  const raw=vector.decoded || (vector.decoded=Int8Array.from(atob(vector.data),c=>c.charCodeAt(0)));
  if(raw.length!==query.length || !Number.isFinite(vector.norm) || vector.norm<=0)throw Error('Invalid corpus embedding');
  let dot=0;
  for(let i=0;i<raw.length;i++)dot+=query[i]*raw[i];
  return Math.max(-1,Math.min(1,dot/vector.norm));
}

export function retrieve(index,message,queryEmbedding=null){
  const intent=parseIntent(message), queryTerms=[...new Set(terms(message))];
  intent.identity=identityIntent(index,message);
  const query=queryEmbedding?normalizeVector(queryEmbedding,index.dimensions):null;
  const precomputed=Boolean(index.lexical);
  const corpus=precomputed?index.documents:index.documents.map(doc=>({...doc,words:terms(doc.text)}));
  const df=new Map();
  if(!precomputed)for(const doc of corpus)for(const word of new Set(doc.words))df.set(word,(df.get(word)||0)+1);
  const average=precomputed?index.lexical.averageLength:corpus.reduce((sum,d)=>sum+d.words.length,0)/Math.max(1,corpus.length);
  const byCharacter=new Map();
  for(const doc of corpus){
    let lexical=0;
    const frequency=new Map();if(!precomputed)for(const word of doc.words)frequency.set(word,(frequency.get(word)||0)+1);
    for(const word of queryTerms){
      const count=precomputed?(doc.termCounts[word]||0):(frequency.get(word)||0);
      if(count){const idf=precomputed?(index.lexical.idf[word]||0):Math.log(1+(corpus.length-(df.get(word)||0)+.5)/((df.get(word)||0)+.5));
        lexical+=idf*count*2.2/(count+1.2*(.25+.75*(precomputed?doc.length:doc.words.length)/Math.max(1,average)));}
    }
    const semantic=query&&doc.vector?cosine(query,doc.vector):0;
    const lexicalScore=lexical/(lexical+4);
    const docScore=query ? .75*Math.max(0,semantic)+.25*lexicalScore : lexicalScore;
    const row={...doc,features:doc.features||features(doc.text),lexicalScore,semantic,docScore};
    if(!byCharacter.has(doc.characterId))byCharacter.set(doc.characterId,[]);
    byCharacter.get(doc.characterId).push(row);
  }
  const hasStats=Object.keys(intent.preferences).length>0;
  const ranked=[];
  for(const c of index.characters){
    if(!respects(c,intent) || !matchesIdentity(c,intent.identity))continue;
    const allPassages=byCharacter.get(c.id)||[];
    const present=new Set(allPassages.flatMap(p=>p.features));
    if(!intent.requiredThemes.every(name=>present.has(name)) || intent.excludedThemes.some(name=>present.has(name)))continue;
    const thematicBonus=p=>.15*intent.requiredThemes.filter(name=>p.features.includes(name)).length;
    const passages=allPassages.sort((a,b)=>(b.docScore+thematicBonus(b))-(a.docScore+thematicBonus(a))||a.id.localeCompare(b.id)).slice(0,3);
    if(!passages.length)continue;
    let attributeScore=0;
    for(const [stat,direction] of Object.entries(intent.preferences)){
      const value=Math.max(0,Math.min(20,Number(c.stats?.[stat])||0))/20;
      attributeScore+=direction>0?value:1-value;
    }
    attributeScore/=Math.max(1,Object.keys(intent.preferences).length);
    const relevance=passages[0].docScore*.75+(passages[1]?.docScore||0)*.15+(passages[2]?.docScore||0)*.1;
    // Do not invent a recommendation on text-only searches with no retrieved evidence.
    if(!hasStats && relevance===0 && intent.maxDifficulty===null && !intent.constraints.length && !intent.identity.required.length)continue;
    const score=hasStats ? .65*attributeScore+.35*relevance : relevance;
    const profile=statisticalProfile(c.stats);
    const numerical=stats.map(key=>`${labels[key]} ${c.stats[key]}`).join(', ');
    if(intent.identity.required.length || intent.identity.excluded.length)passages.unshift({
      id:`${c.id}:identity`,title:'Identité de la fiche',text:`${c.name}. Race déclarée : ${c.race}. Statistiques : ${numerical}.`
    });
    const facts=`Statistiques : ${numerical}. Profil suggéré par les statistiques : ${profile}.\n`+
      passages.map(p=>`[${p.id}] ${p.text}`).join('\n');
    ranked.push({id:c.id,name:c.name,race:c.race,difficulty:c.difficulty,classes:c.classes,stats:c.stats,profile,
      facts,score,attributeScore,relevance,passages:passages.map(p=>({id:p.id,title:p.title,text:p.text}))});
  }
  ranked.sort((a,b)=>b.score-a.score||a.id.localeCompare(b.id));
  return {candidates:ranked.slice(0,6),intent,mode:query?'stats+embeddings+bm25':'stats+bm25'};
}

export async function embedQuery(message,index,key,fetcher=fetch){
  const response=await fetcher(`https://generativelanguage.googleapis.com/v1beta/models/${index.model}:embedContent`,{
    method:'POST',headers:{'Content-Type':'application/json','x-goog-api-key':key.trim()},
    signal:AbortSignal.timeout(15000),body:JSON.stringify({model:`models/${index.model}`,taskType:'RETRIEVAL_QUERY',
      outputDimensionality:index.dimensions,content:{parts:[{text:message}]}})
  });
  if(!response.ok)throw Error('Query embedding unavailable');
  const data=await response.json();
  return normalizeVector(data.embedding?.values,index.dimensions);
}
