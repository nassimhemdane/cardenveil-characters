/* Read-only A4 sheet renderer. Pagination measures the actual DOM at print dimensions. */
'use strict';
const sheets=document.querySelector('#sheets');
const escapeText=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const has=v=>v!==null&&v!==undefined&&v!==''&&(typeof v==='string'?v.replace(/<[^>]*>|&nbsp;/g,'').trim().length>0:Array.isArray(v)?v.some(has):typeof v==='object'?Object.values(v).some(has):true);
const names={nom:'Name',joueur:'Player',niveau:'Level',race:'Race',alignement:'Alignment',age:'Age',taille:'Height',poids:'Weight',yeux:'Eyes',peau:'Skin',cheveux:'Hair',force:'Strength',agilite:'Agility',esprit:'Spirit',social:'Social',pvMax:'Max HP',pvActuels:'Current HP',pvTemporaires:'Temporary HP',bonusPv:'HP bonus',initiative:'Initiative',mouvement:'Movement',perceptionPassive:'Passive Perception',seuilSauvegarde:'Save DC',seuilMiss:'Miss Threshold',volonte:'Willpower',deflexion:'Deflection',parade:'Parry',armure:'Armor',gardeBonus:'Guard bonus',bonus:'Bonus',bonusAttaque:"Attack bonus",initiativeBonus:'Initiative bonus',mouvementBonus:'Movement bonus',canalisation:'Channeling',inspiration:'Inspiration',fatigue:'Fatigue',mort:'Death',background:'Background',objectif:'Goal',liens:'Bonds',traitsSpeciaux:'Special traits',personnalite:'Personality',reputation:'Reputation',education:'Education',croyances:'Beliefs',cicatrices:'Scars',pulsion:'Drive',maniesEtTics:'Habits and tics',instinct:'Instinct',cardMin:'Min cards',cardMax:'Max cards',knownAbilities:'Known abilities',maxPreparedAbilities:'Max prepared',colorReductions:'Suit reductions',spade:'Spades',heart:'Hearts',club:'Clubs',diamond:'Diamonds',xpDepenses:'XP spent',xpDisponibles:'Available XP',de:'Die',forceAgi:'Strength / Agility',critique:'Critical',avantage:'Advantage',perfection:'Perfection',notes:'Notes',family:'Family',element:'Element',level:'Level',title:'Name',description:'Description',raretePrix:'Rarity / Price',enchantement:'Enchantment',vitesse:'Speed',weaponName:'Weapon',name:'Name',degats:'Damage',attributs:'Attributes',familySummary:'Family properties',catalystColor:'Focus suit',equipmentData:'Equipment properties',equipement:'Equipment',inventaire:'Inventory',or:'Gold',rations:'Rations',athletisme:'Athletics',resilience:'Resilience',discretion:'Stealth',representation:'Performance',perspicacite:'Insight'};
Object.assign(names,{acrobaties:'Acrobatics',escamotage:'Sleight of Hand',arcanes:'Arcana',culture:'Knowledge',survie:'Survival',nature:'Nature',tromperie:'Deception',dressage:'Animal Handling'});
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
  const heading=rest.querySelector('h3');if(heading&&!heading.textContent.endsWith(' (continued)'))heading.append(' (continued)');
  return rest;
}
/** Append prose, splitting only when it cannot fit or when totem continuation is requested. */
function flow(block,content,splitHere=false){
  content.append(block);if(fits(content))return content;
  if(!splitHere&&content.children.length>1){block.remove();content=page('Sheet — continued');content.append(block);if(fits(content))return content;}
  let guard=0;
  while(!fits(content)){
    if(++guard>50)throw Error('Text is too long to paginate.');
    const rest=splitBlock(block,content);
    if(!rest){block.remove();content=page('Sheet — continued');content.append(block);if(!fits(content)&&block.textContent.length===0)throw Error('This block cannot be paginated.');continue;}
    content=page('Sheet — continued');block=rest;content.append(block);
  }
  return content;
}

/** Keep the reference's empty writing boxes visible without inserting invented values. */
function referenceFields(c,keys){return keys.map(k=>`<div class="field"><small>${escapeText(label(k))}</small><div class="value">${has(c[k])?rich(c[k]):'&nbsp;'}</div></div>`).join('');}
/** Compare duplicate legacy totem text without typography or HTML differences. */
function sameProse(a,b){return plain(a).toLowerCase().replace(/[^\p{L}\p{N}]/gu,'')===plain(b).toLowerCase().replace(/[^\p{L}\p{N}]/gu,'');}
/** Build the reference-style three-column overview with stored game values. */
function overview(c){
  const layout=element('<div class="overview"><div class="stack"></div><div class="stack"></div><div class="stack"></div></div>');
  const [left,center,right]=layout.children;
  if(c.portrait)left.append(element(`<div class="box">${picture(c.portrait,'portrait')}</div>`));
  left.append(box('Attributes',Object.entries(groups).map(([stat,keys])=>`<div class="stat"><div class="stat-score"><b>${escapeText(c.stats[stat])}</b><small>${label(stat)}</small>${has(c.statBonuses?.[stat])?`<small>Bonus ${escapeText(c.statBonuses[stat])}</small>`:''}</div><div class="skills">${keys.filter(k=>c.skills[k]).map(k=>`<div class="skill"><span>${c.skills[k].trained?'●':'○'} ${label(k)}</span><i>${escapeText(c.skills[k].bonus)}</i></div>`).join('')}</div></div>`).join('')));
  center.append(box('Identity',`<div class="fields">${referenceFields(c.identity,['niveau','race','alignement','joueur'])}</div>`));
  center.append(box('Combat',`<div class="combat-fields">${values(c.derived)}${values(c.defense)}</div>`));
  if(c.weapons.some(w=>has(w)))center.append(box('Weapons',c.weapons.filter(has).map(w=>`<div class="narrative-card"><b>${escapeText(plain(w.nom))}</b><div>${compact(Object.fromEntries(Object.entries(w).filter(([k])=>k!=='nom')))}</div></div>`).join('')));
  right.append(box('Appearance',`<div class="fields">${referenceFields(c.identity,['age','taille','poids','yeux','peau','cheveux'])}</div>`));
  const narrative=box('Narrative','');
  for(const [k,v] of Object.entries(c.narrative))narrative.lastElementChild.append(element(`<div class="narrative-card"><b>${label(k)}</b><div>${has(v)?rich(v):'<span class="empty-rule"></span>'}</div></div>`));
  if(narrative.lastElementChild.children.length)right.append(narrative);
  return layout;
}
/** Render a non-editable, seven-column ability row based on htmls/verso.html. */
function ability(a){
  const cost=a.cost||{},color=cost.color||'';
  const reductions=[['incantation',cost.incantationReduction],['suit',cost.colorReduction],['awakening',cost.awakeningReduction],['mastery',cost.weaponMasteryReduction]].filter(([,v])=>Number(v));
  return element(`<section class="box ability ability-row" role="row">
    <div class="ability-visual" role="cell">${picture(a.image)}</div>
    <div class="ability-description" role="cell"><h3>${escapeText(plain(a.name))}</h3><div class="box-body rich">${rich(a.description)}</div><small class="prepared">Prepared: ${a.prepared?'Yes':'No'}</small></div>
    <div class="ability-value rich" role="cell">${rich(a.value.main)}${has(a.value.bonus)?`<small>Bonus : ${rich(a.value.bonus)}</small>`:''}</div>
    <div class="ability-cost" role="cell"><span class="cost ${['heart','diamond'].includes(color)?'red':''}">${escapeText(suits[color]||color)} ${escapeText(cost.total)}</span><div class="formula">${escapeText(cost.base)}${reductions.map(([,v])=>` − ${escapeText(v)}`).join('')} = ${escapeText(cost.total)}</div>${reductions.map(([k,v])=>`<small>${escapeText(k)} : −${escapeText(v)}</small>`).join('')}</div>
    <div class="rich" role="cell">${rich(a.incantation)}</div>
    <div class="rich" role="cell">${rich(a.save)}</div>
    <div class="rich" role="cell">${rich(a.usage)}</div>
  </section>`);
}
/** Create a repeated table heading so every printed continuation remains understandable. */
function abilityTable(content){
  const table=element('<div class="ability-table" role="table" aria-label="Abilities"></div>');
  table.append(element('<div class="ability-columns" role="row">'+['Image','Description','Value','Cost','Incantation','Saving throw','Usage'].map(t=>`<div role="columnheader">${t}</div>`).join('')+'</div>'));
  content.append(table);return table;
}
/** Keep ordinary rows together; exceptionally long descriptions continue across A4 sheets. */
function abilityPages(c){
  let content=page('Abilities — reverse');
  if(has(c.abilityControls.colorReductions))content.append(box('Ability cost reductions',compact(c.abilityControls.colorReductions),'reductions'));
  let table=abilityTable(content);
  for(const a of c.capacities){
    let row=ability(a);table.append(row);
    if(fits(content))continue;
    row.remove();
    if(table.children.length===1)table.remove();
    content=page('Abilities — continued');table=abilityTable(content);table.append(row);
    let guard=0;
    while(!fits(content)){
      if(++guard>50)throw Error('Ability text is too long to paginate.');
      const rest=splitBlock(row,content);
      if(!rest)throw Error('The properties of this ability exceed one A4 sheet.');
      content=page('Abilities — continued');table=abilityTable(content);row=rest;table.append(row);
    }
  }
  if(has(c.notes))content=flow(box('Personal notes',rich(c.notes)),content);
  // Blank ruled space is only decorative: never create a sheet just for empty lines.
  const notes=box('Personal notes','<div class="writing-lines"></div>','blank-notes');
  content.append(notes);if(!fits(content)||has(c.notes))notes.remove();
  return content;
}
/** Fill a two-column page with unbroken cards; oversize cards use full width then continuation. */
function cards(blocks,content){
  const title=content.textContent.includes('inventory')?'Equipment & inventory — continued':'Abilities — continued';
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
  let content=page();content.append(element(`<header class="sheet-heading"><h1>${escapeText(plain(c.identity.nom))}</h1><small>Cardenveil · Character sheet</small></header>`));
  const main=overview(c);content.append(main);const deferred=[];
  // Move narrative paragraphs out of an oversized overview before moving whole sections.
  const narrative=main.querySelector('.stack:last-child .box:last-child');
  if(narrative?.querySelector('h3')?.textContent==='Narrative'){
    while((!fits(content)||main.offsetHeight>650)&&narrative.lastElementChild.children.length){const item=narrative.lastElementChild.lastElementChild;deferred.unshift(box(item.firstElementChild.textContent,item.lastElementChild.innerHTML));item.remove();}
    if(!narrative.lastElementChild.children.length)narrative.remove();
  }
  while(!fits(content)){
    const stack=[...main.children].sort((a,b)=>b.offsetHeight-a.offsetHeight)[0];
    if(!stack.lastElementChild)throw Error('Too much content on the first page.');
    const block=stack.lastElementChild;block.remove();deferred.unshift(block);
  }
  if(has(c.totem))content=flow(box(`Totem — ${plain(c.totem.nom)}`,picture(c.totem.image)+rich(c.totem.description),'totem'),content,true);
  if(has(c.inventory.totem)&&!sameProse(c.inventory.totem,c.totem.description))content=flow(box('Totem — notes',rich(c.inventory.totem)),content,true);
  for(const block of deferred)content=flow(block,content,true);
  const mechanics=[];
  for(const [title,obj] of [['Progression',c.progression],['Cards and abilities',c.abilityControls],['Tokens',c.resources.tokens]])if(has(obj))mechanics.push(`<div class="narrative-card"><b>${title}</b><div>${compact(obj)}</div></div>`);
  for(const [title,items] of [['Weapon Masteries',c.weaponMasteries],['Elemental Masteries',c.elementalMasteries],['Feats',c.feats]])if(items.length)mechanics.push(`<div class="narrative-card"><b>${title}</b>${items.map(compact).join('<br>')}</div>`);
  for(const [title,v] of [['Cards and tokens',c.resources.cartesEtTokens],['Actions',c.actions],['Reactions',c.reactions],['Free tokens',c.tokens]])if(has(v))mechanics.push(`<div class="narrative-card"><b>${title}</b>${rich(v)}</div>`);
  if(mechanics.length)content=flow(box('Resources and masteries',`<div class="cards">${mechanics.join('')}</div>`),content,true);
  content=abilityPages(c);
  const inventory=[];
  for(const [slot,item] of Object.entries(c.equipment))if(has(item))inventory.push(box(label(slot),compact(item)));
  for(const item of c.inventoryItems)if(has(item))inventory.push(box(item.name||item.weaponName||'Item',compact(item)));
  for(const [title,v] of [['Equipment',c.inventory.equipement],['Inventory',c.inventory.inventaire]])if(has(v))inventory.push(box(title,rich(v)));
  if(has(c.resources.or)||has(c.resources.rations))inventory.unshift(box('Provisions',values({or:c.resources.or,rations:c.resources.rations})));
  if(inventory.length){
    content=page('Equipment & inventory');const inventoryPage=content.parentElement;content=cards(inventory,content);
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

  const overflow=[...document.querySelectorAll('.page-content')].some(p=>!fits(p));
  if(overflow)throw Error('A sheet exceeds the A4 page size.');
  document.title=`${plain(c.identity.nom)} — A4 sheet`;
  document.querySelector('#print-status').textContent=`${count} A4 sheets`;
  document.querySelector('#print-button').disabled=false;
  document.body.dataset.ready='true';return count;
}
document.querySelector('#print-button').addEventListener('click',()=>window.print());
if(!new URLSearchParams(location.search).has('audit'))fetch('/data/characters.json').then(r=>{if(!r.ok)throw Error('Catalogue unavailable');return r.json();}).then(data=>{
  const id=new URLSearchParams(location.search).get('character');const c=data.find(c=>c.id===id);if(!c)throw Error('Character not found');return renderSheet(c);
}).catch(error=>{document.querySelector('#print-status').textContent=error.message;document.body.dataset.error=error.message;});
