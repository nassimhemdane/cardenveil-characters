/* Read-only A4 sheet renderer. Pagination measures the actual DOM at print dimensions. */
'use strict';
const sheets=document.querySelector('#sheets');
const escapeText=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const has=v=>v!==null&&v!==undefined&&v!==''&&(typeof v==='string'?v.replace(/<[^>]*>|&nbsp;/g,'').trim().length>0:Array.isArray(v)?v.some(has):typeof v==='object'?Object.values(v).some(has):true);
const names={nom:'Nom',joueur:'Joueur',niveau:'Niveau',race:'Race',alignement:'Alignement',age:'Âge',taille:'Taille',poids:'Poids',yeux:'Yeux',peau:'Peau',cheveux:'Cheveux',force:'Force',agilite:'Agilité',esprit:'Esprit',social:'Social',pvMax:'PV max',pvActuels:'PV actuels',pvTemporaires:'PV temporaires',bonusPv:'Bonus PV',initiative:'Initiative',mouvement:'Mouvement',perceptionPassive:'Perception passive',seuilSauvegarde:'Seuil sauvegarde',seuilMiss:'Seuil de miss',volonte:'Volonté',deflexion:'Déflexion',parade:'Parade',armure:'Armure',gardeBonus:'Bonus garde',bonus:'Bonus',bonusAttaque:"Bonus d’attaque",initiativeBonus:'Bonus initiative',mouvementBonus:'Bonus mouvement',canalisation:'Canalisation',inspiration:'Inspiration',fatigue:'Fatigue',mort:'Mort',background:'Background',objectif:'Objectif',liens:'Liens',traitsSpeciaux:'Traits spéciaux',personnalite:'Personnalité',reputation:'Réputation',education:'Éducation',croyances:'Croyances',cicatrices:'Cicatrices',pulsion:'Pulsion',maniesEtTics:'Manies et tics',instinct:'Instinct',cardMin:'Carte min',cardMax:'Carte max',knownAbilities:'Capacités connues',maxPreparedAbilities:'Préparées max',colorReductions:'Réductions par couleur',spade:'Pique',heart:'Cœur',club:'Trèfle',diamond:'Carreau',xpDepenses:'XP dépensés',xpDisponibles:'XP disponibles',de:'Dé',forceAgi:'Force / Agilité',critique:'Critique',avantage:'Avantage',perfection:'Perfection',notes:'Notes',family:'Famille',element:'Élément',level:'Niveau',title:'Nom',description:'Description',raretePrix:'Rareté / Prix',enchantement:'Enchantement',vitesse:'Vitesse',weaponName:'Arme',name:'Nom',degats:'Dégâts',attributs:'Attributs',familySummary:'Propriétés de famille',catalystColor:'Couleur catalyseur',equipmentData:'Propriétés équipement',equipement:'Équipement',inventaire:'Inventaire',or:'Or',rations:'Rations',athletisme:'Athlétisme',resilience:'Résilience',discretion:'Discrétion',representation:'Représentation',perspicacite:'Perspicacité'};
const label=k=>names[k]||k.replace(/([a-z])([A-Z])/g,'$1 $2').replace(/^./,s=>s.toUpperCase());
const groups={force:['athletisme','resilience'],agilite:['acrobaties','discretion','escamotage'],esprit:['arcanes','investigation','perception','culture','survie','nature'],social:['persuasion','tromperie','intimidation','representation','perspicacite','dressage']};
const suits={spade:'♠',heart:'♥',diamond:'♦',club:'♣'};

/** Keep rich sheet text without allowing attributes or active HTML into the page. */
function rich(value){
  if(Array.isArray(value))return value.map(rich).join('<br>');
  const template=document.createElement('template');template.innerHTML=String(value??'').replace(/>\s+</g,'><');
  const walk=node=>{
    if(node.nodeType===3)return escapeText(node.nodeValue);
    if(['SCRIPT','STYLE','IFRAME','OBJECT','SVG','MATH'].includes(node.nodeName))return '';
    const body=[...node.childNodes].map(walk).join('');
    const tag={B:'strong',STRONG:'strong',I:'em',EM:'em',P:'p',DIV:'p',UL:'ul',OL:'ol',LI:'li'}[node.nodeName];
    return node.nodeName==='BR'?'<br>':tag?`<${tag}>${body}</${tag}>`:body;
  };
  return [...template.content.childNodes].map(walk).join('');
}
/** Extract a plain title without exposing HTML in headings or attributes. */
function plain(v){const t=document.createElement('template');t.innerHTML=rich(v);return t.content.textContent.trim();}
/** Only generated local assets are allowed as image sources. */
function picture(ref,cls=''){return typeof ref==='string'&&ref.startsWith('/assets/')?`<img class="${cls}" src="${escapeText(ref)}" alt="Illustration">`:'';}
/** Construct a measured sheet block from generated safe markup. */
function element(html){const t=document.createElement('template');t.innerHTML=html;return t.content.firstElementChild;}
/** Render all supplied nested game values, including zero, with explicit labels. */
function values(obj){return Object.entries(obj||{}).filter(([,v])=>has(v)).map(([k,v])=>`<div class="field"><small>${escapeText(label(k))}</small><div class="value">${typeof v==='object'&&!Array.isArray(v)?values(v):rich(v)}</div></div>`).join('');}
/** Compact labeled properties for inventory and mechanics. */
function compact(obj){return Object.entries(obj||{}).filter(([,v])=>has(v)).map(([k,v])=>`<span class="pair"><b>${escapeText(label(k))} :</b> ${typeof v==='object'&&!Array.isArray(v)?compact(v):rich(v)}</span>`).join(' ');}
/** Standard framed section with a detachable body for overflow pagination. */
function box(title,body,cls=''){return element(`<section class="box ${cls}"><h3>${escapeText(plain(title))}</h3><div class="box-body rich">${body}</div></section>`);}

/** Add a physical A4 page with a fixed usable area and reserved footer. */
function page(title=''){
  const sheet=element('<article class="a4"><div class="page-content"></div><footer class="page-footer"></footer></article>');
  sheets.append(sheet);const content=sheet.firstElementChild;
  if(title)content.append(element(`<h2 class="page-label">${escapeText(title)}</h2>`));
  return content;
}
/** Check measured layout, never hide or crop overflowing text. */
function fits(content){return content.scrollHeight<=content.clientHeight+1;}

/** Clone either side of a text offset while retaining nested bold and paragraphs. */
function fragmentAt(body,offset,before){
  const walker=document.createTreeWalker(body,NodeFilter.SHOW_TEXT);let node,remaining=offset;
  while((node=walker.nextNode())){if(remaining<=node.length)break;remaining-=node.length;}
  const range=document.createRange();range.selectNodeContents(body);
  if(node){if(before)range.setEnd(node,remaining);else range.setStart(node,remaining);}
  else if(!before)range.collapse(false);
  return range.cloneContents();
}
/** Split oversized prose at a word boundary; each continuation keeps its heading. */
function splitBlock(block,content){
  const original=block.querySelector('.box-body').cloneNode(true),text=original.textContent;
  const body=block.querySelector('.box-body');let low=0,high=text.length;
  while(low<high){const mid=Math.ceil((low+high)/2);body.replaceChildren(fragmentAt(original,mid,true));if(fits(content))low=mid;else high=mid-1;}
  let cut=low;while(cut>0&&cut<text.length&&!/\s/.test(text[cut-1]))cut--;
  if(cut===0)cut=low;
  if(cut<1){body.replaceChildren(...original.cloneNode(true).childNodes);return null;}
  body.replaceChildren(fragmentAt(original,cut,true));
  const rest=block.cloneNode(true);rest.querySelectorAll('img').forEach(img=>img.remove());
  rest.querySelector('.box-body').replaceChildren(fragmentAt(original,cut,false));
  rest.querySelector('.box-body').querySelectorAll('img').forEach(img=>img.remove());
  const heading=rest.querySelector('h3');if(heading&&!heading.textContent.endsWith(' (suite)'))heading.append(' (suite)');
  return rest;
}
/** Append prose, splitting only when it cannot fit or when totem continuation is requested. */
function flow(block,content,splitHere=false){
  content.append(block);if(fits(content))return content;
  if(!splitHere&&content.children.length>1){block.remove();content=page('Fiche — suite');content.append(block);if(fits(content))return content;}
  let guard=0;
  while(!fits(content)){
    if(++guard>50)throw Error('Texte trop volumineux pour la pagination.');
    const rest=splitBlock(block,content);
    if(!rest){block.remove();content=page('Fiche — suite');content.append(block);if(!fits(content)&&block.textContent.length===0)throw Error('Bloc impossible à paginer.');continue;}
    content=page('Fiche — suite');block=rest;content.append(block);
  }
  return content;
}

/** Build the reference-style three-column overview with stored game values. */
function overview(c){
  const layout=element('<div class="overview"><div class="stack"></div><div class="stack"></div><div class="stack"></div></div>');
  const [left,center,right]=layout.children;
  if(c.portrait)left.append(element(`<div class="box">${picture(c.portrait,'portrait')}</div>`));
  left.append(box('Caractéristiques',Object.entries(groups).map(([stat,keys])=>`<div class="stat"><div class="stat-score"><b>${escapeText(c.stats[stat])}</b><small>${label(stat)}</small>${has(c.statBonuses?.[stat])?`<small>Bonus ${escapeText(c.statBonuses[stat])}</small>`:''}</div><div class="skills">${keys.filter(k=>c.skills[k]).map(k=>`<div class="skill"><span>${c.skills[k].trained?'●':'○'} ${label(k)}</span><i>${escapeText(c.skills[k].bonus)}</i></div>`).join('')}</div></div>`).join('')));
  center.append(box('Identité',`<div class="fields">${values(Object.fromEntries(['joueur','niveau','race','alignement'].map(k=>[k,c.identity[k]])))}</div>`));
  center.append(box('Combat',`<div class="combat-fields">${values(c.derived)}${values(c.defense)}</div>`));
  if(c.weapons.some(w=>has(w)))center.append(box('Armes',c.weapons.filter(has).map(w=>`<div class="narrative-card"><b>${escapeText(plain(w.nom))}</b><div>${compact(Object.fromEntries(Object.entries(w).filter(([k])=>k!=='nom')))}</div></div>`).join('')));
  right.append(box('Physique',`<div class="fields">${values(Object.fromEntries(['age','taille','poids','yeux','peau','cheveux'].map(k=>[k,c.identity[k]])))}</div>`));
  const narrative=box('Narratif','');
  for(const [k,v] of Object.entries(c.narrative).filter(([,v])=>has(v)))narrative.lastElementChild.append(element(`<div class="narrative-card"><b>${label(k)}</b><div>${rich(v)}</div></div>`));
  if(narrative.lastElementChild.children.length)right.append(narrative);
  return layout;
}
/** Compact ability card: illustration, full rich description, values and complete cost. */
function ability(a){
  const cost=a.cost||{},color=cost.color||'';
  return element(`<section class="box ability"><header class="ability-header"><h3>${escapeText(plain(a.name))}</h3><span class="cost ${['heart','diamond'].includes(color)?'red':''}">${escapeText(suits[color]||color)} ${escapeText(cost.total)}</span></header><div class="box-body rich">${picture(a.image)}${rich(a.description)}<div class="ability-details">${[['Valeur',a.value.main],['Bonus',a.value.bonus],['Incantation',a.incantation],['Sauvegarde',a.save],['Utilisation',a.usage],['Préparée',a.prepared?'Oui':'Non']].filter(([,v])=>has(v)).map(([k,v])=>`<span><strong>${k} :</strong> ${rich(v)}</span>`).join('')}<div class="formula">Coût ${escapeText(cost.base)} − ${escapeText(cost.incantationReduction)} incant. − ${escapeText(cost.colorReduction)} couleur − ${escapeText(cost.awakeningReduction)} éveil − ${escapeText(cost.weaponMasteryReduction)} maîtrise = ${escapeText(cost.total)}</div></div></div></section>`);
}
/** Fill a two-column page with unbroken cards; oversize cards use full width then continuation. */
function cards(blocks,content){
  const title=content.textContent.includes('inventaire')?'Équipement & inventaire — suite':'Capacités — suite';
  const newGrid=()=>{const g=element('<div class="cards"><div class="stack"></div><div class="stack"></div></div>');content.append(g);return g;};
  let grid=newGrid();
  for(const block of blocks){
    let placed=false;
    for(const column of [...grid.children].sort((a,b)=>a.offsetHeight-b.offsetHeight)){
      column.append(block);if(fits(content)){placed=true;break;}block.remove();
    }
    if(placed)continue;
    if(!grid.textContent.trim()&&!grid.querySelector('img'))grid.remove();
    content=page(title);grid=newGrid();grid.firstElementChild.append(block);
    if(!fits(content)){
      block.remove();grid.remove();content=flow(block,content,true);grid=newGrid();
    }
  }
  if(!grid.textContent.trim()&&!grid.querySelector('img'))grid.remove();
  return content;
}

/** Lay out the whole sheet. Inventory begins on page three or later after core content. */
function layout(c,size){
  sheets.replaceChildren();sheets.style.setProperty('--body-size',`${size}pt`);
  let content=page();content.append(element(`<header class="sheet-heading"><h1>${escapeText(plain(c.identity.nom))}</h1><small>Cardenveil · Fiche de personnage</small></header>`));
  const main=overview(c);content.append(main);const deferred=[];
  // Move narrative paragraphs out of an oversized overview before moving whole sections.
  const narrative=main.querySelector('.stack:last-child .box:last-child');
  if(narrative?.querySelector('h3')?.textContent==='Narratif'){
    while((!fits(content)||main.offsetHeight>650)&&narrative.lastElementChild.children.length){const item=narrative.lastElementChild.lastElementChild;deferred.unshift(box(item.firstElementChild.textContent,item.lastElementChild.innerHTML));item.remove();}
    if(!narrative.lastElementChild.children.length)narrative.remove();
  }
  while(!fits(content)){
    const stack=[...main.children].sort((a,b)=>b.offsetHeight-a.offsetHeight)[0];
    if(!stack.lastElementChild)throw Error('Première page trop chargée.');
    const block=stack.lastElementChild;block.remove();deferred.unshift(block);
  }
  if(has(c.totem))content=flow(box(`Totem — ${plain(c.totem.nom)}`,picture(c.totem.image)+rich(c.totem.description),'totem'),content,true);
  if(has(c.inventory.totem))content=flow(box('Totem — notes',rich(c.inventory.totem)),content,true);
  for(const block of deferred)content=flow(block,content,true);
  const mechanics=[];
  for(const [title,obj] of [['Progression',c.progression],['Cartes et capacités',c.abilityControls],['Tokens',c.resources.tokens]])if(has(obj))mechanics.push(`<div class="narrative-card"><b>${title}</b><div>${compact(obj)}</div></div>`);
  for(const [title,items] of [['Maîtrises d’armes',c.weaponMasteries],['Maîtrises élémentaires',c.elementalMasteries],['Dons',c.feats]])if(items.length)mechanics.push(`<div class="narrative-card"><b>${title}</b>${items.map(compact).join('<br>')}</div>`);
  for(const [title,v] of [['Cartes et tokens',c.resources.cartesEtTokens],['Actions',c.actions],['Réactions',c.reactions],['Tokens libres',c.tokens],['Notes',c.notes]])if(has(v))mechanics.push(`<div class="narrative-card"><b>${title}</b>${rich(v)}</div>`);
  if(mechanics.length)content=flow(box('Ressources et maîtrises',`<div class="cards">${mechanics.join('')}</div>`),content,true);
  // Keep the visual boundary between overview and spells, but reuse continuation pages.
  if(sheets.children.length===1)content=page('Capacités');
  else content=flow(box('Capacités',''),content);
  content=cards(c.capacities.map(ability),content);
  const inventory=[];
  for(const [slot,item] of Object.entries(c.equipment))if(has(item))inventory.push(box(label(slot),compact(item)));
  for(const item of c.inventoryItems)if(has(item))inventory.push(box(item.name||item.weaponName||'Objet',compact(item)));
  for(const [title,v] of [['Équipement',c.inventory.equipement],['Inventaire',c.inventory.inventaire]])if(has(v))inventory.push(box(title,rich(v)));
  if(has(c.resources.or)||has(c.resources.rations))inventory.unshift(box('Provisions',values({or:c.resources.or,rations:c.resources.rations})));
  if(inventory.length){
    content=page('Équipement & inventaire');const inventoryPage=content.parentElement;content=cards(inventory,content);
    if([...sheets.children].indexOf(inventoryPage)>2)sheets.insertBefore(inventoryPage,sheets.children[2]);
  }
  [...sheets.children].forEach((sheet,i)=>{sheet.lastElementChild.innerHTML=`<span>${escapeText(plain(c.identity.nom))}</span><span>${i+1} / ${sheets.children.length}</span>`;});
  return sheets.children.length;
}
/** Wait for every source image before measuring page breaks, including cached images. */
async function loadImages(c){
  const refs=[c.portrait,c.totem.image,...c.capacities.map(a=>a.image)].filter(Boolean);
  await Promise.all(refs.map(src=>new Promise(resolve=>{const image=new Image();image.onload=resolve;image.onerror=resolve;image.src=src;})));
  await document.fonts.ready;
}
/** Public entry point also used by the browser regression audit. */
async function renderSheet(c){
  await loadImages(c);
  let count=layout(c,9);
  if(count>3){const smaller=layout(c,8.5);if(smaller>=count)count=layout(c,9);else count=smaller;}
  const overflow=[...document.querySelectorAll('.page-content')].some(p=>!fits(p));
  if(overflow)throw Error('Une feuille dépasse le format A4.');
  document.title=`${plain(c.identity.nom)} — Fiche A4`;
  document.querySelector('#print-status').textContent=`${count} feuilles A4`;
  document.querySelector('#print-button').disabled=false;
  document.body.dataset.ready='true';return count;
}
document.querySelector('#print-button').addEventListener('click',()=>window.print());
if(!new URLSearchParams(location.search).has('audit'))fetch('/data/characters.json').then(r=>{if(!r.ok)throw Error('Catalogue indisponible');return r.json();}).then(data=>{
  const id=new URLSearchParams(location.search).get('character');const c=data.find(c=>c.id===id);if(!c)throw Error('Personnage introuvable');return renderSheet(c);
}).catch(error=>{document.querySelector('#print-status').textContent=error.message;document.body.dataset.error=error.message;});
