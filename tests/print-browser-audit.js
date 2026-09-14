/* Exercise real A4 layout, source text preservation, images and oversized totem continuation. */
document.querySelector('iframe').onload=async function(){
  const win=this.contentWindow;
  const chars=await fetch('/data/characters.json').then(r=>r.json());
  const results=[];
  const words=s=>s.toLowerCase().match(/[\p{L}\p{N}]+/gu)||[];
  const counts=s=>words(s).reduce((map,w)=>(map[w]=(map[w]||0)+1,map),{});
  const giant=JSON.parse(JSON.stringify(chars.find(c=>c.id==='luna')));
  giant.id='continuation-test';giant.identity.nom='Continuation test';
  giant.totem.description=Array.from({length:18},(_,i)=>`<p><strong>Repère${i}</strong> : ${'Texte de continuation intégral. '.repeat(12)}</p>`).join('');
  for(const c of [...chars,giant]){
    try{
      const pages=await win.renderSheet(c);const doc=win.document;
      const sourceText=v=>{const t=doc.createElement('template');t.innerHTML=win.rich(v);const w=doc.createTreeWalker(t.content,win.NodeFilter.SHOW_TEXT);const parts=[];let n;while((n=w.nextNode()))parts.push(n.nodeValue);return parts.join(' ');};
      const expected=[c.totem.description,...Object.values(c.narrative),...c.capacities.map(a=>a.description)].map(sourceText).join(' ');
      const walker=doc.createTreeWalker(doc.querySelector('#sheets'),win.NodeFilter.SHOW_TEXT);const texts=[];let node;
      while((node=walker.nextNode()))texts.push(node.nodeValue);
      const wanted=counts(expected),actual=counts(texts.join(' '));
      const missing=Object.keys(wanted).filter(w=>(actual[w]||0)<wanted[w]);
      const horizontal=[...doc.querySelectorAll('.box,.field,.ability-header')].filter(e=>e.scrollWidth>e.clientWidth+3).length;
      const images=[c.portrait,c.totem.image,...c.capacities.map(a=>a.image)].filter(Boolean);
      const missingImages=images.filter(src=>![...doc.images].some(img=>img.getAttribute('src')===src));
      const inventoryPage=[...doc.querySelectorAll('.page-content')].findIndex(p=>p.firstElementChild.textContent==='Équipement & inventaire');
      results.push({id:c.id,pages,horizontal,missing,missingImages,inventoryPage});
    }catch(e){results.push({id:c.id,error:e.message});}
  }
  document.querySelector('#result').textContent=JSON.stringify(results);document.title='DONE';
};
