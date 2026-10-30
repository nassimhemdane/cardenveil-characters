/** Same-origin, human-verified recommendation endpoint. Keys remain in Pages secrets. */
import {MODEL, SYSTEM, schema, candidatesFrom, validateRecommendations} from '../../web/recommendations-core.js';

const json = (body, status=200) => Response.json(body, {status, headers:{'Cache-Control':'no-store'}});

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
      body:JSON.stringify({secret:env.TURNSTILE_SECRET_KEY,response:body.token,
        remoteip:request.headers.get('CF-Connecting-IP') || undefined})
    });
    const check=await verification.json();
    if(!check.success || check.hostname!==new URL(request.url).hostname || check.action!=='recommend')
      return json({detail:'Vérification anti-abus échouée. Réessayez.'},403);
    const catalogueResponse=await env.ASSETS.fetch(new URL('/data/recommendation-catalog.json',origin));
    if(!catalogueResponse.ok)throw Error('catalogue');
    const candidates=candidatesFrom(await catalogueResponse.json());
    const source=JSON.stringify(candidates);
    if(!candidates.length || source.length>120000)throw Error('catalogue');
    const digest=await crypto.subtle.digest('SHA-256',new TextEncoder().encode(MODEL+SYSTEM+source+message));
    const hash=Array.from(new Uint8Array(digest),b=>b.toString(16).padStart(2,'0')).join('');
    const cacheKey=new Request(origin+'/_recommendation-cache/'+hash);
    const cached=await caches.default.match(cacheKey);
    if(cached)return json(await cached.json());
    // No tools, search grounding, retries or model fallback: exactly one bounded call.
    const response=await fetch(`https://generativelanguage.googleapis.com/v1beta/models/${MODEL}:generateContent`,{
      method:'POST',headers:{'Content-Type':'application/json','x-goog-api-key':env.GEMINI_API_KEY},
      signal:AbortSignal.timeout(45000),body:JSON.stringify({
        systemInstruction:{parts:[{text:SYSTEM}]},
        contents:[{role:'user',parts:[{text:JSON.stringify({request:message,candidates})}]}],
        generationConfig:{temperature:0.1,maxOutputTokens:2300,responseMimeType:'application/json',responseJsonSchema:schema}
      })
    });
    if(!response.ok)return json({detail:response.status===429?'Quota gratuit atteint. Réessayez plus tard.':'Gemini est temporairement indisponible.'},response.status===429?429:503);
    const data=await response.json(), candidate=data.candidates?.[0];
    if(candidate?.finishReason!=='STOP')throw Error('incomplete');
    const text=(candidate.content?.parts||[]).filter(p=>!p.thought).map(p=>p.text||'').join('');
    const result=validateRecommendations(JSON.parse(text),candidates);
    waitUntil(caches.default.put(cacheKey,Response.json(result,{headers:{'Cache-Control':'public, max-age=3600'}})));
    return json(result);
  } catch {
    // Never echo upstream errors, keys or model output into public responses/logs.
    return json({detail:'Réponse indisponible ou non vérifiable. Réessayez ou utilisez les filtres.'},503);
  }
}
