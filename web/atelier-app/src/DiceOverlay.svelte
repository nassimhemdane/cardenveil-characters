<script>
  import {onMount} from 'svelte';
  import {diceEvents} from './diceService.js';
  let active=$state(null),frame=$state(null),settled=$state(false),problem=$state(''),viewportHeight=$state(window.visualViewport?.height??innerHeight);
  let queue=[],timer=null,autoClose=null,portraitUrl=null;
  function releasePortrait(){if(portraitUrl){URL.revokeObjectURL(portraitUrl);portraitUrl=null;}}
  function show(request){clearTimeout(timer);clearTimeout(autoClose);releasePortrait();active=request;const portrait=request.data.portrait;if(typeof portrait==='string'&&portrait.startsWith('data:')){try{const [header,encoded]=portrait.split(',');const raw=atob(encoded);portraitUrl=URL.createObjectURL(new Blob([Uint8Array.from(raw,c=>c.charCodeAt(0))],{type:header.slice(5).split(';')[0]}));active={...request,data:{...request.data,portrait:portraitUrl}};}catch{active={...request,data:{...request.data,portrait:''}};}}settled=false;problem='';timer=setTimeout(()=>{problem='Le lancer n’a pas pu aboutir. Fermez puis relancez.';settled=true;active.reject(new Error(problem));},45000);}
  function close(){clearTimeout(timer);clearTimeout(autoClose);releasePortrait();active=null;settled=false;if(queue.length)show(queue.shift());}
  function url(data){const params=new URLSearchParams({label:data.label||'Lancer de dés',plainLabel:data.label||'Jet',formula:data.formula||'',playerId:data.playerId||'local-mj',rollId:data.rollId,playerName:data.playerName||'',portrait:data.portrait||'',portraitImage:data.portraitIsImage?'1':'0',self:'1',diceSpec:JSON.stringify(data.diceSpec),seed:String(data.seed),modifier:String(data.modifier||0),color:'#181818',keep:data.keep||'',zoomCrit:data.zoomCrit?'1':'0',noCrit:data.noCrit?'1':'0',critFrom:data.critFrom==null?'':String(data.critFrom),staged:data.staged?'1':'0'});if(data.rolls){params.set('rolls',data.rolls.join(','));params.set('types',data.diceTypes.join(','));params.set('total',String(data.total));}if(data.breakdown)params.set('breakdown',JSON.stringify(data.breakdown));if(data.tags)params.set('tags',data.tags);return '/atelier/dice.html?'+params;}
  onMount(()=>{
    const resize=()=>viewportHeight=window.visualViewport?.height??innerHeight;
    window.addEventListener('resize',resize);window.visualViewport?.addEventListener('resize',resize);
    const request=e=>{if(active&&!settled)queue.push(e.detail);else show(e.detail);};
    const message=e=>{
      if(e.origin!==location.origin||e.source!==frame?.contentWindow||e.data?.type!=='cardenveil-dice-result'||e.data.result?.rollId!==active?.data.rollId||settled)return;
      clearTimeout(timer);settled=true;const result=e.data.result;
      active.resolve(result);autoClose=setTimeout(close,6500);
    };
    const key=e=>{if(e.key==='Escape'&&settled)close();};
    diceEvents.addEventListener('roll',request);window.addEventListener('message',message);window.addEventListener('keydown',key);
    return()=>{releasePortrait();window.removeEventListener('resize',resize);window.visualViewport?.removeEventListener('resize',resize);diceEvents.removeEventListener('roll',request);window.removeEventListener('message',message);window.removeEventListener('keydown',key);clearTimeout(timer);clearTimeout(autoClose);};
  });
</script>
{#if active}<section class="dice-overlay" style={`--dice-frame-height:${Math.max(140,Math.min(400,viewportHeight-88))}px;max-height:${viewportHeight-24}px`} role="dialog" aria-label="Lancer de dés 3D" aria-modal="false"><div class="dice-overlay-header"><span>{settled?'Résultat du lancer':'Les dés roulent…'}</span><button disabled={!settled} title="Fermer les dés" onclick={close}>✕</button></div>{#key active.data.rollId}<iframe bind:this={frame} title="Dés 3D Cardenveil" src={url(active.data)} allow="autoplay"></iframe>{/key}{#if problem}<p role="alert">{problem}</p>{/if}</section>{/if}
