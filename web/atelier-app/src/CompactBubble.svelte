<script>
  import {onMount} from 'svelte';
  import SheetPopover from './vendor/SheetPopover.svelte';
  let {enabled,onAction}=$props();
  let x=$state(0),y=$state(88),height=$state(540),panel=$state(null),drag=null;
  let schedule=()=>{};
  const positionKey='cardenveil-atelier-compact-position-v2';
  function limits(){const viewport=window.visualViewport,nav=document.querySelector('.sandbox-header')?.getBoundingClientRect();let top=Math.max((viewport?.offsetTop??0)+8,nav&&nav.bottom>0?nav.bottom+6:0);let bottom=Math.min(innerHeight,(viewport?.offsetTop??0)+(viewport?.height??innerHeight))-12;const dock=document.querySelector('.hand-dock');if(dock){const r=dock.getBoundingClientRect();if(r.height>0)bottom=Math.min(bottom,r.top-12);}if(bottom-top<40)top=Math.max((viewport?.offsetTop??0)+8,bottom-40);return {top,bottom};}
  function clamp(){const viewportWidth=document.documentElement.clientWidth,width=Math.min(460,viewportWidth-72),{top,bottom}=limits();x=Math.max(12,Math.min(x,viewportWidth-width-60));y=Math.max(top,Math.min(y,Math.max(top,bottom-80)));}
  function start(e){if(!e.target.closest('.compact-grip')||e.target.closest('button')||e.button!==0)return;drag={px:e.clientX,py:e.clientY,x,y};e.currentTarget.setPointerCapture(e.pointerId);}
  function move(e){if(!drag)return;x=drag.x+e.clientX-drag.px;y=drag.y+e.clientY-drag.py;clamp();schedule();}
  function end(){if(!drag)return;drag=null;try{localStorage.setItem(positionKey,JSON.stringify({x,y}));}catch{}}
  onMount(()=>{
    x=innerWidth-520;y=limits().top;try{const saved=JSON.parse(localStorage.getItem(positionKey));if(saved&&Number.isFinite(saved.x)&&Number.isFinite(saved.y)){x=saved.x;y=saved.y;}}catch{}
    let frame=0,observedRoot=null,observedDock=null;
    const resize=new ResizeObserver(()=>schedule());
    function measure(){
      frame=0;
      const root=panel?.querySelector('.native-compact')??null,dock=document.querySelector('.hand-dock');
      if(root!==observedRoot){if(observedRoot)resize.unobserve(observedRoot);observedRoot=root;if(root)resize.observe(root);}
      if(dock!==observedDock){if(observedDock)resize.unobserve(observedDock);observedDock=dock;if(dock)resize.observe(dock);}
      if(!root)return;
      clamp();const {bottom}=limits();const natural=Math.ceil(Math.max(root.scrollHeight,root.getBoundingClientRect().height));
      height=Math.min(natural,Math.max(40,Math.floor(bottom-y)));
    }
    schedule=()=>{if(!frame)frame=requestAnimationFrame(measure);};
    const viewportChanged=()=>{y=limits().top;schedule();};
    // Accordions, async sheet loads, and showing/hiding the hand all alter the available layout.
    const mutations=new MutationObserver(()=>schedule());mutations.observe(document.body,{childList:true,subtree:true});
    window.addEventListener('resize',viewportChanged);window.visualViewport?.addEventListener('resize',viewportChanged);schedule();
    return()=>{cancelAnimationFrame(frame);resize.disconnect();mutations.disconnect();window.removeEventListener('resize',viewportChanged);window.visualViewport?.removeEventListener('resize',viewportChanged);schedule=()=>{};};
  });
</script>
{#if enabled}<aside bind:this={panel} class="compact-bubble expanded native-compact-window" style={`left:${x}px;top:${y}px;height:${height}px`} aria-label="Fiche compacte déplaçable" onpointerdown={start} onpointermove={move} onpointerup={end} onpointercancel={end}>
  <div class="sheet-frame compact-scroll"><SheetPopover {onAction}/></div>
</aside>{/if}
