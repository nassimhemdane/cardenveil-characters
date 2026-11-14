import {createServer} from 'node:http';
import {readFileSync,existsSync,mkdtempSync,createReadStream,mkdirSync,writeFileSync} from 'node:fs';
import {tmpdir} from 'node:os';
import path from 'node:path';
import {spawn} from 'node:child_process';
import {fileURLToPath} from 'node:url';
const publicRoot=fileURLToPath(new URL('../../public/',import.meta.url));
const browser=process.env.CHROME_PATH || 'C:/Program Files/Google/Chrome/Application/chrome.exe';
const server=createServer((req,res)=>{
  const name=path.resolve(publicRoot,'.'+decodeURIComponent(req.url.split('?')[0]));
  if(!name.startsWith(publicRoot)){res.writeHead(403).end();return;}
  const target=path.extname(name)?name:path.join(name,'index.html');
  if(!existsSync(target)){res.writeHead(404).end();return;}
  const types={'.js':'application/javascript','.css':'text/css','.html':'text/html; charset=utf-8','.json':'application/json','.png':'image/png','.zip':'application/zip'};
  res.writeHead(200,{'Content-Type':types[path.extname(target)]||'application/octet-stream'});createReadStream(target).pipe(res);
});
await new Promise(r=>server.listen(0,'127.0.0.1',r));
const origin=`http://127.0.0.1:${server.address().port}`;
const profile=mkdtempSync(path.join(tmpdir(),'cardenveil-test-'));
const child=spawn(browser,['--headless','--use-angle=swiftshader','--enable-unsafe-swiftshader','--no-first-run','--remote-debugging-port=0',`--user-data-dir=${profile}`,'about:blank'],{stdio:'ignore',windowsHide:true});
const delay=ms=>new Promise(r=>setTimeout(r,ms));
let ws;
try{
  const active=path.join(profile,'DevToolsActivePort');
  for(let i=0;i<100&&!existsSync(active);i++)await delay(100);
  const port=readFileSync(active,'utf8').split('\n')[0];
  const targets=await fetch(`http://127.0.0.1:${port}/json/list`).then(r=>r.json());
  ws=new WebSocket(targets.find(t=>t.type==='page').webSocketDebuggerUrl);
  await new Promise((r,j)=>{ws.onopen=r;ws.onerror=j;});
  let id=0;const waiting=new Map(),errors=[];
  ws.onmessage=({data})=>{const m=JSON.parse(data);if(m.id){const p=waiting.get(m.id);waiting.delete(m.id);m.error?p.reject(Error(m.error.message)):p.resolve(m.result);}else if(m.method==='Runtime.consoleAPICalled'&&m.params.type==='error')errors.push(m.params.args.map(a=>a.description||a.value).join(' '));else if(m.method==='Runtime.exceptionThrown')errors.push(m.params.exceptionDetails.exception?.description||m.params.exceptionDetails.text);else if(m.method==='Page.javascriptDialogOpening')send('Page.handleJavaScriptDialog',{accept:true});};
  function send(method,params={}){return new Promise((resolve,reject)=>{const current=++id;waiting.set(current,{resolve,reject});ws.send(JSON.stringify({id:current,method,params}));});}
  await send('Runtime.enable');await send('Page.enable');
  await send('Emulation.setDeviceMetricsOverride',{width:1440,height:1100,deviceScaleFactor:1,mobile:false});
  await send('Page.navigate',{url:origin+'/atelier/'});
  await delay(500);
  async function evaluate(expression){const result=await send('Runtime.evaluate',{expression,awaitPromise:true,returnByValue:true});if(result.exceptionDetails)throw Error((result.exceptionDetails.exception?.description||result.exceptionDetails.text)+'\nBrowser errors: '+errors.join('\n'));return result.result.value;}
  const report=await evaluate(`(async()=>{
    const pause=()=>new Promise(r=>setTimeout(r,80));
    async function until(fn,label){for(let i=0;i<400;i++){if(fn())return;await pause();}throw Error('Timeout '+label+' '+document.querySelector('.notice')?.textContent+' '+document.body.innerText.slice(-300));}
    function awaitToken(){setTimeout(()=>document.querySelector('[title="Esprit : usage carte"]').click(),0)}
    const click=t=>{if(t==='＋ Emplacement'){document.querySelector('.token-chip').click();awaitToken();return;}const b=t==='＋ Piocher'?document.querySelector('[title="Piocher une carte"]'):[...document.querySelectorAll('button')].find(b=>b.textContent.trim()===t||b.title===t);if(!b)throw Error('Missing '+t);b.click();};
    const cards=()=>document.querySelectorAll('.plugin-fan .playing-card:not(.crystallized)');
    await until(()=>document.querySelector('.target-accordion'),'mount');
    if(document.querySelector('.plugin-draw'))throw Error('Hand should be hidden on initial load');
    if(!document.querySelector('.plugin-draw')){document.querySelector('.hand-toggle').click();await until(()=>document.querySelector('.plugin-draw'),'show default-hidden hand');}
    const draw=document.querySelector('.plugin-draw');if(draw.disabled||getComputedStyle(draw).backgroundColor!=='rgb(36, 112, 58)'||draw.getBoundingClientRect().height<34)throw Error('Enabled draw should be large and green');
    click('＋ Piocher');await until(()=>cards().length===1,'draw');
    const geometry=cards()[0].getBoundingClientRect();if(geometry.width!==80||geometry.height!==120)throw Error('Plugin card geometry mismatch '+geometry.width+'×'+geometry.height);
    click('＋ Emplacement');await pause();cards()[0].click();await pause();click('Cristalliser');
    await until(()=>document.querySelector('.plugin-fan .playing-card.crystallized'),'crystallization');
    click('＋ Piocher');await pause();
    const pair=document.querySelectorAll('.plugin-card-wrap');if(pair.length!==2||Math.abs(pair[1].getBoundingClientRect().left-pair[0].getBoundingClientRect().left)!==64)throw Error('Plugin spread mismatch');
    cards()[0].click();await pause();click('Échange simulé');
    await until(()=>document.body.innerText.includes('Allié fictif · échange'),'exchange');click('Refuser et rembourser');await pause();
    if(document.body.innerText.includes('Allié fictif · échange'))throw Error('Exchange not cleared');
    const gmSummary=[...document.querySelectorAll('.page-accordion>summary')].find(node=>node.textContent.includes('Gestion MJ'));if(!gmSummary)throw Error('Missing Gestion MJ accordion');gmSummary.click();await pause();const fatigue=document.querySelector('.table-footer select');fatigue.value='2';fatigue.dispatchEvent(new Event('change',{bubbles:true}));await pause();
    if(!document.querySelector('.value-badge'))throw Error('Fatigue missing');
    document.querySelector('.target-accordion>summary').click();await until(()=>document.querySelector('.target-content select')?.options.length>1,'catalogue');
    const select=document.querySelector('.target-content select');select.value=select.options[1].value;select.dispatchEvent(new Event('change',{bubbles:true}));await pause();document.querySelector('.target-content .primary').click();
    await until(()=>document.querySelector('.target-accordion>summary strong')?.textContent!=='Mon personnage','import');
    await until(()=>document.querySelector('.sheet-frame').textContent.includes('COMPÉTENCES'),'sheet');
    if(document.querySelector('.skill-row button'))throw Error('Skill pin still displayed');
    if([...document.querySelectorAll('.sheet-frame button')].some(b=>b.textContent.includes('📌')))throw Error('Pin still present in sheet');
    click('NARRATIF');await pause();if(document.querySelector('.narrative-card button'))throw Error('Narrative + still present');
    click('CAPACITÉS');await pause();
    if(getComputedStyle(document.querySelector('.capacity-grid')).gridTemplateColumns.split(' ').length!==2)throw Error('Capacity grid should have two columns on desktop');
    const description=document.querySelector('.capacity-description');
    if(description && (description.scrollHeight>description.clientHeight+1 || getComputedStyle(description).webkitLineClamp==='2'))throw Error('Capacity description truncated');
    const expand=document.querySelector('[title="Afficher toute la capacité"]');
    if(!expand)throw Error('Missing capacity + button');expand.click();await pause();
    const modalText=document.querySelector('.sheet-frame .fixed .rich-html');
    if(!modalText || getComputedStyle(modalText).color==='rgb(255, 255, 255)')throw Error('Capacity modal contrast');
    document.querySelector('.sheet-frame .fixed [title="Fermer"]').click();await pause();
    click('INVENTAIRE');await pause();
    const add=document.querySelector('[title="Ajouter un objet ou une arme sans passer par ÉDITION"]');add.click();await pause();
    const inventoryRows=document.querySelectorAll('.sheet-frame .fixed button.text-gray-100');
    if(!inventoryRows.length)throw Error('Inventory add list missing');
    for(const row of inventoryRows){const rgb=getComputedStyle(row).color.match(/[\\d.]+/g).map(Number);if(rgb.slice(0,3).every(v=>v>200))throw Error('White inventory list text');}
    const template=[...inventoryRows].find(b=>!b.disabled);template.click();await pause();
    for(const input of document.querySelectorAll('.sheet-frame .fixed input')){const rgb=getComputedStyle(input).color.match(/[\\d.]+/g).map(Number);if(rgb.slice(0,3).every(v=>v>200))throw Error('White add/edit input text');}
    document.querySelector('.sheet-frame .fixed [title="Retour à la liste"]').click();await pause();document.querySelector('.sheet-frame .fixed [title="Fermer"]').click();await pause();
    for(const t of ['CAPACITÉS','INVENTAIRE','NARRATIF','MAÎTRISES','NOTES','COMPÉTENCES']){click(t);await pause();}
    const stat=document.querySelector('.sheet-frame [role="button"]');
    if(!stat)throw Error('Missing stat roll');stat.click();await pause();
    await until(()=>document.querySelector('.dice-overlay iframe')?.contentDocument?.body?.dataset.renderer==='three-rapier','actual 3D renderer');
    const diceDocument=document.querySelector('.dice-overlay iframe').contentDocument;
    if(new URL(document.querySelector('.dice-overlay iframe').src).searchParams.get('color')!=='#181818')throw Error('Dice should be black');
    if(!diceDocument.querySelector('canvas'))throw Error('No WebGL dice canvas');
    if(getComputedStyle(diceDocument.body).backgroundColor!=='rgb(255, 255, 255)')throw Error('Dice tray is not white');
    if(document.body.innerText.includes('Jet transmis à Owlbear'))throw Error('Remote roll');
    await until(()=>document.querySelector('.history').textContent.includes('utilise'),'physics result logged');
    document.querySelector('[title="Fermer les dés"]').click();await pause();
    await until(()=>document.querySelector('.target-content small')?.textContent.includes('Enregistré'),'save');
    return {name:document.querySelector('.target-accordion>summary strong').textContent,count:cards().length};
  })()`);
  // Direct VTT manipulation: create a real token, drag from its current grab point,
  // then undo the whole gesture as a single history entry.
  await evaluate(`(async()=>{document.querySelector('.vtt-header-actions button').click();for(let i=0;i<100;i++){if(document.querySelector('.vtt-token-overlay'))return;await new Promise(r=>setTimeout(r,50))}throw Error('VTT token creation failed')})()`);
  await evaluate(`document.querySelector('.vtt-shell').scrollIntoView({block:'start'})`);await delay(120);
  const tokenStart=await evaluate(`(()=>{const r=document.querySelector('.vtt-token-overlay').getBoundingClientRect();return{x:r.x+r.width*.35,y:r.y+r.height*.4,left:r.left,top:r.top}})()`);
  await send('Input.dispatchMouseEvent',{type:'mousePressed',x:tokenStart.x,y:tokenStart.y,button:'left',clickCount:1});
  await send('Input.dispatchMouseEvent',{type:'mouseMoved',x:tokenStart.x+96,y:tokenStart.y+54,button:'left',buttons:1});
  await send('Input.dispatchMouseEvent',{type:'mouseReleased',x:tokenStart.x+96,y:tokenStart.y+54,button:'left',clickCount:1});await delay(120);
  const tokenMoved=await evaluate(`(()=>{const r=document.querySelector('.vtt-token-overlay').getBoundingClientRect();return{left:r.left,top:r.top}})()`);
  if(Math.hypot(tokenMoved.left-tokenStart.left,tokenMoved.top-tokenStart.top)<40)throw Error('VTT direct drag did not follow pointer '+JSON.stringify({tokenStart,tokenMoved}));
  await evaluate(`document.querySelector('.vtt-stage').dispatchEvent(new KeyboardEvent('keydown',{key:'z',ctrlKey:true,bubbles:true}))`);await delay(250);
  const tokenUndone=await evaluate(`(()=>{const r=document.querySelector('.vtt-token-overlay').getBoundingClientRect();return{left:r.left,top:r.top}})()`);
  if(Math.hypot(tokenUndone.left-tokenStart.left,tokenUndone.top-tokenStart.top)>6)throw Error('VTT drag undo did not restore position '+JSON.stringify({tokenStart,tokenMoved,tokenUndone}));
  await evaluate(`document.querySelector('.vtt-tool-group .tool-caret').click()`);await delay(50);
  await evaluate(`[...document.querySelectorAll('.measure-menu button')].find(b=>b.textContent.includes('Gabarit de portée')).click()`);await delay(50);
  await evaluate(`[...document.querySelectorAll('.range-shapes button')].find(b=>b.textContent==='Cône').click()`);await delay(80);
  const rangeUi=await evaluate(`(()=>{const menu=document.querySelector('.range-template-menu'),color=menu?.querySelector('input[type=color]');return{visible:!!menu,color:color?.value,side:menu?.getBoundingClientRect().left>document.querySelector('.vtt-tools').getBoundingClientRect().right}})()`);
  if(!rangeUi.visible||rangeUi.color!=='#d32f2f'||!rangeUi.side)throw Error('Range template menu invalid '+JSON.stringify(rangeUi));
  const rangePoint=await evaluate(`(()=>{const r=document.querySelector('.vtt-stage').getBoundingClientRect();return{x:r.left+r.width*.72,y:r.top+r.height*.32}})()`);
  await send('Input.dispatchMouseEvent',{type:'mouseMoved',x:rangePoint.x,y:rangePoint.y});
  await send('Input.dispatchMouseEvent',{type:'mousePressed',x:rangePoint.x,y:rangePoint.y,button:'left',clickCount:1});
  await send('Input.dispatchMouseEvent',{type:'mouseReleased',x:rangePoint.x,y:rangePoint.y,button:'left',clickCount:1});await delay(100);
  await evaluate(`document.querySelector('.outliner-toggle-right').click()`);await delay(80);
  if(!await evaluate(`[...document.querySelectorAll('.outliner-row')].some(row=>row.textContent.includes('Portée cone'))`))throw Error('Range template was not persisted as a note object');
  await evaluate(`document.querySelector('.outliner-toggle-right').click()`);await delay(260);
  await evaluate(`(()=>{const stage=document.querySelector('.vtt-stage');stage.focus();stage.dispatchEvent(new KeyboardEvent('keydown',{code:'Space',key:' ',bubbles:true}))})()`);await delay(320);
  const centeredRange=await evaluate(`(()=>{const r=document.querySelector('.vtt-token-overlay').getBoundingClientRect(),s=document.querySelector('.vtt-stage').getBoundingClientRect();return Math.hypot(r.x+r.width/2-(s.x+s.width/2),r.y+r.height/2-(s.y+s.height/2))})()`);
  if(centeredRange>12)throw Error('Space did not center the range selection: '+centeredRange);
  // Capture a second real throw while the white 3D tray is visible.
  await evaluate(`document.querySelector('.sheet-frame [role="button"]').click()`);
  await evaluate(`new Promise((resolve,reject)=>{let n=0;const t=setInterval(()=>{const doc=document.querySelector('.dice-overlay iframe')?.contentDocument;if(doc?.body?.dataset.renderer==='three-rapier'){clearInterval(t);resolve(true)}else if(n++>200){clearInterval(t);reject(Error('3D capture timeout'))}},100)})`);
  const diceImageDir=fileURLToPath(new URL('../../../.tmp/',import.meta.url));mkdirSync(diceImageDir,{recursive:true});
  await send('Emulation.setDeviceMetricsOverride',{width:1024,height:600,deviceScaleFactor:2,mobile:false});await delay(200);
  const diceBounds=await evaluate('(()=>{const r=document.querySelector(".dice-overlay").getBoundingClientRect();const c=document.querySelector(".dice-overlay iframe").contentDocument.querySelector("canvas");return {left:r.left,top:r.top,bottom:r.bottom,height:innerHeight,canvas:c.width,css:c.getBoundingClientRect().width,dpr:devicePixelRatio}})()');
  if(diceBounds.left<0||diceBounds.left>20||diceBounds.top<0||diceBounds.bottom>diceBounds.height||Math.abs(diceBounds.canvas-diceBounds.css*diceBounds.dpr)>3)throw Error('Dice bounds/resolution mismatch '+JSON.stringify(diceBounds));
  const diceScreenshot=await send('Page.captureScreenshot',{format:'png'});writeFileSync(path.join(diceImageDir,'cardenveil-test-dice.png'),Buffer.from(diceScreenshot.data,'base64'));
  await evaluate(`new Promise((resolve,reject)=>{let n=0;const t=setInterval(()=>{const close=document.querySelector('[title="Fermer les dés"]');if(close&&!close.disabled){clearInterval(t);close.click();resolve(true)}else if(n++>350){clearInterval(t);reject(Error('Second roll timeout'))}},100)})`);
  await send('Emulation.setDeviceMetricsOverride',{width:1440,height:1100,deviceScaleFactor:1,mobile:false});await delay(100);
  await send('Page.reload');await delay(600);
  const persisted=await evaluate(`new Promise((resolve,reject)=>{let n=0,opened=false;const timer=setInterval(()=>{if(document.querySelector('.target-accordion')&&!opened&&!document.querySelector('.plugin-draw')){opened=true;document.querySelector('.hand-toggle').click()}if(document.querySelector('.plugin-draw')){clearInterval(timer);resolve({name:document.querySelector('.target-accordion>summary strong').textContent,count:document.querySelectorAll('.plugin-fan .playing-card:not(.crystallized)').length})}else if(n++>100){clearInterval(timer);reject(Error('Reload timeout'))}},100)})`);
  if(JSON.stringify(report)!==JSON.stringify(persisted))throw Error('Persistence mismatch '+JSON.stringify({report,persisted}));
  // Import the actual canonical archive through the same file-input handler as users.
  await evaluate(`(async()=>{
    const catalogue=await fetch('/data/characters.json').then(r=>r.json());
    const blob=await fetch(catalogue[1].download).then(r=>r.blob());
    const file=new File([blob],'character.zip',{type:'application/zip'});
    const old=HTMLInputElement.prototype.click;
    HTMLInputElement.prototype.click=function(){if(this.type==='file'){Object.defineProperty(this,'files',{value:[file]});this.onchange({target:this});}else old.call(this)};
    document.querySelector('.sheet-frame button[title="Importer une fiche JSON"]').click();
    HTMLInputElement.prototype.click=old;
    for(let i=0;i<150;i++){if(document.querySelector('.target-accordion>summary strong').textContent===catalogue[1].identity.nom)return;await new Promise(r=>setTimeout(r,100))}
    throw Error('ZIP import failed '+document.body.innerText.slice(-500));
  })()`);
  await evaluate(`(async()=>{
    const pause=()=>new Promise(r=>setTimeout(r,100));
    document.querySelector('.sheet-frame button[title="Modifier la fiche (formulaire agrandi)"]').click();await pause();
    const identity=[...document.querySelectorAll('.sheet-frame button')].find(b=>b.textContent.trim()==='IDENTITÉ');identity.click();await pause();
    const name=document.querySelector('.sheet-frame .fixed input[type="text"]');
    if(!name)throw Error('Identity editor missing');
    if(getComputedStyle(name).color==='rgb(255, 255, 255)')throw Error('White editor field text');
    name.value='Personnage de test';name.dispatchEvent(new Event('input',{bubbles:true}));await pause();
    const save=[...document.querySelectorAll('.sheet-frame .fixed button')].find(b=>b.textContent.trim()==='Sauvegarder');save.click();
    for(let i=0;i<100;i++){if(document.querySelector('.target-accordion>summary strong').textContent==='Personnage de test')return;await pause()}
    throw Error('Sheet edit not saved');
  })()`);
  await send('Emulation.setDeviceMetricsOverride',{width:1440,height:1100,deviceScaleFactor:1,mobile:false});await delay(200);
  const screenshotDir=fileURLToPath(new URL('../../../.tmp/',import.meta.url));mkdirSync(screenshotDir,{recursive:true});
  const screenshot=await send('Page.captureScreenshot',{format:'png',captureBeyondViewport:false});writeFileSync(path.join(screenshotDir,'cardenveil-test.png'),Buffer.from(screenshot.data,'base64'));
  await evaluate("document.querySelector('.sheet-section').scrollIntoView()");await delay(150);
  const navState=await evaluate(`(()=>{const nav=document.querySelector('.sandbox-header'),r=nav.getBoundingClientRect(),link=nav.querySelector('a[href="/"]'),b=link.getBoundingClientRect();return {top:r.top,height:r.height,position:getComputedStyle(nav).position,hit:document.elementFromPoint(b.x+b.width/2,b.y+b.height/2)?.closest('.sandbox-header')===nav}})()`);
  if(navState.position!=='sticky'||Math.abs(navState.top)>1||navState.height>60||!navState.hit)throw Error('Sticky compact navigation failed '+JSON.stringify(navState));
  const dock=await evaluate('({position:getComputedStyle(document.querySelector(".hand-dock")).position,bottom:document.querySelector(".hand-dock").getBoundingClientRect().bottom,height:innerHeight})');
  if(dock.position!=='fixed'||Math.abs(dock.height-dock.bottom)>30)throw Error('Hand dock not anchored to viewport bottom');
  await evaluate('document.querySelector(".plugin-bar-left button").click()');await delay(100);
  await evaluate('scrollTo(0,0)');await delay(100);
  const topDock=await evaluate('document.querySelector(".hand-dock").getBoundingClientRect().bottom<=innerHeight');if(!topDock)throw Error('Hand not accessible at top');
  await evaluate('document.querySelector(".hand-toggle").click()');await delay(80);if(await evaluate('!!document.querySelector(".hand-dock")'))throw Error('Hide hand failed');
  await evaluate('document.querySelector(".hand-toggle").click()');await delay(80);
  await evaluate('document.querySelector(".compact-toggle").click()');await delay(80);
  await evaluate(`new Promise((resolve,reject)=>{let n=0;const t=setInterval(()=>{if(document.querySelector('.native-compact')?.textContent.includes('B. ATT.')){clearInterval(t);resolve(true)}else if(n++>100){clearInterval(t);reject(Error('Native compact did not load'))}},30)})`);
  const initialTop=await evaluate('({top:document.querySelector(".native-compact-window").getBoundingClientRect().top,nav:document.querySelector(".sandbox-header").getBoundingClientRect().bottom})');if(Math.abs(initialTop.top-initialTop.nav-6)>2)throw Error('Compact is not aligned below navigation');
  const grip=await evaluate('(()=>{const r=document.querySelector(".compact-grip").getBoundingClientRect();return {x:r.x+20,y:r.y+20}})()');
  await send('Input.dispatchMouseEvent',{type:'mousePressed',x:grip.x,y:grip.y,button:'left',clickCount:1});
  await send('Input.dispatchMouseEvent',{type:'mouseMoved',x:grip.x-120,y:grip.y+60,button:'left',buttons:1});
  await send('Input.dispatchMouseEvent',{type:'mouseReleased',x:grip.x-120,y:grip.y+60,button:'left',clickCount:1});await delay(100);
  const moved=await evaluate('document.querySelector(".compact-grip").getBoundingClientRect().x');if(Math.abs(moved-(grip.x-20))<50)throw Error('Compact panel not draggable');
  await evaluate(`(async()=>{
    const root=document.querySelector('.native-compact'),pause=()=>new Promise(r=>setTimeout(r,100));
    const initialCompactHeight=root.closest('.native-compact-window').getBoundingClientRect().height;
    for(const label of ['PV','PARADE','INITIAT.','ARMURE','VITESSE','B. ATT.','FAVORIS','TOTEM'])if(!root.textContent.includes(label))throw Error('Compact section missing '+label);
    if(root.textContent.includes('📌'))throw Error('Compact reintroduced pins');
    for(const die of [4,6,8,10,12,20,100])if(!root.querySelector('[title="Ajouter 1d'+die+' à la formule"]'))throw Error('Missing quick die '+die);
    const bonus=root.querySelector('[title^="Bonus d"]');bonus.click();await pause();
    const input=bonus.querySelector('input');input.value='7';input.dispatchEvent(new Event('input',{bubbles:true}));input.dispatchEvent(new KeyboardEvent('keydown',{key:'Enter',bubbles:true}));await pause();
    if(!bonus.textContent.includes('+7'))throw Error('B.ATT edit not committed');
    root.querySelector('[title="Valeur brute (multiplicateur / base / dés)"]').click();await pause();
    if(!root.textContent.includes('MULTIPLICATEUR')||!root.textContent.includes('CARACTÉRISTIQUE'))throw Error('Missing magic controls');
    if(root.closest('.native-compact-window').getBoundingClientRect().height<=initialCompactHeight)throw Error('Compact did not grow when accordion opened');
    root.querySelector('[title="Valeur brute (multiplicateur / base / dés)"]').click();await pause();
    root.querySelector('[title="Attaque (avantage / engagement)"]').click();await pause();
    if(!root.textContent.includes('ENGAGEMENT')&&!root.textContent.includes('Aucune arme équipée'))throw Error('Missing attack panel');
    root.querySelector('[title="Attaque (avantage / engagement)"]').click();await pause();
    root.querySelector('[title="Voir les notes"]').click();await pause();
    if(!root.querySelector('textarea'))throw Error('Missing notes');root.querySelector('[title="Masquer les notes"]').click();
    root.querySelector('[title="Ajouter 1d4 à la formule"]').click();root.querySelector('[title="Ajouter 1d6 à la formule"]').click();await pause();
    if(root.querySelector('input[placeholder="1d20+1d6…"]').value!=='1d4+1d6')throw Error('Quick dice composition failed');
    const launch=root.querySelector('[title="Lancer la formule"]');if(launch.disabled)throw Error('Compound quick roll disabled');launch.click();
  })()`);
  await evaluate(`new Promise((resolve,reject)=>{let n=0;const t=setInterval(()=>{const close=document.querySelector('[title="Fermer les dés"]');if(close&&!close.disabled&&document.querySelector('.history').textContent.includes('Jet rapide')){clearInterval(t);close.click();resolve(true)}else if(n++>450){clearInterval(t);reject(Error('Compact quick dice failed'))}},100)})`);
  await evaluate(`(()=>{const r=document.querySelector('.native-compact');r.querySelector('[title="Attaque (avantage / engagement)"]').click();r.querySelector('[title="Valeur brute (multiplicateur / base / dés)"]').click();r.querySelector('[title="Voir les notes"]').click()})()`);await delay(150);
  await send('Emulation.setDeviceMetricsOverride',{width:1024,height:700,deviceScaleFactor:1,mobile:false});await delay(250);
  const constrained=await evaluate(`(()=>{const panel=document.querySelector('.native-compact-window'),scroller=panel.querySelector('.compact-scroll'),dock=document.querySelector('.hand-dock');const p=panel.getBoundingClientRect(),d=dock.getBoundingClientRect();scroller.scrollTop=scroller.scrollHeight;return {bottom:p.bottom,dockTop:d.top,height:p.height,scroll:scroller.scrollHeight,client:scroller.clientHeight,top:scroller.scrollTop}})()`);
  if(constrained.bottom>constrained.dockTop-10||constrained.scroll<=constrained.client||constrained.top<=0)throw Error('Compact overlap/scroll constraint failed '+JSON.stringify(constrained));
  await evaluate('document.querySelector(".plugin-bar-left button").click()');await delay(200);
  const expandedDock=await evaluate(`(()=>{const p=document.querySelector('.native-compact-window').getBoundingClientRect(),d=document.querySelector('.hand-dock').getBoundingClientRect();return {bottom:p.bottom,dockTop:d.top,height:p.height}})()`);
  if(expandedDock.bottom>expandedDock.dockTop-10||expandedDock.height>=constrained.height)throw Error('Compact did not follow expanded hand');
  await evaluate('document.querySelector(".hand-toggle").click()');await delay(200);
  if(!await evaluate(`document.querySelector('.native-compact-window').getBoundingClientRect().height>${expandedDock.height}`))throw Error('Compact did not reclaim hidden-hand space');
  await evaluate('document.querySelector(".hand-toggle").click()');await delay(150);await evaluate('document.querySelector(".plugin-bar-left button").click()');await delay(150);
  await evaluate(`(()=>{const r=document.querySelector('.native-compact');r.querySelector('[title="Attaque (avantage / engagement)"]').click();r.querySelector('[title="Valeur brute (multiplicateur / base / dés)"]').click();r.querySelector('[title="Masquer les notes"]').click()})()`);
  await send('Emulation.setDeviceMetricsOverride',{width:1440,height:1100,deviceScaleFactor:1,mobile:false});await delay(200);
  const compactDir=fileURLToPath(new URL('../../../.tmp/',import.meta.url));mkdirSync(compactDir,{recursive:true});
  const compactShot=await send('Page.captureScreenshot',{format:'png'});writeFileSync(path.join(compactDir,'cardenveil-test-compact.png'),Buffer.from(compactShot.data,'base64'));
  await evaluate('document.querySelector(".compact-toggle").click()');await delay(100);
  if(await evaluate('!!document.querySelector(".compact-bubble")'))throw Error('Compact cannot be disabled');
  await evaluate('document.querySelector(".compact-toggle").click()');await delay(250);
  if(!await evaluate('document.querySelector(".native-compact [title^=\\"Bonus d\\"]").textContent.includes("+7")'))throw Error('Attack bonus not persisted');
  await evaluate('document.querySelector(".compact-toggle").click()');await delay(100);
  await evaluate("document.querySelector('.sheet-section').scrollIntoView()");await delay(100);
  if(!await evaluate('document.querySelector(".hand-dock").classList.contains("is-folded")&&!document.querySelector(".plugin-fan")'))throw Error('Hand cannot be hidden');
  await evaluate('document.querySelector(".plugin-bar-left button").click()');await delay(100);
  const sheetScreenshot=await send('Page.captureScreenshot',{format:'png'});writeFileSync(path.join(screenshotDir,'cardenveil-test-sheet.png'),Buffer.from(sheetScreenshot.data,'base64'));
  await evaluate("[...document.querySelectorAll('.sheet-tabs button')].find(b=>b.textContent.trim()==='CAPACITÉS').click()");await delay(150);
  await evaluate("document.querySelector('.sheet-tabs').scrollIntoView()");await delay(100);
  const capacityScreenshot=await send('Page.captureScreenshot',{format:'png'});writeFileSync(path.join(screenshotDir,'cardenveil-test-capacities.png'),Buffer.from(capacityScreenshot.data,'base64'));
  const contrast=await evaluate(`(()=>{const bad=[];for(const el of document.querySelectorAll('.capacity-card *')){if(!el.children.length&&el.textContent.trim()){const c=getComputedStyle(el).color.match(/[\\d.]+/g)?.map(Number);if(c&&c[0]>210&&c[1]>210&&c[2]>210&&!el.closest('button'))bad.push(el.textContent.trim())}}return bad})()`);
  if(contrast.length)throw Error('Light text on light capacity surface: '+contrast.join(', '));
  await send('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:true});await delay(200);
  const width=await evaluate('({scroll:document.documentElement.scrollWidth,width:innerWidth})');
  if(width.scroll>width.width+2)throw Error('Mobile overflow '+JSON.stringify(width));
  await evaluate('scrollTo(0,0);document.querySelector(".compact-toggle").click()');await delay(200);
  const layouts=[];
  for(const [w,h] of [[1920,1080],[1440,900],[1024,600],[768,1024],[650,1024],[390,844],[320,568],[844,390],[1280,420],[320,320]]){
    await send('Emulation.setDeviceMetricsOverride',{width:w,height:h,deviceScaleFactor:1,mobile:false});await delay(180);
    const layout=await evaluate(`(()=>{const p=document.querySelector('.native-compact-window').getBoundingClientRect(),d=document.querySelector('.hand-dock').getBoundingClientRect(),draw=document.querySelector('.plugin-draw'),b=draw.getBoundingClientRect();return {width:innerWidth,height:innerHeight,scroll:document.documentElement.scrollWidth,panel:{left:p.left,top:p.top,right:p.right,bottom:p.bottom},dock:{left:d.left,right:d.right,top:d.top,bottom:d.bottom},draw:{left:b.left,right:b.right,top:b.top,bottom:b.bottom},overflow:document.querySelector('.compact-scroll').scrollHeight>document.querySelector('.compact-scroll').clientHeight}})()`);
    layouts.push(layout);
    const navVisible=await evaluate(`(()=>{const r=document.querySelector('.sandbox-header').getBoundingClientRect();return r.top>=0&&r.bottom<=innerHeight})()`);if(!navVisible)throw Error('Navigation outside viewport at '+w+'x'+h);
    if(w===1920&&(Math.abs(layout.dock.right-layout.dock.left-640)>1||Math.abs(layout.dock.bottom-layout.dock.top-196)>2))throw Error('Desktop dock proportions changed '+JSON.stringify(layout));
    for(const box of [layout.panel,layout.dock])if(box.left<0||box.right>w+1||box.top<0||box.bottom>h+1)throw Error('Out-of-viewport panel '+JSON.stringify(layout));
    if(layout.panel.bottom>layout.dock.top-10||layout.scroll>w+1||layout.dock.right<w-25)throw Error('Responsive overlap/overflow '+JSON.stringify(layout));
    if(layout.draw.left<layout.dock.left||layout.draw.right>layout.dock.right)throw Error('Draw button clipped '+JSON.stringify(layout));
    if(layout.draw.top<layout.dock.top-1||layout.draw.bottom>layout.dock.bottom+1)throw Error('Draw button outside dock viewport '+JSON.stringify(layout));
    const hit=await evaluate(`document.elementFromPoint(${(layout.draw.left+layout.draw.right)/2},${(layout.draw.top+layout.draw.bottom)/2})?.closest('.plugin-draw')!=null`);if(!hit)throw Error('Draw button cannot be clicked at '+w+'x'+h);
    if((w===650&&h===1024)||(w===844&&h===390)){const shot=await send('Page.captureScreenshot',{format:'png'});writeFileSync(path.join(screenshotDir,'cardenveil-test-layout-'+w+'x'+h+'.png'),Buffer.from(shot.data,'base64'));}
  }
  console.log('Ratios checked: '+layouts.map(l=>l.width+'x'+l.height).join(', '));
  await send('Emulation.setDeviceMetricsOverride',{width:1440,height:900,deviceScaleFactor:1,mobile:false});await delay(150);
  await evaluate(`(()=>{const draw=document.querySelector('.plugin-draw');for(let i=0;i<20;i++)if(!draw.disabled)draw.click()})()`);await delay(100);
  if(!await evaluate(`document.querySelector('.plugin-draw')?.disabled===true`))throw Error('Blocked draw should be disabled');
  if(errors.length)throw Error(errors.join('\n'));
  await evaluate(`(async()=>{document.querySelector('.target-content .danger').click();for(let i=0;i<100;i++){if(document.querySelector('.target-accordion>summary strong').textContent==='Mon personnage'&&!document.querySelector('.playing-card'))return;await new Promise(r=>setTimeout(r,100))}throw Error('Reset failed')})()`);
  console.log('PASS: compact grows with accordions, stops above the cards, scrolls internally, follows hand expansion/hiding and viewport resize; existing compact, dice and persistence flows pass.');
}finally{ws?.close();child.kill();server.close();}
