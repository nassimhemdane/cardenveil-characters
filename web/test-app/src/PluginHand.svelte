<script>
  import {handCap,maxTokensFor,fatiguePenaltyFor} from './vendor/deck.js';
  let {player,game,selected,folded,pick,dispatch,onfold,ontoken,onreplace,onexchange,onreorder,disabled=false}=$props();
  let tokensOpen=$state(false),scheme=$state('classic'),hovered=$state(null),dragId=$state(null);
  const names={force:'Force',agilite:'Agilité',esprit:'Esprit',social:'Social'};
  const colors={force:'#b34c43',agilite:'#397a42',esprit:'#2d6499',social:'#765496'};
  const cardColors={'♥':'#ef4444','♦':'#d97706','♣':'#16a34a','♠':'#6b7280'};
  let cards=$derived([...player.hand.map(card=>({card,crystal:false})),...player.crystallized.map(card=>({card,crystal:true}))]);
  let cap=$derived(maxTokensFor(player));
  let full=$derived(player.hand.length>=handCap(player));
  let drawBlocked=$derived(disabled||full||!!player.pendingHalfling||game.pendingExchanges?.length>0);
  let penalty=$derived(fatiguePenaltyFor(player.race,player.fatigue));
  function token(key,mode){tokensOpen=false;ontoken(key,mode);}
  function cardAction(e,action){e.stopPropagation();dispatch(action);}
</script>

<div class="plugin-hand" style={`--fan-width:${Math.max(320,cards.length*64+160)}px`}>
  {#if !folded}
  <div class="plugin-fan-scroll">
    <div class="hand-row plugin-fan" style={`height:${cards.length?120:26}px;width:${Math.max(320,cards.length*64+160)}px`} aria-label="Main de cartes">
      {#each cards as {card,crystal},i (card.id)}
        {@const active=selected===card.id}
        {@const blocked=(player.grayedCards??[]).includes(card.id)}
        <div class="plugin-card-wrap" class:is-active={active} style={`left:calc(50% + ${(i-(cards.length-1)/2)*64}px);z-index:${active||hovered===card.id?50:i}`} onpointerenter={()=>hovered=card.id} onpointerleave={()=>hovered=null}>
          <button class="playing-card plugin-card" class:crystallized={crystal} class:chosen={active} aria-label={`${card.value}${card.suit}${crystal?' cristallisée':''}`} aria-pressed={active} onclick={()=>pick(card)} draggable={!crystal} ondragstart={e=>{dragId=card.id;e.dataTransfer.setData('text/plain',card.id)}} ondragend={()=>dragId=null} ondragover={e=>e.preventDefault()} ondrop={e=>{e.preventDefault();onreorder(e.dataTransfer.getData('text/plain'),card.id);dragId=null;}} style={`color:${scheme==='classic'?(card.isRed?'#dc2626':'#111827'):cardColors[card.suit]};background:${crystal?'#ef9b9b':'#fff'};border:${crystal?'2.5px solid #ef4444':'1.5px solid #d1d5db'}`}>
            <span class="plugin-corner"><span>{card.value}</span><span>{card.suit}</span></span>
            <span class="plugin-suit">{card.suit}</span>
            <span class="plugin-corner plugin-corner-bottom"><span>{card.value}</span><span>{card.suit}</span></span>
            {#if blocked}<span class="blocked-veil"></span>{/if}
            {#if penalty>0 && i===cards.length-1}<span class="value-badge" title={`Fatigue : −${penalty}`}>−{penalty}</span>{/if}
          </button>
          {#if !dragId && !tokensOpen}
          <div class="plugin-card-overlay" class:open={active}>
            {#if crystal||(!blocked&&player.hand.length>player.spiritBounds)}<button class="discard-action" title="Défausser" aria-label="Défausser" onclick={e=>cardAction(e,{type:'DISCARD',cardId:card.id,from:crystal?'crystallized':'hand'})}>▶️</button>{/if}
            {#if !crystal}<button class="crystal-action" title="Cristalliser" aria-label="Cristalliser" disabled={player.spiritBounds<1} onclick={e=>cardAction(e,{type:'CRYSTALLIZE',cardId:card.id})}>✦</button><button class="gray-action" title={blocked?'Débloquer':'Bloquer'} onclick={e=>cardAction(e,{type:'TOGGLE_GRAY',cardId:card.id})}>◑</button>{/if}
          </div>
          {/if}
        </div>
      {:else}<p class="plugin-empty">Aucune carte</p>{/each}
    </div>
  </div>
  {/if}
  <div class="plugin-bar">
    <div class="plugin-bar-left"><button onclick={onfold}>{folded?'🃏 Afficher':'🃏 Replier'}</button>{#if selected&&player.race==='nimbri'}<button title="Diviser la carte" onclick={()=>dispatch({type:'SPLIT_CARD',cardId:selected})}>✂</button>{/if}{#if game.pendingExchanges?.length}<span title="Échange en attente">⏳</span>{/if}</div>
    <div class="plugin-bar-center"><button class="plugin-draw" title="Piocher une carte" disabled={drawBlocked} onclick={()=>dispatch({type:'DRAW'})}>{player.pendingHalfling?'Choix en cours…':full?`Pleine ${player.hand.length}/${handCap(player)}`:`Piocher ${player.hand.length}/${handCap(player)}`}{#if player.spiritBounds>0}<span> ✦×{player.spiritBounds}</span>{/if}</button><button class="scheme-toggle" title="Changer les couleurs des cartes" onclick={()=>scheme=scheme==='classic'?'color':'classic'}>🎨</button>{#if player.race==='tieffelin'&&player.tieflingDrawEligible}<button title="Pioche Tieffelin" disabled={full} onclick={()=>dispatch({type:'DRAW_SPADE'})}>♠</button>{/if}</div>
    <div class="plugin-bar-right"><button class="token-chip token-grid" title="Tokens — Carte et Combat" aria-expanded={tokensOpen} onclick={()=>tokensOpen=!tokensOpen}><span>🎟</span>{#each Object.keys(names) as key}<span style={`color:${colors[key]}`}>{player.tokens[key]}</span>{/each}</button></div>
  </div>
  {#if tokensOpen}
    <div class="plugin-token-backdrop"><section class="plugin-token-modal" role="dialog" aria-label="Tokens — usage"><div class="plugin-modal-title"><strong>Tokens — usage</strong><button title="Fermer les tokens" onclick={()=>tokensOpen=false}>✕</button></div>{#each Object.entries(names) as [key,name]}<div class="plugin-token-line"><strong style={`color:${colors[key]}`}>{name}</strong><span style={`color:${colors[key]}`}>{player.tokens[key]}/{cap[key]}</span><button disabled={player.tokens[key]<1} title={`${name} : usage carte`} style={`color:${colors[key]};border-color:${colors[key]};background:${colors[key]}15`} onclick={()=>token(key,'card')}>Carte</button><button disabled={player.tokens[key]<1} title={`${name} : usage combat`} onclick={()=>token(key,'combat')}>Combat</button></div>{/each}</section></div>
  {/if}
</div>
{#if selected}<div class="plugin-extra-actions"><button onclick={onexchange}>Échange simulé</button><button onclick={onreplace}>Remplacer · MJ</button><span>Carte sélectionnée · les actions sont aussi accessibles directement sur la carte.</span></div>{/if}
