/** Same-origin, human-verified recommendation endpoint. Keys remain in Pages secrets. */
import {MODEL, SYSTEM, ragSchema, validateRagRecommendations} from '../../web/recommendations-core.js';
import {RAG_VERSION, retrieve, embedQuery, identityIntent} from '../../web/rag-retrieval.js';

const json = (body, status=200) => Response.json(body, {status, headers:{'Cache-Control':'no-store'}});
// One current public index per isolate, invalidated by the asset ETag on every request.
let indexCache=null;

async function boundedJSON(request) {
  if (!request.headers.get('content-type')?.startsWith('application/json')) throw Error('body');
  const reader = request.body?.getReader();
  if (!reader) throw Error('body');
  const chunks=[]; let size=0;
  try {
    while (true) {
      const {done,value}=await reader.read(); if(done)break;
      size+=value.byteLength;
      if(size>4096) {await reader.cancel(); throw Error('body');}
      chunks.push(value);
    }
  } finally {reader.releaseLock();}
  const bytes=new Uint8Array(size); let offset=0;
  for(const part of chunks){bytes.set(part,offset);offset+=part.length;}
  return JSON.parse(new TextDecoder().decode(bytes));
}

export async function onRequestPost({request,env,waitUntil}) {
  const origin=new URL(request.url).origin;
  if(request.headers.get('origin')!==origin || request.headers.get('X-Cardenveil-Client')!=='catalogue')
    return json({detail:'Origine refusée.'},403);
  if(!env.GEMINI_API_KEY || !env.TURNSTILE_SECRET_KEY || !env.TURNSTILE_SITE_KEY ||
      env.GEMINI_FREE_TIER_CONFIRMED!=='1')return json({detail:'Recommandations non configurées.'},503);
  let body;
  try {body=await boundedJSON(request);} catch {return json({detail:'Requête JSON invalide ou trop longue.'},400);}
  if(typeof body.message!=='string' || !body.message.trim() || body.message.length>1000 ||
      typeof body.token!=='string' || !body.token || body.token.length>2048)
    return json({detail:'Phrase ou vérification manquante.'},400);
  const message=body.message.trim();
  try {
    const verification=await fetch('https://challenges.cloudflare.com/turnstile/v0/siteverify', {
      method:'POST',headers:{'Content-Type':'application/json'},signal:AbortSignal.timeout(10000),
      body:JSON.stringify({secret:env.TURNSTILE_SECRET_KEY.trim(),response:body.token,
        remoteip:request.headers.get('CF-Connecting-IP') || undefined})
    });
    const check=await verification.json();
    if(!check.success){
      const codes=Array.isArray(check['error-codes'])?check['error-codes']:[];
      if(codes.includes('invalid-input-secret') || codes.includes('missing-input-secret'))
        return json({detail:'Clé secrète Turnstile refusée. Vérifiez TURNSTILE_SECRET_KEY et son association à la Site key du même widget.',code:'turnstile_secret_invalid'},503);
      if(codes.includes('timeout-or-duplicate'))
        return json({detail:'La vérification a expiré ou a déjà été utilisée. Attendez le nouveau Success puis réessayez.',code:'turnstile_token_expired'},403);
      if(codes.includes('internal-error') || verification.status>=500 || verification.status===429)
        return json({detail:'Turnstile est temporairement indisponible. Réessayez.',code:'turnstile_unavailable',
          upstreamStatus:verification.status, errors:codes.filter(c=>['internal-error','invalid-input-response','timeout-or-duplicate','bad-request'].includes(c))},503);
      if(codes.includes('bad-request'))
        return json({detail:'Turnstile refuse la requête de validation. Vérifiez que les clés ont été copiées seules, sans nom de variable ni guillemets.',code:'turnstile_bad_request'},503);
      return json({detail:'Jeton Turnstile refusé. Rechargez la page et réessayez ; si cela persiste, vérifiez que les deux clés proviennent du même widget.',code:'turnstile_token_invalid'},403);
    }
    if(check.hostname!==new URL(request.url).hostname)
      return json({detail:'Le domaine validé par Turnstile ne correspond pas au site. Vérifiez les hostnames du widget.',code:'turnstile_hostname_mismatch'},403);
    if(check.action!=='recommend')
      return json({detail:'Le widget est une ancienne version. Rechargez complètement la page avant de réessayer.',code:'turnstile_action_mismatch'},403);
    const catalogueResponse=await env.ASSETS.fetch(new URL('/data/rag-index.json',origin));
    if(!catalogueResponse.ok)throw Error('catalogue');
    const etag=catalogueResponse.headers.get('etag');
    const index=etag && indexCache?.etag===etag ? indexCache.index : await catalogueResponse.json();
    if(etag)indexCache={etag,index};
    if(!index.version || !Array.isArray(index.characters) || !index.documents?.length)throw Error('catalogue');
    const digest=await crypto.subtle.digest('SHA-256',new TextEncoder().encode(RAG_VERSION+MODEL+SYSTEM+index.version+message));
    const hash=Array.from(new Uint8Array(digest),b=>b.toString(16).padStart(2,'0')).join('');
    const cacheKey=new Request(origin+'/_recommendation-cache/'+hash);
    const cached=await caches.default.match(cacheKey);
    if(cached)return json(await cached.json());
    let queryVector=null;
    const identity=identityIntent(index,message);
    if(!identity.only && index.embeddedDocuments===(index.embeddingRequiredDocuments??index.documents.length)){
      try{queryVector=await embedQuery(message,index,env.GEMINI_API_KEY);}catch{}
    }
    const retrieval=retrieve(index,message,queryVector);
    const candidates=retrieval.candidates;
    if(!candidates.length){
      const empty={matches:[],explanation:'Aucune fiche ne respecte ces contraintes avec les éléments disponibles.',retrieval:{mode:retrieval.mode}};
      waitUntil(caches.default.put(cacheKey,Response.json(empty,{headers:{'Cache-Control':'public, max-age=3600'}})));
      return json(empty);
    }
    if(identity.only){
      const result={explanation:'Personnages dont l’identité déclarée dans la fiche correspond à votre recherche.',
        matches:candidates.map(c=>({character_id:c.id,comment:identity.names.length?`La fiche demandée est celle de ${c.name}.`:`${c.name} correspond à votre demande : sa race est « ${c.race} ».`,
          evidence:c.passages[0].text,source_id:c.passages[0].id,stats:c.stats,profile:c.profile,race:c.race,
          sources:[{id:c.passages[0].id,title:c.passages[0].title}]})),
        retrieval:{mode:'structured-identity',version:RAG_VERSION}};
      waitUntil(caches.default.put(cacheKey,Response.json(result,{headers:{'Cache-Control':'public, max-age=3600'}})));
      return json(result);
    }
    // One query embedding at most, then one explanation call; never regenerate document vectors here.
    const response=await fetch(`https://generativelanguage.googleapis.com/v1beta/models/${MODEL}:generateContent`,{
      method:'POST',headers:{'Content-Type':'application/json','x-goog-api-key':env.GEMINI_API_KEY.trim()},
      signal:AbortSignal.timeout(45000),body:JSON.stringify({
        systemInstruction:{parts:[{text:SYSTEM}]},
        contents:[{role:'user',parts:[{text:JSON.stringify({request:message,intent:retrieval.intent,
          candidates:candidates.map(({id,name,race,stats,profile,difficulty,classes,passages})=>({id,name,race,stats,profile,difficulty,classes,sources:passages}))})}]}],
        generationConfig:{temperature:0.1,maxOutputTokens:2300,responseMimeType:'application/json',responseJsonSchema:ragSchema}
      })
    });
    if(!response.ok)return json({detail:response.status===429?'Quota gratuit atteint. Réessayez plus tard.':'Gemini est temporairement indisponible.'},response.status===429?429:503);
    const data=await response.json(), candidate=data.candidates?.[0];
    if(candidate?.finishReason!=='STOP')throw Error('incomplete');
    const text=(candidate.content?.parts||[]).filter(p=>!p.thought).map(p=>p.text||'').join('');
    const result=validateRagRecommendations(JSON.parse(text),candidates);
    for(const match of result.matches){
      const candidate=candidates.find(c=>c.id===match.character_id);
      match.stats=candidate.stats;match.profile=candidate.profile;match.race=candidate.race;
      match.sources=candidate.passages.map(p=>({id:p.id,title:p.title}));
    }
    result.retrieval={mode:retrieval.mode,version:RAG_VERSION,embedded:index.embeddedDocuments,total:index.documents.length,
      embeddingRequired:index.embeddingRequiredDocuments??index.documents.length};
    waitUntil(caches.default.put(cacheKey,Response.json(result,{headers:{'Cache-Control':'public, max-age=3600'}})));
    return json(result);
  } catch {
    // Never echo upstream errors, keys or model output into public responses/logs.
    return json({detail:'Réponse indisponible ou non vérifiable. Réessayez ou utilisez les filtres.'},503);
  }
}
