<script>
  import { ACTION_CHECKS, STAT_COLORS } from './characterSheet.js';

  // Rulebook color classes: guide-force (Force), guide-agilite (Agilité),
  // guide-esprit (Esprit), guide-social (Social) — mapped to the stat palette.

  let {
    checks = {},
    onToggle = () => {},
    compact = false,
    class: rootClass = 'flex items-center justify-center'
  } = $props();

  // ─── Combat actions reference (shown after a long hover) ───
  const ACTION_RULES = [
    {
      group: 'Bonus actions',
      entries: [
        {
          name: 'Attaque secondaire',
          stat: 'force',
          bullets: ['Une seconde attaque en mêlée', 'Sans modificateur aux dégâts']
        },
        {
          name: 'Poussée',
          stat: 'force',
          bullets: ['Repoussez une créature de 5 m', 'Contestation de vos jets d’Athlétisme']
        },
        {
          name: 'Ruée',
          stat: 'agilite',
          bullets: [
            'Augmentez votre vitesse de déplacement de moitié',
            'Vous permet un troisième mouvement durant le round'
          ]
        },
        {
          name: 'Planque',
          stat: 'agilite',
          bullets: [
            'Si vous êtes hors de vue ou obscurci, cachez-vous',
            'Faites un jet de Discrétion contre la Perception ennemie',
            'Au début de chaque round et chaque fois que vous entrez dans une ligne de vue, refaites un jet',
            'Toute action hostile vous dévoile',
            'Une action non hostile exige un nouveau jet pour rester planqué'
          ]
        },
        {
          name: 'Consommable',
          stat: 'agilite',
          bullets: ['Boire une potion', 'Utiliser un parchemin', 'Ou un consommable du même type']
        },
        {
          name: 'Échange d’équipement',
          stat: 'agilite',
          bullets: ['Alterner entre deux armes ou équipements']
        },
        {
          name: 'Stabilisation',
          stat: 'agilite',
          bullets: [
            'Mettez fin à une condition dont la sortie est possible',
            'Sur un allié ou sur vous si la condition le permet',
            'Exemples : À terre, Immobilisé, Endormi, Inconscient',
            'Certaines conditions peuvent exiger un jet contextuel selon la situation'
          ]
        },
        {
          name: 'Analyse',
          stat: 'esprit',
          bullets: [
            'Faites un jet d’Investigation : DC 10 + mod. Agilité',
            'Sur une créature adverse',
            'Découvre une résistance, une immunité, une vulnérabilité',
            'Ou un détail contextuel'
          ]
        },
        {
          name: 'Imprégnation',
          stat: 'esprit',
          bullets: [
            'Imprégnez une arme ou un projectile avec un consommable',
            'Si une source élémentaire est à portée (feu, poison, etc.), utilisez-la pour imprégner votre arme',
            'Ajoutez mod. Survie en dégâts élémentaires à votre prochaine attaque'
          ]
        },
        {
          name: 'Canalisation',
          stat: 'esprit',
          bullets: [
            'Canalisez votre catalyseur et activez son bonus de couleur pour ce round et le suivant',
            'Les capacités de la couleur correspondante voient leur coût réduit de votre modificateur d’Esprit + le bonus du catalyseur',
            'Si vous maniez deux catalyseurs à une main, vous pouvez les canaliser simultanément pour combiner leurs couleurs',
            'Le catalyseur s’entoure alors d’une aura de son type de dégâts',
            'En canalisant, vous donnez avantage à vos jets d’attaques avec le catalyseur et de valeur brute de capacités'
          ]
        },
        {
          name: 'Provocation',
          stat: 'social',
          bullets: [
            'Provoquez une créature',
            'Faites un jet de Représentation contre sa Perspicacité',
            'La créature provoquée ne peut cibler que vous jusqu’à la fin du round'
          ]
        },
        {
          name: 'Flatterie',
          stat: 'social',
          bullets: [
            'Faites un jet de Tromperie contre la Perspicacité de l’allié',
            'En cas de réussite, l’allié gagne + mod. Social aux dégâts de sa prochaine attaque'
          ]
        }
      ]
    },
    {
      group: 'Réactions',
      entries: [
        {
          name: 'Attaque d’opportunité',
          stat: 'force',
          bullets: [
            'Si un ennemi quitte votre zone de contrôle',
            'S’il lance une capacité à distance',
            'Ou s’il est attaqué par un allié en mêlée',
            'Vous pouvez l’attaquer',
            'Si vous jouez dual wield, attaquez avec vos deux armes'
          ]
        },
        {
          name: 'Parade',
          stat: 'force',
          bullets: [
            'Parez avec votre bouclier ou vos armes',
            'Vous réduisez les dégâts subits avant réduction d’armure',
            'Avec bouclier : déflexion de l’armure + parade du bouclier + mod. Force',
            'Sans bouclier : parade de l’arme = valeur maximale du dé de votre arme / 2 + mod. Agilité',
            'Exemple : 3 pour 1d6',
            'Si vous annulez la totalité des dégâts, vous activez Feintre'
          ]
        },
        {
          name: 'Bastion',
          stat: 'force',
          bullets: ['Interceptez une attaque ciblée visant un allié', 'Jet d’Acrobaties = 3 + 2 × distance en mètres']
        },
        {
          name: 'Soutien',
          stat: 'force',
          bullets: ['Lorsqu’un allié dans votre zone de contrôle attaque', 'Offrez-lui avantage à son jet d’attaque']
        },
        {
          name: 'Ciblage',
          stat: 'agilite',
          bullets: [
            'Lorsqu’un ennemi agit (attaque, mouvement, etc.)',
            'Utilisez votre réaction pour vous focaliser sur lui',
            'Analysez ses mouvements',
            'Vous vous octroyez avantage pour un tir contre lui au prochain tour'
          ]
        },
        {
          name: 'Précipitation',
          stat: 'agilite',
          bullets: [
            'Utilisez votre réaction pour précipiter votre tour',
            'Faites un jet d’initiative avec avantage pendant l’action d’une autre créature',
            'Si votre résultat dépasse son initiative, vous pouvez jouer immédiatement votre Action et/ou Bonus Action',
            'Vos deux actions sont résolues simultanément selon la décision du MJ',
            'Si vous avez déjà joué ce round, faites un jet d’initiative avec avantage contre 10 + l’initiative de la créature actuelle',
            'En cas de réussite, vous pouvez jouer votre Action et/ou Bonus Action du round suivant immédiatement'
          ]
        },
        {
          name: 'Harmonisation',
          stat: 'esprit',
          bullets: [
            'Lorsqu’une créature lance une capacité utilisant l’Esprit',
            'Accentuer : + mod. Esprit au jet de valeur brute de la capacité et au seuil de sauvegarde',
            'Atténuer : - mod. Esprit aux dégâts directs et au seuil de sauvegarde'
          ]
        },
        {
          name: 'Altération',
          stat: 'esprit',
          bullets: [
            'Lorsque vous utilisez une capacité',
            'Vous pouvez ajuster son effet ou sa portée',
            'Sans augmenter sa puissance',
            'Peut potentiellement activer une combinaison élémentaire'
          ]
        },
        {
          name: 'Dissuasion',
          stat: 'social',
          bullets: [
            'Faites un jet d’Intimidation contre la Perspicacité de l’ennemi',
            'Donnez-lui désavantage à son attaque en mêlée'
          ]
        },
        {
          name: 'Coordination',
          stat: 'social',
          bullets: [
            'En réaction, choisissez un allié à 2 × mod. Persuasion m',
            'Cet allié peut immédiatement utiliser une réaction',
            'Ou refaire son jet de sauvegarde contre la capacité qui le vise'
          ]
        }
      ]
    },
    {
      group: 'Actions',
      entries: [
        { name: 'Attaquer', stat: 'force', bullets: ['Attaquez votre cible'] },
        {
          name: 'Esquive',
          stat: 'agilite',
          bullets: ['Désavantage aux attaques contre vous', 'Pas d’attaques d’opportunité']
        }
      ]
    }
  ];

  // The reference panel opens from the round "?" button, not from a hover
  // (issue #5): a hover is undiscoverable and fires by accident. It stays open
  // until closed (✕ / Escape / click outside) so the text can be read.
  let panelVisible = $state(false);

  function close() {
    panelVisible = false;
  }
</script>

<svelte:window onkeydown={(e) => e.key === 'Escape' && close()} />

<div class={rootClass}>
  {#each ACTION_CHECKS as ac}
    <button
      onclick={() => onToggle(ac.key)}
      title={ac.label}
      class="group flex items-center {compact ? 'gap-1.5' : 'gap-2.5'}"
    >
      <span
        class="rotate-45 rounded-[2px] border-2 transition-colors {compact ? 'h-2.5 w-2.5' : 'h-3 w-3'} {checks?.[ac.key]
          ? 'bg-indigo-500 border-indigo-300'
          : 'bg-transparent border-[#4b5563] group-hover:border-[#9ca3af]'}"
      ></span>
      <span
        class="font-bold tracking-wide {compact ? 'text-[9px]' : 'text-[10px]'} {checks?.[ac.key]
          ? 'text-white'
          : 'text-[#9ca3af]'}"
      >
        {ac.label}
      </span>
    </button>
  {/each}
  <button
    onclick={() => (panelVisible = true)}
    title="Guide des actions, bonus actions et réactions"
    aria-label="Guide des actions de combat"
    class="shrink-0 w-4 h-4 rounded-full border border-[#4b5563] bg-[#111827] text-[#9ca3af] hover:text-white hover:border-[#9ca3af] text-[9px] font-bold leading-none flex items-center justify-center transition-colors"
  >?</button>
</div>

{#if panelVisible}
  <div
    class="fixed inset-0 z-[70] bg-black/60 flex items-center justify-center p-3"
    onclick={close}
    role="presentation"
  >
    <div
      class="bg-[#1f2937] border border-[#374151] rounded-xl w-[min(94vw,560px)] max-h-[86vh] flex flex-col overflow-hidden"
      onclick={(e) => e.stopPropagation()}
      role="dialog"
      tabindex="-1"
    >
      <div class="h-9 flex items-center px-3 border-b border-[#374151] shrink-0 bg-[#111827]">
        <span class="text-[11px] font-bold tracking-wide">ACTIONS DE COMBAT</span>
        <button
          onclick={close}
          title="Fermer"
          class="ml-auto w-6 h-6 rounded-full bg-[#242424] border border-[#374151] text-[#9ca3af] hover:text-white text-[10px] font-bold flex items-center justify-center transition-colors"
        >
          ✕
        </button>
      </div>
      <div class="flex-1 min-h-0 overflow-y-auto scrollbar-thin p-3 text-left">
        {#each ACTION_RULES as section}
          <div class="text-[10px] font-bold text-indigo-300 uppercase tracking-wide">{section.group}</div>
          {#each section.entries as entry}
            <div class="mt-2">
              <div class="text-[11px] font-bold" style="color: {STAT_COLORS[entry.stat] ?? '#e5e7eb'}">{entry.name}</div>
              <ul class="mt-0.5 space-y-0.5">
                {#each entry.bullets as bullet}
                  <li class="text-[10px] leading-snug text-[#9ca3af] flex gap-1.5">
                    <span class="text-[#6b7280] shrink-0">•</span>
                    <span>{bullet}</span>
                  </li>
                {/each}
              </ul>
            </div>
          {/each}
          <div class="h-2"></div>
        {/each}
      </div>
    </div>
  </div>
{/if}

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
