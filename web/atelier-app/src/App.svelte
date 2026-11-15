<script>
  import { onMount } from 'svelte';
  import CharacterSheet from './vendor/CharacterSheet.svelte';
  import PluginHand from './PluginHand.svelte';
  import DiceOverlay from './DiceOverlay.svelte';
  import CompactBubble from './CompactBubble.svelte';
  import VirtualTable from './VirtualTable.svelte';
  import {roll3D} from './diceService.js';
  import { RACES, SUITS_INFO, handCap, maxTokensFor, fatiguePenaltyFor, drawNormal } from './vendor/deck.js';
  import { createEmptyCharacterSheet, importCharacterSheet, saveCharacterSheet, tokensFromStats, effectiveStats, computeDerived, normalizeRaceName } from './vendor/characterSheet.js';
  import { runAttack, weaponFlags } from './vendor/attackRoll.js';
  import { read, write, listen } from './storage.js';
  import { ACTOR, PARTNER, freshGame, reduce, rest } from './session.js';
  let game = $state(null), sheet = $state(null), ready = $state(false), error = $state(''), saved = $state('');
  let selected = $state(null), folded = $state(false), drawer = $state(false), catalogue = $state([]), catalogueId = $state(''), loading = $state(false);
  let suit = $state('♠'), value = $state('A'), crystal = $state(false), replace = $state(false), showCatalogue = $state(false);
  let agility = $state(false), exchangeCard = $state(''), showExchange = $state(false), restKind = $state(''), restDiscard = $state([]);
  let offline = $state(!navigator.onLine), revision = $state(0), attackResult = $state(null), advantage = $state(0), engagement = $state(0), attackBusy=$state(false);
  let player = $derived(game?.players?.[ACTOR]), cap = $derived(player ? maxTokensFor(player) : {});
  let selectedCard = $derived(player ? [...player.hand, ...player.crystallized].find(c => c.id === selected) : null);
  let pendingExchange = $derived(game?.pendingExchanges?.[0]);
  let sequence = Promise.resolve();
  let handVisible=$state(false),compactEnabled=$state(false);
  let panelOrder=$state(['sheet','map','mj','history']), draggedPanel=$state(''), panelDropTarget=$state(null);
  let dockNode=$state(null),dockHeight=$state(0);
  let headerNode=$state(null),navBottom=$state(72);
  $effect(()=>{const node=headerNode;if(!node)return;const update=()=>navBottom=Math.max(0,node.getBoundingClientRect().bottom);update();const observer=new ResizeObserver(update);observer.observe(node);window.addEventListener('scroll',update,{passive:true});return()=>{observer.disconnect();window.removeEventListener('scroll',update);};});
  $effect(()=>{const node=dockNode;if(!node){dockHeight=0;return;}const update=()=>dockHeight=node.getBoundingClientRect().height;update();const observer=new ResizeObserver(update);observer.observe(node);return()=>observer.disconnect();});
  const tokenNames = {force:'Force',agilite:'Agilité',esprit:'Esprit',social:'Social'};
  const combatNames = {force:'Double frappe',agilite:'Courber',esprit:'Réverbération',social:'Attaque alliée'};
  function panelDragOver(event,target){event.preventDefault();const summary=event.currentTarget.querySelector(':scope>summary'),rect=(summary||event.currentTarget).getBoundingClientRect();panelDropTarget={id:target,after:event.clientY>rect.top+rect.height/2};}
  function panelDrop(target){if(!draggedPanel||draggedPanel===target){draggedPanel='';panelDropTarget=null;return;}const next=panelOrder.filter(id=>id!==draggedPanel),index=next.indexOf(target);next.splice(index+(panelDropTarget?.after?1:0),0,draggedPanel);panelOrder=next;localStorage.setItem('cardenveil-atelier-panel-order',JSON.stringify(next));draggedPanel='';panelDropTarget=null;}
  function panelMove(id,direction){const index=panelOrder.indexOf(id),target=index+direction;if(index<0||target<0||target>=panelOrder.length)return;const next=[...panelOrder];[next[index],next[target]]=[next[target],next[index]];panelOrder=next;localStorage.setItem('cardenveil-atelier-panel-order',JSON.stringify(next));}
  function persist(next) {
    game = next; saved = 'Enregistrement…';
    const snapshot = JSON.parse(JSON.stringify(next));
    sequence = sequence.catch(() => {}).then(() => write('game', snapshot)).then(() => saved = 'Enregistré sur cet appareil').catch(e => { error = `Sauvegarde impossible : ${e.message}. Gardez cet onglet ouvert.`; saved = 'Non enregistré'; });
  }
  function dispatch(action) {
    if (offline || !game) return;
    const next = reduce(JSON.parse(JSON.stringify(game)), action);
    if (JSON.stringify(next) === JSON.stringify(game)) { error = 'Action indisponible : vérifiez les cartes, les jetons et la limite de main.'; return; }
    error = ''; persist(next);
  }
  function pick(card) { selected = selected === card.id ? null : card.id; }
  const cardImage = (card, c = false) => `/atelier/cards/${({'♠':'S','♣':'C','♥':'H','♦':'D'})[card.suit]}-${card.value}${c ? '-c' : ''}.png`;
  function applySheet(row, previous) {
    sheet = row?.data ?? null;
    if (!game || !sheet) return;
    let next = JSON.parse(JSON.stringify(game));
    const p = next.players[ACTOR]; p.name = sheet.identity?.nom || 'Mon personnage';
    if (previous && previous.derived?.fatigue !== sheet.derived?.fatigue) p.fatigue = Math.max(0,Math.min(3,Number(sheet.derived?.fatigue)||0));
    const race = normalizeRaceName(sheet.identity?.race);
    if (p.race !== race && RACES.some(r => r.id === race)) next = reduce(next, {type:'SET_RACE',race});
    if (!RACES.some(r => r.id === race)) next.players[ACTOR].race = null;
    const statsChanged = JSON.stringify(previous?.stats) !== JSON.stringify(sheet.stats);
    if (statsChanged) next = reduce(next, {type:'SYNC_TOKENS',tokens:tokensFromStats(effectiveStats(sheet)), counts:sheet.resources?.tokens});
    persist(next);
  }
  onMount(() => {
    let disposed = false;
    try { const stored=JSON.parse(localStorage.getItem('cardenveil-atelier-panel-order')); if(Array.isArray(stored)&&stored.length===4)panelOrder=stored; } catch {}
    const onOffline = () => offline = true, onOnline = () => offline = false;
    const onPanelDrag = event => {if(!draggedPanel)return;const panel=event.target.closest?.('.page-accordion');if(!panel)return;event.preventDefault();const rect=panel.querySelector(':scope>summary').getBoundingClientRect(),after=event.clientY>rect.top+rect.height/2,title=panel.querySelector(':scope>summary strong')?.textContent,id=title==='Map de jeu'?'map':title==='Fiche de personnage'?'sheet':title==='Gestion MJ'?'mj':'history';document.querySelectorAll('.page-accordion.drop-before,.page-accordion.drop-after').forEach(node=>node.classList.remove('drop-before','drop-after'));panel.classList.add(after?'drop-after':'drop-before');panelDropTarget={id,after};};
    const clearPanelDrag = () => document.querySelectorAll('.page-accordion.drop-before,.page-accordion.drop-after').forEach(node=>node.classList.remove('drop-before','drop-after'));
    window.addEventListener('offline',onOffline); window.addEventListener('online',onOnline);
    document.addEventListener('dragover',onPanelDrag);document.addEventListener('dragend',clearPanelDrag);document.addEventListener('drop',clearPanelDrag);
    const off = listen('sheet', row => { const old = sheet; applySheet(row, old); });
    (async () => {
      try {
        const cached = await read('game');
        game = cached?.players?.[ACTOR] ? cached : freshGame();
        const row = await read('sheet');
        if (row) applySheet(row, row.data);
        else await saveCharacterSheet(ACTOR,'local',createEmptyCharacterSheet());
        if (!disposed) ready = true;
        const requested = new URLSearchParams(location.search).get('character');
        if (requested) { await loadCatalogue(); catalogueId = requested; await openCatalogueCharacter(); }
      } catch(e) { error = `Impossible d'ouvrir la sauvegarde locale : ${e.message}`; }
    })();
    return () => { disposed = true; off(); window.removeEventListener('offline',onOffline); window.removeEventListener('online',onOnline);document.removeEventListener('dragover',onPanelDrag);document.removeEventListener('dragend',clearPanelDrag);document.removeEventListener('drop',clearPanelDrag); };
  });
  async function loadCatalogue() {
    if (catalogue.length) return;
    loading = true;
    try { const res = await fetch('/data/characters.json'); if (!res.ok) throw new Error('Catalogue indisponible'); catalogue = await res.json(); }
    catch(e) { error = e.message; } finally { loading = false; }
  }
  async function openCatalogueCharacter() {
    const character = catalogue.find(c => c.id === catalogueId); if (!character) { error = 'Sélectionnez un personnage du catalogue.'; return; }
    if (sheet?.identity?.nom && !confirm('Remplacer la fiche locale par ce personnage ? La main actuelle est conservée.')) return;
    try { await importCharacterSheet(ACTOR,'local',JSON.stringify(character)); dispatch({type:'SYNC_TOKENS',tokens:tokensFromStats(effectiveStats(sheet)),counts:sheet.resources?.tokens}); revision++; showCatalogue = false; error = ''; }
    catch(e) { error = e.message; }
  }
  async function reset() {
    if (!confirm('Effacer la fiche, les cartes, les jetons et le journal de ce bac à sable ?')) return;
    try { await sequence; game = freshGame(); await write('game',game); await saveCharacterSheet(ACTOR,'local',createEmptyCharacterSheet()); selected = null; attackResult = null; revision++; error = ''; }
    catch(e) { error = e.message; }
  }
  function giveCard() {
    dispatch(replace && selectedCard && player.hand.some(c => c.id === selected)
      ? {type:'SWAP_CARD',oldCardId:selected,suit,value,source:'normal'}
      : {type:'GIVE_CARDS',mode:'specific',cards:[{suit,value}],crystal});
    selected = null;
  }
  function beginExchange() {
    if (!selectedCard || !player.hand.some(c => c.id === selected) || player.hand.length <= player.spiritBounds) { error = 'Sélectionnez une carte normale disponible pour l’échange.'; return; }
    let next = JSON.parse(JSON.stringify(game));
    next = reduce(next,{type:'REGISTER_PLAYER',playerId:PARTNER,name:'Allié fictif'});
    next.players[PARTNER].hand = [drawNormal(),drawNormal(),drawNormal()];
    next = reduce(next,{type:player.race === 'sporelin' ? 'SPORELIN_EXCHANGE' : 'PROPOSE_EXCHANGE',cardId:selected,targetId:PARTNER});
    if (!next.pendingExchanges.length) { error = 'Il faut un jeton Social pour proposer cet échange.'; return; }
    persist(next); showExchange = true;
  }
  function finishExchange(accept) {
    if (!pendingExchange || (accept && !exchangeCard)) return;
    dispatch({type: accept ? 'ACCEPT_EXCHANGE' : 'DECLINE_EXCHANGE',playerId:PARTNER,exchangeId:pendingExchange.id,cardId:exchangeCard});
    showExchange = false; selected = null; exchangeCard = '';
  }
  async function doRest() {
    try {
      const next = rest(game,restKind,restDiscard);
      const d = sheet.derived, maximum = Number(d.pvMax) || 0;
      await saveCharacterSheet(ACTOR,'local',{...sheet,derived:{...d,pvActuels:restKind === 'long' ? maximum : Math.min(maximum,(Number(d.pvActuels)||0)+Math.floor(maximum/2)),fatigue:next.players[ACTOR].fatigue}});
      persist(next); restKind = ''; restDiscard = [];
    } catch(e) { error = e.message; }
  }
  async function attack(weapon) {
    if(attackBusy)return;
    attackBusy=true;
    try {
      const result = await runAttack({...weapon,seuilMiss:computeDerived(sheet).seuilMiss},effectiveStats(sheet),{race:player.race,bonus:computeDerived(sheet).bonusAttaque,advantage:Number(advantage),engagement:Number(engagement)},async(count,sides,keep)=>{
        const result=await roll3D({label:`Attaque : ${weapon.nom}`,formula:`${count}d${sides}`,playerId:ACTOR,diceSpec:[{count,sides}],modifier:0,keep:keep==='max'?'high':keep==='min'?'low':'',staged:true,zoomCrit:true,noCrit:weaponFlags(weapon,player.race).brute,critFrom:player.race==='gobelin'?sides-1:undefined});
        return result.rolls;
      });
      if (!result) throw new Error('Dé d’arme invalide.');
      attackResult = result;
      dispatch({type:'USE_CAPACITY',capacityName:`Attaque : ${weapon.nom}`,formula:weapon.de,total:result.total,rolls:result.stages?.flatMap(s => s.dice) ?? []});
    } catch(e) { error = e.message; } finally {attackBusy=false;}
  }
</script>

<header bind:this={headerNode} class="sandbox-header"><a class="brand" href="/">CARDENVEIL</a><nav aria-label="Navigation principale"><a href="/">Personnages</a><a href="/statistiques/">Statistiques</a><a href="/regles/">Règles & docs</a><a href="/atelier/" aria-current="page">Atelier</a><a href="/gm/">Agent MJ</a></nav></header>
<main class="sandbox">
  {#if error}<div class="notice error" role="alert">{error}<button onclick={() => error = ''} aria-label="Fermer le message">×</button></div>{/if}
  {#if offline}<div class="notice" role="status">Vous êtes hors connexion. La dernière main est conservée ; les commandes reprendront au retour du réseau.</div>{/if}
  {#if !ready}<p role="status">{error ? 'Le stockage du navigateur doit être autorisé pour ouvrir l’Atelier.' : 'Ouverture de l’Atelier…'}</p>{:else}
  <details class="target-accordion" ontoggle={e=>e.currentTarget.open&&loadCatalogue()}><summary><strong>{player.name}</strong><span>Changer de personnage</span></summary><div class="target-content"><label>Personnage<select bind:value={catalogueId}><option value="">{loading ? 'Chargement…' : 'Choisir un personnage'}</option>{#each catalogue as c}<option value={c.id}>{c.identity.nom} — {c.identity.race}</option>{/each}</select></label><button class="primary" disabled={!catalogueId} onclick={openCatalogueCharacter}>Ouvrir</button><button class="danger" onclick={reset}>Réinitialiser</button><small>{saved || 'Sauvegarde locale'}</small></div></details>
  <div class="accordion-stack">
  <details class="page-accordion" class:drop-before={panelDropTarget?.id==='map'&&!panelDropTarget.after} class:drop-after={panelDropTarget?.id==='map'&&panelDropTarget.after} style={`order:${panelOrder.indexOf('map')}`} open ondragover={e=>panelDragOver(e,'map')} ondrop={()=>panelDrop('map')}><summary draggable="true" ondragstart={()=>draggedPanel='map'} ondragend={()=>{draggedPanel='';panelDropTarget=null}}><span class="drag-handle">⠿</span><strong>Map de jeu</strong></summary><VirtualTable {sheet} /></details>
  <details class="page-accordion" class:drop-before={panelDropTarget?.id==='sheet'&&!panelDropTarget.after} class:drop-after={panelDropTarget?.id==='sheet'&&panelDropTarget.after} style={`order:${panelOrder.indexOf('sheet')}`} open ondragover={e=>panelDragOver(e,'sheet')} ondrop={()=>panelDrop('sheet')}><summary draggable="true" ondragstart={()=>draggedPanel='sheet'} ondragend={()=>{draggedPanel='';panelDropTarget=null}}><span class="drag-handle">⠿</span><strong>Fiche de personnage</strong></summary><div class="accordion-content">
  <section class="surface table-section" aria-label="Main et jetons">
    {#if agility && selectedCard}<div class="inline-panel">Dépenser 1 Agilité et remplacer la carte sélectionnée : {#each SUITS_INFO as s}<button onclick={() => { dispatch({type:'USE_AGILITE',cardId:selected,suit:s.symbol});agility=false;selected=null; }}>{s.symbol} {s.label}</button>{/each}</div>{/if}
    {#if player.pendingHalfling}<div class="inline-panel"><strong>Halfling : conservez une carte</strong>{#each player.pendingHalfling as card}<button onclick={() => dispatch({type:'HALFLING_CHOOSE',cardId:card.id})}>{card.value}{card.suit}</button>{/each}</div>{/if}
    {#if pendingExchange}<div class="inline-panel"><strong>Allié fictif · échange de {pendingExchange.fromCard.value}{pendingExchange.fromCard.suit}</strong><label>Carte reçue<select bind:value={exchangeCard}><option value="">Choisir…</option>{#each game.players[PARTNER].hand as c}<option value={c.id}>{c.value}{c.suit}</option>{/each}</select></label><button disabled={!exchangeCard} onclick={() => finishExchange(true)}>Accepter à sa place</button><button onclick={() => finishExchange(false)}>Refuser et rembourser</button></div>{/if}
    <div class="table-footer"><span>Emplacements d’Esprit : <strong>{player.spiritBounds}</strong></span><span>Défausse : <strong>{game.discard.length}</strong></span><label>Fatigue <select value={player.fatigue} onchange={e=>dispatch({type:'SET_FATIGUE',val:Number(e.currentTarget.value)})}>{#each [0,1,2,3] as n}<option value={n}>{n}{n === 3 ? ' — Mort' : ''}</option>{/each}</select></label><button onclick={()=>restKind='court'}>Repos court</button><button onclick={()=>restKind='long'}>Repos long</button>{#if player.race==='illithid'}<button onclick={()=>dispatch({type:'DEVOUR_MIND'})}>Dévoration mentale</button>{/if}</div>
  </section>
  {#if restKind}<section class="surface"><h2>Préparer le repos {restKind}</h2><p>Les {player.spiritBounds} premières cartes seront cristallisées pour consommer les emplacements d’Esprit. Réordonnez la main avant de confirmer. Choisissez les autres cartes à défausser avant de compléter la main.</p><div class="actions">{#each player.hand.slice(player.spiritBounds) as card}<label><input type="checkbox" value={card.id} bind:group={restDiscard}> {card.value}{card.suit}</label>{/each}<button class="primary" onclick={doRest}>Confirmer le repos</button><button onclick={()=>{restKind='';restDiscard=[];}}>Annuler</button></div></section>{/if}
  <section class="surface sheet-section"><div class="section-heading"><div><p class="eyebrow">FICHE INTERACTIVE</p><h2>Votre personnage, en détail.</h2></div><small>Importer JSON / ZIP ou modifier une fiche vide</small></div><div class="sheet-frame">{#key revision}<CharacterSheet playerId={ACTOR} roomId="local" gameState={game} onAction={dispatch} />{/key}</div></section>
  {#if sheet?.weapons?.length}<section class="surface"><h2>Attaques d’armes</h2><div class="inline-panel"><label>Avantage / désavantage<input type="number" min="-10" max="10" bind:value={advantage}></label><label>Engagement<input type="number" min="0" max="10" bind:value={engagement}></label>{#each sheet.weapons as w}<button onclick={()=>attack(w)}>⚔ {w.nom} · {w.de}</button>{/each}</div>{#if attackResult}<output class="attack-result"><strong>{attackResult.total} dégâts</strong><p>{attackResult.breakdown?.join('\n')}</p></output>{/if}</section>{/if}
  </div></details>
  <details class="page-accordion" style={`order:${panelOrder.indexOf('mj')}`} ondragover={e=>e.preventDefault()} ondrop={()=>panelDrop('mj')}><summary draggable="true" ondragstart={()=>draggedPanel='mj'}><span class="drag-handle">⠿</span><strong>Gestion MJ</strong></summary><section class="surface mj-panel"><div class="form-grid"><label>Race<select value={player.race||''} onchange={async e=>{const race=e.currentTarget.value; await saveCharacterSheet(ACTOR,'local',{...sheet,identity:{...sheet.identity,race}});revision++;}}><option value="">Sans race</option>{#each RACES as r}<option value={r.id}>{r.label}</option>{/each}</select></label><label>Limite de main<input type="number" min="0" max="15" value={player.maxHandSize} onchange={e=>dispatch({type:'SET_MAX_HAND',val:e.currentTarget.value})}></label><label>Pioche min.<input type="number" min="1" max={player.maxDrawValue} value={player.minDrawValue} onchange={e=>dispatch({type:'SET_DRAW_RANGE',field:'minDrawValue',val:e.currentTarget.value})}></label><label>Pioche max.<input type="number" min={player.minDrawValue} max="13" value={player.maxDrawValue} onchange={e=>dispatch({type:'SET_DRAW_RANGE',field:'maxDrawValue',val:e.currentTarget.value})}></label></div><div class="form-grid">{#each Object.entries(tokenNames) as [key,name]}<div><label>{name} · réserve<input type="number" min="0" max={cap[key]} value={player.tokens[key]} onchange={e=>dispatch({type:'SET_TOKENS',token:key,val:e.currentTarget.value})}></label><label>Maximum<input type="number" min="0" max="10" value={player.maxTokens[key]} onchange={e=>dispatch({type:'SET_MAX_TOKENS',token:key,val:e.currentTarget.value})}></label></div>{/each}</div><div class="inline-panel"><label>Enseigne<select bind:value={suit}>{#each SUITS_INFO as s}<option value={s.symbol}>{s.symbol} {s.label}</option>{/each}</select></label><label>Valeur<select bind:value={value}>{#each ['2','3','4','5','6','7','8','9','10','J','Q','K','A'] as v}<option>{v}</option>{/each}</select></label><label><input type="checkbox" bind:checked={crystal}> Cristallisée</label><label><input type="checkbox" bind:checked={replace}> Remplacer la sélection</label><button class="primary" onclick={giveCard}>Appliquer</button><button onclick={()=>dispatch({type:'GIVE_CARDS',count:1})}>Carte aléatoire</button></div></section></details>
  <details class="page-accordion history" style={`order:${panelOrder.indexOf('history')}`} ondragover={e=>e.preventDefault()} ondrop={()=>panelDrop('history')}><summary draggable="true" ondragstart={()=>draggedPanel='history'}><span class="drag-handle">⠿</span><strong>Journal d’actions</strong><span>{game.logs.length} / 200</span></summary><ol>{#each [...game.logs].reverse() as entry}<li><time>{new Date(entry.ts).toLocaleTimeString('fr-FR')}</time><span><strong>{entry.playerName}</strong> {entry.msg}</span></li>{:else}<li>Aucune action.</li>{/each}</ol></details>
  </div>
  <footer><a href="/regles/">Consulter les règles →</a></footer>
  {/if}
</main>
{#if ready && handVisible}
<div bind:this={dockNode} class="hand-dock" class:is-folded={folded} aria-label="Main flottante"><PluginHand disabled={offline} {player} {game} {selected} {folded} {pick} {dispatch} onfold={() => folded=!folded} onreplace={()=>{replace=true;drawer=true;}} onexchange={beginExchange} ontoken={(key,mode)=>{if(mode==='combat')dispatch({type:'SPEND_TOKEN',token:key});else if(key==='social')beginExchange();else if(key==='agilite'){agility=true;if(!selectedCard)error='Sélectionnez une carte pour choisir une enseigne.';}else dispatch({type:key==='force'?'DRAW_FORCE':'USE_ESPRIT'});}} onreorder={(fromId,toId)=>{const from=player.hand.findIndex(c=>c.id===fromId),to=player.hand.findIndex(c=>c.id===toId);if(from<0||to<0||from===to)return;const next=JSON.parse(JSON.stringify(game));const [card]=next.players[ACTOR].hand.splice(from,1);next.players[ACTOR].hand.splice(to,0,card);persist(next);}} /></div>
{/if}
{#if ready}<nav class="edge-tools" aria-label="Outils flottants">
  <button style={`bottom:${handVisible?dockHeight+24:20}px`} class="edge-toggle hand-toggle" aria-label={handVisible?'Masquer la main':'Afficher la main'} title={handVisible?'Masquer la main':'Afficher la main'} aria-pressed={handVisible} onclick={()=>handVisible=!handVisible}><svg viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linejoin="round"><rect x="8" y="5" width="12" height="16" rx="2"/><path d="M6 18 2 4a2 2 0 0 1 1.4-2.4L12 0"/><path d="m14 9 3 3-3 3-3-3z"/></svg></button>
  <button style={`top:${navBottom+12}px`} class="edge-toggle compact-toggle" aria-label={compactEnabled?'Masquer le compact':'Afficher le compact'} title={compactEnabled?'Masquer le compact':'Afficher le compact'} aria-pressed={compactEnabled} onclick={()=>compactEnabled=!compactEnabled}><svg viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"><rect x="4" y="2" width="16" height="20" rx="2"/><circle cx="12" cy="8" r="2.5"/><path d="M8 15c0-4 8-4 8 0M8 18h8"/></svg></button>
</nav><CompactBubble enabled={compactEnabled} onAction={dispatch} />{/if}
<DiceOverlay />
