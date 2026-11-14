<script>
  import { onMount } from 'svelte';
  import OBR from '@owlbear-rodeo/sdk';
  import {roll3D} from '../diceService.js';
  let {onAction}=$props();
  function dispatch(roomId,action){onAction(action);return Promise.resolve();}
  const broadcastRoll=(data)=>roll3D(data);
  import { tooltip } from './tooltip.js';
  import ActionDiamonds from './ActionDiamonds.svelte';
  import {
    STAT_COLORS,
    STAT_LABELS,
    SKILL_GROUPS,
    SKILL_LABELS,
    fetchCharacterSheet,
    healSheetBase,
    isDiceFormula,
    rollDice,
    saveCharacterSheet,
    raceLabel,
    raceTraits,
    racePvBonus,
    effectiveStats,
    rollD20Keep,
    normalizeRaceName,
    skillModifier,
    skillRollModifier,
    computeDerived,
    subscribeToCharacterSheet,
    onSheetBroadcast,
    suitColor,
    suitSymbol,
    toNumber,
    isImageUrl,
    DICE_GEMS,
    DICE_GEM_LABELS,
    diceGemColor,
    parseDiceSpec,
    weaponTagInfo
  } from './characterSheet.js';

  import { logEvent, logError, setLogContext } from './appLog.js';



  import { rollAttack, runAttack, attackPreview, pickAttackWeapon, isGobelin, weaponFlags } from './attackRoll.js';
  import { SIDES_TO_TYPE } from './diceRoll.js';

  const playerId='local-mj',roomId='local';

  let sheet = $state(null);
  let folded = $state(false);
  let showNotes = $state(false);
  let notesDraft = $state('');
  let notesDraftDirty = $state(false);

  // Follow external sheet updates until the user types
  $effect(() => {
    if (showNotes && !notesDraftDirty) notesDraft = sheet?.notes ?? '';
  });

  function saveNotes() {
    if (!sheet) return;
    notesDraftDirty = false;
    sheet = { ...sheet, notes: notesDraft };
    saveInFlight = true;
    saveCharacterSheet(playerId, roomId, sheet)
      .catch((err) => {
        // 10 of 13 save sites are silent; a refused save (no merge base after an
        // outage) must reach the player, same alert as the full sheet.
        logError('sheet_popover_save_failed', err);
        alert('Erreur lors de la sauvegarde: ' + err.message);
      })
      .finally(() => {
        saveInFlight = false;
      });
  }
  // ─── Quick dice row (d4 → d100 icons; click adds to the formula) ───
  const QUICK_DICE = [
    { die: 'd4', icon: '<polygon points="12,2 22,20 2,20"/>' },
    { die: 'd6', icon: '<rect x="3" y="3" width="18" height="18" rx="3"/>' },
    { die: 'd8', icon: '<polygon points="12,1 23,12 12,23 1,12"/>' },
    { die: 'd10', icon: '<polygon points="12,1 22,10 12,23 2,10"/>' },
    { die: 'd12', icon: '<polygon points="12,1 23,9 19,22 5,22 1,9"/>' },
    { die: 'd20', icon: '<polygon points="12,1 22,6.5 22,17.5 12,23 2,17.5 2,6.5"/>' },
    { die: 'd100', icon: '<polygon points="15,2 21,10 15,22 9,10"/><polygon points="9,7 13,11 9,18 5,11" fill-opacity="0.5"/>' }
  ];
  let quickFormula = $state('');

  // count of each die type in the quick formula (for the badge chips)
  let quickCounts = $derived.by(() => {
    const counts = {};
    for (const m of quickFormula.matchAll(/(\d*)d(\d+)/gi)) {
      const sides = m[2];
      counts[sides] = (counts[sides] ?? 0) + (m[1] ? parseInt(m[1], 10) : 1);
    }
    return counts;
  });

  function addQuickDie(die) {
    quickFormula = quickFormula ? `${quickFormula}+1${die}` : `1${die}`;
  }

  let expandedHeight = 540;
  const FOLDED_HEIGHT = 40;

  function toggleFold(){folded=!folded;}

  onMount(()=>{
    const off=subscribeToCharacterSheet(playerId,roomId,row=>{if(row)sheet=row.data;});
    fetchCharacterSheet(playerId,roomId).then(row=>{if(sheet==null)sheet=row?.data??null;}).catch(err=>logError('compact_load_failed',err));
    return off;
  });

  function statMod(stat) {
    const value = effectiveStats(sheet)?.[stat] || 10;
    return Math.floor((value - 10) / 2);
  }

  // BONUS ATT.: click-to-edit in the combat row; writes derived.overrides
  // (same mechanism as the full sheet's ÉDITION — empty = rule value), so
  // both views share one value and the attack roll uses it directly.
  let editingBonusAttaque = $state(false);
  let bonusAttaqueDraft = $state('');

  function setBonusAttaqueOverride(raw) {
    if (!sheet) return;
    const overrides = { ...(sheet.derived?.overrides ?? {}) };
    if (raw === '' || raw == null || Number.isNaN(Number(raw))) delete overrides.bonusAttaque;
    else overrides.bonusAttaque = Number(raw);
    sheet = { ...sheet, derived: { ...(sheet.derived ?? {}), overrides } };
    saveCharacterSheet(playerId, roomId, sheet).catch((err) => logError('sheet_popover_save_failed', err));
  }

  /** Commit the B. ATT. editor once (Enter, then the input is removed and
   *  fires blur — the guard keeps that from saving twice). */
  function commitBonus() {
    if (!editingBonusAttaque) return;
    setBonusAttaqueOverride(bonusAttaqueDraft);
    editingBonusAttaque = false;
  }

  function stripHtml(text) {
    return (text || '').replace(/<[^>]*>/g, '').trim();
  }

  function fmt(value) {
    return value >= 0 ? `+${value}` : `${value}`;
  }

  function skillColor(skillKey) {
    const group = SKILL_GROUPS.find((g) => g.skills.includes(skillKey));
    return group ? STAT_COLORS[group.stat] : '#9ca3af';
  }

  function skillMod(skillKey) {
    return skillRollModifier(effectiveStats(sheet), skillKey, sheet?.skills?.[skillKey]);
  }

  // ─── Per-turn action diamonds (toggle + persist, no reset logic) ───
  let saveInFlight = false;
  function toggleActionCheck(key) {
    if (!sheet) return;
    const current = sheet.actionChecks ?? {};
    const next = { ...sheet, actionChecks: { ...current, [key]: !current[key] } };
    sheet = next;
    saveInFlight = true;
    saveCharacterSheet(playerId, roomId, next)
      .catch((err) => {
        logError('sheet_popover_save_failed', err);
        alert('Erreur lors de la sauvegarde: ' + err.message);
      })
      .finally(() => {
        saveInFlight = false;
      });
  }


  // Flat mode (GM Classique): pre-rolled numbers (old path). 3D mode: the
  // rapier simulation in the popup decides the numbers — broadcast an intent
  // and dispatch USE_CAPACITY when the result is reported back.
  async function doRoll(label,formula,opts={}){
    try{
      const base=parseDiceSpec(formula,effectiveStats(sheet));if(!base)throw Error('Formule invalide');
      const result=await roll3D({label,formula:base.formula,playerId,portrait:sheet?.portrait||'',portraitIsImage:isImageUrl(sheet?.portrait),diceSpec:opts.keep?[{count:2,sides:20}]:base.terms,modifier:base.modifier,keep:opts.keep||'',zoomCrit:!!opts.zoomCrit});
      await dispatch(roomId,{type:'USE_CAPACITY',playerId,capacityName:label,formula:base.formula,total:result.total,rolls:result.rolls});
    }catch(err){logError('compact_roll_failed',err);}
  }

  // ─── Attack + capacity accordions ───
  let showAttack = $state(false);
  let attackInFlight = false; // one staged roll at a time — stages are sequential
  // single-slot resolver for the current staged throw (sequential by design)
  let pendingStage = null;
  const STAGE_TIMEOUT_MS = 10000;
  // let players read the settled dice before the next stage / summary opens
  const STAGE_PAUSE_MS = 3000;
  let attackWeaponName = $state('');
  let attackAdv = $state(0); // −7…+7 (− = désavantage, + = avantage)
  let attackEngagement = $state(0); // 0…7
  let attackAmplitude = $state(false); // Amplitude: attacking at max range (3 m)
  /** Per-weapon Finesse answer (issue #10): the attack panel's checkbox, saved
   *  in the same localStorage record as the sliders. Absent = follow the weapon. */
  let attackFinesseMap = $state(/** @type {Record<string, boolean>} */ ({}));
  let attackFinesse = $derived(
    attackWeaponName && typeof attackFinesseMap[attackWeaponName] === 'boolean'
      ? attackFinesseMap[attackWeaponName]
      : null
  );

  function setAttackFinesse(checked) {
    if (!attackWeaponName) return;
    attackFinesseMap = { ...attackFinesseMap, [attackWeaponName]: checked };
    saveAttackSettings();
  }

  // Capacity accordion (🪄): Valeur brute = MULT × MOD d6 (pool size = product).
  let showCapacity = $state(false);
  let capacityInFlight = false;
  let capMultiplier = $state(1); // ×0.5 … ×20
  let capStat = $state('esprit'); // stat whose mod seeds the base
  let capMod = $state(null); // null = the selected stat's mod (reset on stat pick)

  function pickCapStat(stat) {
    capStat = stat;
    capMod = capModFloor(stat); // slider defaults to the selected stat's mod
  }

  /** Slider floor is 0 (a negative stat mod still allows a 0 pool). */
  function capModFloor(stat) {
    return Math.max(0, statMod(stat));
  }

  let capModValue = $derived(Math.max(0, capMod ?? statMod(capStat)));

  let capMult = $derived(Math.min(20, Math.max(0.5, Number(capMultiplier) || 1)));
  /** Valeur brute roll: the dice POOL is Multiplier × Mod, summed as-is. */
  let capCount = $derived(
    Math.max(1, Math.min(999, Math.round(capMult * capModValue)))
  );
  /**
   * Racial natural weapons: always available for the attack roll without being
   * an inventory entry (the Khajeet's claws). Marked equipped + main hand so
   * pickAttackWeapon treats them like a weapon; they are appended LAST so an
   * actually equipped main-hand weapon stays the default and the claws are the
   * fallback when nothing is equipped.
   */
  const RACIAL_ATTACKS = /** @type {{[key: string]: Object}} */ ({
    khajeet: {
      nom: 'Griffes',
      de: '1d6',
      degats: 'tranchant',
      proprietes: 'Finesse, Légère, Naturelle',
      icon: '🐾',
      bonus: '',
      equipped: true,
      hand: 'main',
      racial: true,
    },
  });

  let attackWeapons = $derived.by(() => {
    const weapons = sheet?.weapons ?? [];
    const racial = RACIAL_ATTACKS[String(normalizeRaceName(sheet?.identity?.race) ?? '')];
    return racial ? [...weapons, racial] : weapons;
  });
  let equippedWeapons = $derived(pickAttackWeapon(attackWeapons).equipped);

  // restore last-used settings once the sheet is loaded
  let attackSettingsLoaded = false;
  $effect(() => {
    if (sheet && !attackSettingsLoaded) {
      attackSettingsLoaded = true;
      try {
        const saved = JSON.parse(localStorage.getItem(`cardenveil-attack-${playerId}`) || '{}');
        if (typeof saved.adv === 'number') attackAdv = Math.max(-7, Math.min(7, saved.adv));
        if (typeof saved.engagement === 'number') attackEngagement = Math.max(0, Math.min(7, saved.engagement));
        if (saved.finesse && typeof saved.finesse === 'object') attackFinesseMap = saved.finesse;
        // The weapon is deliberately NOT restored: the panel always opens on the
        // main-hand weapon (pickAttackWeapon falls back to it) and the choice
        // made during the session stays until the popover is reloaded.
      } catch {
        /* corrupt settings — defaults */
      }
    }
  });

  // The <select> is bound to `attackWeaponName`, which starts empty: the browser
  // then DISPLAYS the first option (possibly the off-hand weapon) while the roll
  // uses the main hand. Seed the name from the weapon actually used, and
  // re-seed whenever the selection no longer matches an equipped weapon.
  $effect(() => {
    if (!sheet) return;
    const used = pickAttackWeapon(attackWeapons, attackWeaponName).weapon;
    if (used?.nom && used.nom !== attackWeaponName) attackWeaponName = used.nom;
  });

  // Self-healing selection: stale saved name falls back to main hand → first equipped.
  let selectedAttackWeapon = $derived(pickAttackWeapon(attackWeapons, attackWeaponName).weapon);
  let attackCalc = $derived(
    selectedAttackWeapon
      ? attackPreview(selectedAttackWeapon, effectiveStats(sheet), { advantage: attackAdv, engagement: attackEngagement, bonus: calc?.bonusAttaque, race: sheet?.identity?.race, amplitude: attackAmplitude, finesse: attackFinesse ?? undefined })
      : null
  );

  let attackLevelLabel = $derived.by(() => {
    if (!attackCalc) return '';
    const lvl = attackCalc.level;
    if (lvl === 0) return 'jet simple';
    return `${lvl > 0 ? '+' : '−'}${Math.abs(lvl)} ${Math.abs(lvl) === 1 ? 'niveau' : 'niveaux'}`;
  });

  let attackKeepLabel = $derived(
    attackCalc?.keep === 'max' ? 'garder le max' : attackCalc?.keep === 'min' ? 'garder le min' : ''
  );

  function accordionCount() {
    return (showAttack ? 1 : 0) + (showCapacity ? 1 : 0);
  }

  function toggleAttack() {
    const before = accordionCount();
    showAttack = !showAttack;
    resizeAccordions(before);
  }

  function toggleCapacity() {
    const before = accordionCount();
    // Opening seeds the MOD slider at the selected stat's mod (Esprit by
    // default) — the slider itself can then go down to 0.
    if (!showCapacity && capMod == null) capMod = capModFloor(capStat);
    showCapacity = !showCapacity;
    resizeAccordions(before);
  }

  function resizeAccordions(){}

  async function doCapacityRoll() {
    if (attackInFlight || capacityInFlight) return;
    const count = capCount;
    const sides = 6; // Valeur brute is always d6
    const label = `Valeur brute · ${count}d6`;
    let rolls;
    // ponytail: physics throws stay playable up to 50 dice — bigger pools
    // fall back to flat pre-rolled (bump the cap if the sim handles more)
    if ((localStorage.getItem('cardenveil-dice-style') || '') !== 'flat' && SIDES_TO_TYPE[sides] && count <= 50) {
      capacityInFlight = true;
      try {
        rolls = await throwAttackStage(label, count, sides, null);
      } catch (err) {
        logEvent('warn', 'roll_3d_fallback', { message: err?.message ?? String(err), detail: { kind: 'capacity' } });
      } finally {
        capacityInFlight = false;
      }
    }
    if (!rolls) {
      try {
        rolls = rollDice(`${count}d${sides}`).rolls;
      } catch (err) {
        logError('sheet_popover_capacity_roll_failed', err);
        return;
      }
    }
    const total = rolls.reduce((a, b) => a + b, 0);
    broadcastRoll({
      label,
      color: diceGemColor(sheet),
      playerId,
      portrait: sheet?.portrait || '',
      portraitIsImage: isImageUrl(sheet?.portrait),
      formula: `${count}d6`,
      rolls,
      diceTypes: rolls.map(() => sides),
      total,
      breakdown: [`Dé : ${count}d6 [${rolls.join(', ')}]`, `Total : ${total}`]
    }, roomId);
    dispatch(roomId, {
      type: 'USE_CAPACITY',
      playerId,
      capacityName: 'Valeur brute',
      formula: `${count}d6`.slice(0, 32),
      total,
      rolls
    }).catch((err) => logError('sheet_popover_capacity_dispatch_failed', err));
  }

  function saveAttackSettings() {
    try {
      localStorage.setItem(
        `cardenveil-attack-${playerId}`,
        JSON.stringify({ adv: attackAdv, engagement: attackEngagement, finesse: attackFinesseMap })
      );
    } catch {
      /* storage unavailable */
    }
  }

  /**
   * Throw one attack stage as a seeded 3D intent; resolves with the dice
   * read off the settled physics (reported back by the popup). Holds
   * STAGE_PAUSE_MS so players can read the dice before the next stage or
   * the final summary replaces them. Rejects on timeout — the caller
   * falls back to the flat pre-rolled path.
   */
  async function throwAttackStage(baseLabel,pool,sides,keep,noCrit){
    const result=await roll3D({label:baseLabel,formula:`${pool}d${sides}`,playerId,portrait:sheet?.portrait||'',portraitIsImage:isImageUrl(sheet?.portrait),diceSpec:[{count:pool,sides}],modifier:0,staged:true,keep:keep==='max'?'high':keep==='min'?'low':'',critFrom:isGobelin(sheet?.identity?.race)?Math.max(2,sides-1):sides,noCrit:!!noCrit,zoomCrit:true});
    await new Promise(resolve=>setTimeout(resolve,STAGE_PAUSE_MS));
    return result.rolls;
  }

  async function doAttackRoll() {
    const weapon = selectedAttackWeapon;
    if (!weapon || !sheet || attackInFlight) return;
    saveAttackSettings();
    const opts = { advantage: attackAdv, engagement: attackEngagement, bonus: calc?.bonusAttaque, race: sheet?.identity?.race, amplitude: attackAmplitude, finesse: attackFinesse ?? undefined };
    const baseLabel = `Attaque · ${weapon.nom || 'Sans nom'}`;

    // 3D mode: staged physics throws — the driver walks runAttack, throwing
    // each stage (initial pool, explosions) as a seeded intent and reading
    // the dice off the settled physics. Any failure falls back to flat.
    const preview = attackPreview(weapon, effectiveStats(sheet), opts);
    let result;
    if ((localStorage.getItem('cardenveil-dice-style') || '') !== 'flat' && preview && SIDES_TO_TYPE[preview.sides]) {
      attackInFlight = true;
      try {
        result = await runAttack(weapon, sheet.stats ?? {}, opts, (pool, sides, keep) =>
          throwAttackStage(baseLabel, pool, sides, keep, weaponFlags(weapon, sheet?.identity?.race).brute)
        );
      } catch (err) {
        logEvent('warn', 'roll_3d_fallback', { message: err?.message ?? String(err), detail: { kind: 'attack' } });
      } finally {
        attackInFlight = false;
      }
    }
    if (!result) {
      try {
        result = await rollAttack(weapon, sheet.stats ?? {}, opts);
      } catch (err) {
        logError('sheet_popover_attack_roll_failed', err);
        return;
      }
    }
    if (!result) return;
    broadcastRoll({
      label: baseLabel,
      color: diceGemColor(sheet),
      playerId,
      portrait: sheet?.portrait || '',
      portraitIsImage: isImageUrl(sheet?.portrait),
      formula: `${result.stages[0]?.pool ?? 1}d${result.sides}${result.weaponBonus ? (result.weaponBonus > 0 ? '+' : '') + result.weaponBonus : ''}${attackEngagement > 0 ? `${fmt(result.engagementMod)}×${attackEngagement}` : ''}`,
      rolls: result.stages.flatMap((s) => s.dice),
      diceTypes: result.stages.flatMap((s) => s.dice.map(() => result.sides)),
      total: result.total,
      breakdown: result.breakdown,
      critCount: result.critCount,
      miss: result.miss,
      critFrom: result.critFrom,
      // Brute: the summary popup must not flash gold either (issue #11).
      noCrit: result.brute,
      // Property tags travel with the roll so the popup can show them under
      // the formula (issue #5).
      tags: weaponTagInfo(weapon).map((t) => t.label).join(', ')
    }, roomId);
    // Action log: same USE_CAPACITY channel, breakdown folded into the formula string (32 chars max).
    dispatch(roomId, {
      type: 'USE_CAPACITY',
      playerId,
      capacityName: baseLabel.slice(0, 120),
      formula: `${result.stages[0]?.pool ?? 1}d${result.sides}${result.miss ? ' MISS' : result.critCount > 0 ? ` CRIT×${result.critCount}` : ''}`.slice(0, 32),
      total: result.total,
      rolls: result.stages.map((s) => s.kept)
    }).catch((err) => logError('sheet_popover_attack_dispatch_failed', err));
  }
  // Rule-derived combat values (parade, initiative, armure, vitesse)
  let calc = $derived(computeDerived(sheet ?? {}));

  let pinnedSkills = $derived(
    (sheet?.pinnedSkills ?? []).filter((key) => sheet?.skills?.[key])
  );

  let pinnedCapacities = $derived(
    (sheet?.capacities ?? []).filter((capacity, i) =>
      (sheet?.pinnedCapacities ?? []).includes(capacity?.name || `#${i}`)
    )
  );
</script>

<div class="native-compact w-full h-full bg-[#242424] text-white rounded-xl border border-[#374151] flex flex-col overflow-hidden" data-folded={folded}>
  <!-- Fold bar -->
  <div class="compact-grip h-10 bg-[#1f2937] border-b border-[#374151] flex items-center px-3 shrink-0">
    <span class="text-[10px] font-bold tracking-wide">FICHE</span>
    <span class="text-[9px] text-[#9ca3af] ml-2 truncate">{sheet?.identity?.nom || ''}</span>
    <button
      onclick={toggleFold}
      title={folded ? 'Déplier la fiche' : 'Replier la fiche'}
      class="ml-auto w-7 h-7 rounded-full bg-[#111827] border border-[#374151] text-[#9ca3af] hover:text-white text-[11px] font-bold flex items-center justify-center transition-colors"
    >
      {folded ? '▴' : '▾'}
    </button>
  </div>

  {#if folded}
    <!-- folded: bar only -->
  {:else if !sheet}
    <div class="flex-1 flex items-center justify-center text-[#9ca3af] text-xs">
      Chargement de la fiche...
    </div>
  {:else}
    <!-- Header -->
    <div class="px-3 pt-3 pb-2 border-b border-[#374151] bg-[#1f2937] shrink-0">
      <div class="flex items-center gap-2.5">
        <div class="w-10 h-12 bg-[#111827] rounded-lg flex items-center justify-center shrink-0 overflow-hidden">
          {#if sheet.portrait && isImageUrl(sheet.portrait)}
            <img src={sheet.portrait} alt="Portrait" class="w-full h-full object-cover" />
          {:else if sheet.portrait}
            <span class="text-xl leading-none">{sheet.portrait}</span>
          {:else}
            <span class="text-[7px] font-bold text-[#9ca3af]">PORTRAIT</span>
          {/if}
        </div>
        <div class="flex-1 min-w-0">
          <div class="text-sm font-bold truncate">{sheet.identity?.nom || 'Sans nom'}</div>
          <div class="text-[10px] text-[#9ca3af] truncate" use:tooltip={raceTraits(sheet.identity?.race).map((t) => `${t.nom} — ${t.texte}`).join('\n')}>
            {raceLabel(sheet.identity?.race) || '—'} · Niv. {sheet.identity?.niveau ?? 1}
          </div>
        </div>
        <div class="text-right shrink-0">
          <div class="text-[8px] font-bold text-[#9ca3af]">PV</div>
          <div class="text-lg font-bold leading-none">
            {toNumber(sheet.derived?.pvActuels)}
            <span class="text-[10px] text-[#9ca3af] font-semibold">/ {toNumber(sheet.derived?.pvMax) + racePvBonus(sheet)}</span>
          </div>
        </div>
      </div>
      <div class="grid grid-cols-4 gap-1.5 mt-2">
        {#each ['force', 'agilite', 'esprit', 'social'] as stat}
          <div
            onclick={() => doRoll(STAT_LABELS[stat] || stat, `d20${statMod(stat) >= 0 ? '+' + statMod(stat) : statMod(stat)}`, { zoomCrit: true })}
            role="button"
            tabindex="0"
            onkeydown={(e) => e.key === 'Enter' && doRoll(STAT_LABELS[stat] || stat, `d20${statMod(stat) >= 0 ? '+' + statMod(stat) : statMod(stat)}`, { zoomCrit: true })}
            use:tooltip={`Jet de ${STAT_LABELS[stat] || stat} (d20) · Compétences : ${SKILL_GROUPS.find((g) => g.stat === stat)?.skills.map((sk) => SKILL_LABELS[sk] || sk).join(', ') || '—'}`}
            class="bg-[#111827] rounded-md px-1.5 py-1 text-center cursor-pointer hover:bg-[#1f2937] transition-colors"
          >
            <div class="text-[7px] font-bold text-[#9ca3af]">{(STAT_LABELS[stat] || stat).toUpperCase()}</div>
            <div class="text-sm font-bold leading-tight" style="color: {STAT_COLORS[stat]}">
              {toNumber(sheet.stats?.[stat])}
              <span class="text-[10px] text-white">{fmt(statMod(stat))}</span>
            </div>
          </div>
        {/each}
      </div>
      <!-- Combat values: Parade (static), Initiative + Vitesse (click-to-roll d20) -->
      <div class="grid grid-cols-5 gap-1.5 mt-1.5">
        <div class="bg-[#111827] rounded-md px-1.5 py-1 text-center">
          <div class="text-[7px] font-bold text-[#9ca3af]">PARADE</div>
          <div class="text-sm font-bold leading-tight text-[#e5e7eb]">{calc.parade}</div>
        </div>
        <div
          onclick={() => doRoll('Initiative', `d20${fmt(calc.initiative)}`)}
          role="button"
          tabindex="0"
          onkeydown={(e) => e.key === 'Enter' && doRoll('Initiative', `d20${fmt(calc.initiative)}`)}
          title={`Jet d'initiative (d20)`}
          class="bg-[#111827] rounded-md px-1.5 py-1 text-center cursor-pointer hover:bg-[#1f2937] transition-colors"
        >
          <div class="text-[7px] font-bold text-[#9ca3af]">INITIAT.</div>
          <div class="text-sm font-bold leading-tight" style="color: {STAT_COLORS.agilite}">{calc.initiative}</div>
        </div>
        <div class="bg-[#111827] rounded-md px-1.5 py-1 text-center">
          <div class="text-[7px] font-bold text-[#9ca3af]">ARMURE</div>
          <div class="text-sm font-bold leading-tight text-[#60a5fa]">{calc.armure}</div>
        </div>
        <div
          onclick={() => doRoll('Vitesse', `d20${fmt(calc.mouvement)}`)}
          role="button"
          tabindex="0"
          onkeydown={(e) => e.key === 'Enter' && doRoll('Vitesse', `d20${fmt(calc.mouvement)}`)}
          title={`Jet de vitesse (d20)`}
          class="bg-[#111827] rounded-md px-1.5 py-1 text-center cursor-pointer hover:bg-[#1f2937] transition-colors"
        >
          <div class="text-[7px] font-bold text-[#9ca3af]">VITESSE</div>
          <div class="text-sm font-bold leading-tight text-[#4ade80]">{calc.mouvement}</div>
        </div>
        <div
          role="button"
          tabindex="0"
          title="Bonus d'attaque — cliquer pour modifier (vide = valeur de règle)"
          onclick={() => { if (!editingBonusAttaque) { bonusAttaqueDraft = ''; editingBonusAttaque = true; } }}
          onkeydown={(e) => e.key === 'Enter' && !editingBonusAttaque && ((bonusAttaqueDraft = ''), (editingBonusAttaque = true))}
          class="bg-[#111827] rounded-md px-1.5 py-1 text-center cursor-pointer hover:bg-[#1f2937] transition-colors"
        >
          <div class="text-[7px] font-bold text-[#9ca3af]">B. ATT.</div>
          {#if editingBonusAttaque}
            <!-- svelte-ignore a11y_autofocus -->
            <input
              type="number"
              value={bonusAttaqueDraft}
              oninput={(e) => (bonusAttaqueDraft = e.currentTarget.value)}
              autofocus
              placeholder={String(calc.bonusAttaque)}
              onblur={commitBonus}
              onkeydown={(e) => {
                // Enter commits and stops here: without stopPropagation the
                // event reaches the tile's own keydown, which sees the editor
                // closed again and immediately reopens it (issue #5).
                if (e.key === 'Enter') { e.preventDefault(); e.stopPropagation(); commitBonus(); }
                else if (e.key === 'Escape') { e.stopPropagation(); editingBonusAttaque = false; }
              }}
              class="w-full text-sm font-bold leading-tight bg-transparent border-b border-indigo-500 focus:outline-none text-center text-indigo-300"
            />
          {:else}
            <div class="text-sm font-bold leading-tight text-indigo-300">{fmt(calc.bonusAttaque)}</div>
          {/if}
        </div>
      </div>
      <div class="flex items-center justify-center gap-1 mt-2 pt-2 border-t border-[#374151] flex-wrap">
        {#each QUICK_DICE as d}
          <button
            onclick={() => addQuickDie(d.die)}
            title={`Ajouter 1${d.die} à la formule`}
            class="relative flex items-center gap-0.5 px-1.5 py-0.5 rounded-md bg-[#111827] border {(quickCounts[d.die.slice(1)] ?? 0) > 0 ? 'border-indigo-400' : 'border-[#374151]'} hover:border-indigo-500 hover:bg-[#1f2937] transition-colors text-[9px] font-bold text-indigo-300"
          >
            <svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round">{@html d.icon}</svg>
            <span>{d.die}</span>
            {#if (quickCounts[d.die.slice(1)] ?? 0) > 0}
              <span class="absolute -top-1.5 -right-1.5 min-w-3.5 h-3.5 px-0.5 rounded-full bg-indigo-500 text-white text-[8px] font-bold leading-[14px]">{quickCounts[d.die.slice(1)]}</span>
            {/if}
          </button>
        {/each}
        <input
          bind:value={quickFormula}
          placeholder="1d20+1d6…"
          class="w-24 min-w-0 px-1.5 py-0.5 bg-[#242424] border border-[#374151] rounded-md text-[10px] font-bold focus:outline-none focus:border-indigo-500"
        />
        <button
          onclick={() => { doRoll('Jet rapide', quickFormula); quickFormula = ''; }}
          disabled={!quickFormula || !isDiceFormula(quickFormula, sheet?.stats ?? {})}
          title="Lancer la formule"
          class="flex items-center gap-1 px-2 py-0.5 rounded-md bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 disabled:cursor-not-allowed transition-colors text-[10px] font-bold text-white"
        >
          🎲 Lancer
        </button>
      </div>
      <!-- Per-turn action diamonds (long hover shows the combat actions reference) + Attaque/Magique/Notes on the right -->
      <div class="flex items-center mt-2 pt-2 border-t border-[#374151]">
        <ActionDiamonds
          checks={sheet.actionChecks}
          onToggle={toggleActionCheck}
          compact
          class="flex items-center gap-4 flex-1 justify-center"
        />
        <div class="flex items-center gap-1 shrink-0 pl-2 border-l border-[#4b5563]">
          <button
            onclick={toggleAttack}
            title="Attaque (avantage / engagement)"
            class={`w-6 h-6 rounded-md border text-[11px] flex items-center justify-center transition-colors ${showAttack ? 'bg-indigo-600 border-indigo-400' : 'bg-[#111827] border-[#374151] hover:bg-[#374151]'}`}
          >
            ⚔️
          </button>
          <button
            onclick={toggleCapacity}
            title="Valeur brute (multiplicateur / base / dés)"
            class={`w-6 h-6 rounded-md border text-[11px] flex items-center justify-center transition-colors ${showCapacity ? 'bg-indigo-600 border-indigo-400' : 'bg-[#111827] border-[#374151] hover:bg-[#374151]'}`}
          >
            🪄
          </button>
          <button
            onclick={() => (showNotes = !showNotes)}
            title={showNotes ? 'Masquer les notes' : 'Voir les notes'}
            class={`w-6 h-6 rounded-md border text-[11px] flex items-center justify-center transition-colors ${showNotes ? 'bg-indigo-600 border-indigo-400' : 'bg-[#111827] border-[#374151] hover:bg-[#374151]'}`}
          >
            📝
          </button>
        </div>
      </div>
      <!-- Attack accordion: weapon dropdown + avantage slider + engagement -->
      {#if showAttack}
        <div class="mt-2 pt-2 border-t border-[#374151] space-y-2">
          {#if equippedWeapons.length === 0}
            <div class="text-[10px] text-[#9ca3af] text-center py-2">Aucune arme équipée</div>
          {:else if selectedAttackWeapon && attackCalc}
            <div class="flex items-center gap-1.5">
              <span class="text-[8px] font-bold text-[#9ca3af] shrink-0">ARME</span>
              <select
                bind:value={attackWeaponName}
                onchange={saveAttackSettings}
                class="flex-1 min-w-0 px-1.5 py-0.5 bg-[#242424] border border-[#374151] rounded-md text-[10px] font-bold focus:outline-none focus:border-indigo-500"
              >
                {#each equippedWeapons as w}
                  <option value={w?.nom}>{w?.nom || 'Sans nom'} — {w?.de}{weaponTagInfo(w).length ? ` · ${weaponTagInfo(w)[0].label}` : ''}</option>
                {/each}
              </select>
            </div>
            {#if weaponTagInfo(selectedAttackWeapon).length}
              <div class="flex flex-wrap gap-1" title="Propriétés de l'arme">
                {#each weaponTagInfo(selectedAttackWeapon) as tag}
                  <span use:tooltip={tag.desc} class="px-1 py-0.5 rounded border border-[#4b5563] bg-[#111827] text-[9px] font-semibold text-indigo-200">{tag.label}</span>
                {/each}
              </div>
            {/if}
            {#if attackCalc.taggedFinesse || attackFinesse !== null}
              <label
                class="flex items-center gap-1.5 cursor-pointer"
                title="Arme Finesse : coche pour utiliser l'Agilité et la répétition du bonus sur critique, décoche pour rester sur la Force"
              >
                <input
                  type="checkbox"
                  checked={attackCalc.finesse}
                  onchange={(e) => setAttackFinesse(e.currentTarget.checked)}
                  class="accent-indigo-500 h-3 w-3"
                />
                <span class="text-[9px] font-bold text-[#9ca3af]">FINESSE (AGILITÉ)</span>
              </label>
            {/if}
            {#if attackCalc.amplitude}
              <label class="flex items-center gap-1.5 cursor-pointer" title="Amplitude : à votre portée maximale (3 m), l'arme bénéficie de la propriété Finesse">
                <input type="checkbox" bind:checked={attackAmplitude} class="accent-indigo-500 h-3 w-3" />
                <span class="text-[9px] font-bold text-[#9ca3af]">À PORTÉE MAXIMALE (3 m) — Finesse</span>
              </label>
            {/if}
            <div>
              <div class="flex items-center justify-between">
                <span class="text-[8px] font-bold text-[#9ca3af]">AVANTAGE / DÉSAVANTAGE</span>
                <span
                  class={`text-[10px] font-bold ${attackAdv > 0 ? 'text-[#4ade80]' : attackAdv < 0 ? 'text-[#f87171]' : 'text-[#9ca3af]'}`}
                >
                  {attackAdv === 0 ? 'NEUTRE' : `${attackAdv > 0 ? '+' : ''}${attackAdv}`}
                </span>
              </div>
              <input
                type="range" min="-7" max="7" step="1" bind:value={attackAdv}
                oninput={saveAttackSettings}
                class="w-full accent-indigo-500 h-1.5"
              />
              <div class="text-[9px] text-[#9ca3af]">
                {attackCalc.diceCount} dés · {attackKeepLabel || "garder l'unique"} · {attackLevelLabel}{attackEngagement > 0 ? ' (après engagement)' : ''}
              </div>
            </div>
            <div>
              <div class="flex items-center justify-between">
                <span class="text-[8px] font-bold text-[#9ca3af]">ENGAGEMENT</span>
                <span class="text-[10px] font-bold text-indigo-300">
                  {attackEngagement === 0
                    ? 'AUCUN'
                    : attackCalc.hybrideEngagement
                      ? `${attackEngagement} · +${attackCalc.hybrideEngagement.force} Force +${attackCalc.hybrideEngagement.agilite} Agilité`
                      : `${attackEngagement} · ${fmt(attackCalc.engagementMod)} ${STAT_LABELS[attackCalc.engagementStat] || ''}${attackCalc.finesse ? ' ×(1+crits)' : ''}`}
                </span>
              </div>
              <input
                type="range" min="0" max="7" step="1" bind:value={attackEngagement}
                oninput={saveAttackSettings}
                class="w-full accent-indigo-500 h-1.5"
              />
            </div>
            <div class="text-[9px] text-[#9ca3af] leading-snug">
              <div>Jet : {attackCalc.diceCount}d{attackCalc.sides}{attackKeepLabel ? ` · ${attackKeepLabel}` : ''} · {attackCalc.brute ? 'pas de critique (Brute)' : `crit ${attackCalc.critFrom}+${attackCalc.gobelin ? ` (max ${attackCalc.maxCrits} critiques)` : ''}`}</div>
              <div>Dégâts : {attackCalc.hybride
                ? `dé + ${fmt(attackCalc.weaponBonus)} bonus + crits × (bonus − min(Force,0))`
                : `${attackCalc.keep ? `${attackCalc.keep} + ` : 'dé + '}${attackCalc.weaponBonus ? `${fmt(attackCalc.weaponBonus)} arme` : ''}${attackEngagement > 0 ? `${attackCalc.weaponBonus ? ' ' : ''}${fmt(attackCalc.engagementMod * attackEngagement)} ${STAT_LABELS[attackCalc.engagementStat]}` : ''}${attackCalc.finesse ? ' (répété ×crits)' : ''}`}{attackCalc.hache ? ' (Brutalité : explosion 2d, doubles)' : ''}{attackCalc.brute ? ' (Brute : pas de critique)' : ''}</div>
            </div>
            <button
              onclick={doAttackRoll}
              class="w-full py-1.5 rounded-md bg-indigo-600 hover:bg-indigo-500 transition-colors text-[11px] font-bold text-white"
            >
              ⚔️ ATTAQUER
            </button>
          {/if}
        </div>
      {/if}
      {#if showCapacity}
        <div class="mt-2 pt-2 border-t border-[#374151] space-y-2">
          <div>
            <div class="flex items-center justify-between">
              <span class="text-[8px] font-bold text-[#9ca3af]">MULTIPLICATEUR</span>
              <span class="text-[10px] font-bold text-indigo-300">×{capMult}</span>
            </div>
            <input
              type="range" min="0.5" max="20" step="0.5" bind:value={capMultiplier}
              class="w-full accent-indigo-500 h-1.5"
            />
          </div>
          <div>
            <div class="text-[8px] font-bold text-[#9ca3af] mb-0.5">CARACTÉRISTIQUE</div>
            <div class="flex gap-1">
              {#each ['force', 'agilite', 'esprit', 'social'] as s}
                <button
                  onclick={() => pickCapStat(s)}
                  class={`flex-1 px-1 py-0.5 rounded-md bg-[#111827] border text-[9px] font-bold transition-colors ${capStat === s ? '' : 'border-[#374151] text-[#9ca3af] hover:border-indigo-500 hover:bg-[#1f2937]'}`}
                  style={capStat === s ? `border-color: ${STAT_COLORS[s]}; color: ${STAT_COLORS[s]}` : ''}
                >
                  {STAT_LABELS[s]}
                </button>
              {/each}
            </div>
          </div>
          <div>
            <div class="flex items-center justify-between">
              <span class="text-[8px] font-bold text-[#9ca3af]">MOD · {STAT_LABELS[capStat]}</span>
              <span class="text-[10px] font-bold text-indigo-300">{capModValue}</span>
            </div>
            <input
              type="range" min="0" max="20" step="1"
              bind:value={capMod}
              oninput={() => { if (capMod == null) capMod = capModFloor(capStat); }}
              class="w-full accent-indigo-500 h-1.5"
            />
          </div>
          <div class="text-[9px] text-[#9ca3af]">Valeur brute : {capCount}d6 (×{capMult} · {capModValue} {STAT_LABELS[capStat]})</div>
          <button
            onclick={doCapacityRoll}
            class="w-full py-1.5 rounded-md bg-indigo-600 hover:bg-indigo-500 transition-colors text-[11px] font-bold text-white"
          >
            🪄 LANCER
          </button>
        </div>
      {/if}
    </div>

    {#if showNotes}
      <div class="shrink-0 px-3 py-2 border-b border-[#374151]">
        <div class="flex items-center justify-between mb-1.5">
          <span class="text-[9px] font-bold text-[#9ca3af]">NOTES</span>
          <button
            onclick={saveNotes}
            disabled={!notesDraftDirty}
            class="px-2.5 py-1 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 disabled:cursor-default rounded-lg text-[9px] font-bold transition-colors"
          >
            💾 Sauvegarder
          </button>
        </div>
        <textarea
          bind:value={notesDraft}
          oninput={() => (notesDraftDirty = true)}
          placeholder="Aucune note."
          class="w-full h-28 px-2 py-1.5 bg-[#242424] border border-[#374151] rounded text-[11px] leading-relaxed focus:outline-none focus:border-indigo-500 resize-y"
        ></textarea>
      </div>
    {/if}

    <!-- Favoris -->
    <div class="compact-favorites flex-1 min-h-0 overflow-y-auto scrollbar-thin p-2.5 space-y-2">
      <div class="text-[9px] font-bold text-[#9ca3af]">FAVORIS — cliquer pour lancer</div>

      {#if !pinnedSkills.length && !pinnedCapacities.length}
        <div class="text-[10px] text-[#9ca3af] bg-[#111827] rounded-md p-2.5">
          Aucun favori enregistré dans cette fiche.
        </div>
      {/if}

      {#each pinnedSkills as skillKey}
        <button
          class="w-full flex items-center gap-2 bg-[#111827] hover:bg-[#1f2937] rounded-md px-2.5 py-2 text-left transition-colors"
          onclick={() => doRoll(SKILL_LABELS[skillKey] || skillKey, `d20${skillMod(skillKey) >= 0 ? '+' + skillMod(skillKey) : skillMod(skillKey)}`, { zoomCrit: true })}
        >
          <div class="w-1 h-5 rounded-full" style="background: {skillColor(skillKey)}"></div>
          <span class="text-[11px] font-medium truncate">
            {SKILL_LABELS[skillKey] || skillKey}
            {#if sheet?.skills?.[skillKey]?.trained}
              <span class="inline-block w-1.5 h-1.5 rounded-full bg-indigo-400 align-middle" title="Maîtrisée — modificateur doublé"></span>
            {/if}
          </span>
          <span class="ml-auto text-[11px] font-bold" style="color: {skillColor(skillKey)}">d20 {fmt(skillMod(skillKey))}</span>
        </button>
      {/each}

      {#each sheet.customRolls ?? [] as roll}
        {#if roll?.formula && isDiceFormula(roll.formula, sheet?.stats ?? {})}
          <button
            class="w-full flex items-center gap-2 bg-[#111827] hover:bg-[#1f2937] rounded-md px-2.5 py-2 text-left transition-colors"
            onclick={() => doRoll(roll.name || roll.formula, roll.formula)}
          >
            <div class="w-1 h-5 rounded-full bg-slate-500"></div>
            <span class="text-[11px] font-medium truncate flex-1">{roll.name || roll.formula}</span>
            <span class="ml-auto text-[11px] font-bold text-slate-300">{roll.formula}</span>
          </button>
        {/if}
      {/each}

      {#each pinnedCapacities as capacity, i}
        {@const formula = capacity?.value?.main}
        <button
          class="w-full flex items-center gap-2 bg-[#111827] hover:bg-[#1f2937] rounded-md px-2.5 py-2 text-left transition-colors {formula && isDiceFormula(formula, sheet?.stats ?? {}) ? '' : 'opacity-60 cursor-default'}"
          onclick={() => formula && isDiceFormula(formula, sheet?.stats ?? {}) && doRoll(capacity.name || `Capacité #${i + 1}`, formula)}
          title={formula && isDiceFormula(formula, sheet?.stats ?? {}) ? `Lancer ${formula}` : 'Aucune formule de dés'}
        >
          <div class="w-1 h-5 rounded-full bg-indigo-500"></div>
          <div class="flex-1 min-w-0">
            <div class="text-[11px] font-semibold truncate">{capacity?.name || 'Sans nom'}</div>
            <div class="text-[9px] text-[#9ca3af] truncate">
              {capacity?.usage || '—'} · Coût {capacity?.cost?.total ?? 0}
              <span style="color: {suitColor(capacity?.cost?.color)}">{suitSymbol(capacity?.cost?.color)}</span>
            </div>
          </div>
          {#if formula && isDiceFormula(formula, sheet?.stats ?? {})}
            <span class="px-2 py-0.5 bg-slate-500 rounded text-[10px] font-bold shrink-0">{formula}</span>
          {/if}
        </button>
      {/each}

      {#if sheet.totem?.nom}
        <div
          use:tooltip={stripHtml(sheet.totem.description)}
          class="bg-indigo-600 rounded-md px-2.5 py-1.5 text-[9px] font-bold truncate cursor-help"
        >
          {#if sheet.totem?.image && !isImageUrl(sheet.totem.image)}
            <span class="mr-1">{sheet.totem.image}</span>
          {/if}
          TOTEM &nbsp;{sheet.totem.nom}
        </div>
      {/if}
    </div>

    <!-- Roll result (animated dice popup only; inline panel removed) -->
  {/if}
</div>

<style>
  .scrollbar-thin::-webkit-scrollbar {
    width: 4px;
  }
  .scrollbar-thin::-webkit-scrollbar-track {
    background: #374151;
    border-radius: 2px;
  }
  .scrollbar-thin::-webkit-scrollbar-thumb {
    background: #9ca3af;
    border-radius: 2px;
  }
</style>
