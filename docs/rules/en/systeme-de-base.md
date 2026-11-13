> **Game framework:** the general rules describe Simple Adventure play. Campaign mode is an optional variant still under development, kept separately in [[en/campaign/progression|Campaign advancement]]. Its starting pool is limited to cards from 2 through 8; this restriction does not apply to standard play.

## Game System: Dice, Cards and Tokens

The system rests on **three** main elements: **dice**, **cards** and **tokens**.

Each plays a distinct but complementary role in resolving actions, managing resources and supporting narrative mechanics.

- **Dice** determine the outcome of actions, checks or effects. They introduce chance and measure success or failure.
- **Cards** represent the character's mental, physical or symbolic resources. They activate abilities, interact with totems and support narrative mechanics such as relationships or flashbacks.
- **Tokens** represent the mastery associated with the main attributes (Strength, Agility, Spirit, Social). They let you adjust or influence cards and dice.

These three elements work together: **dice** decide the outcome, **cards** define what you can attempt, and **tokens** provide ways to modify or strengthen those actions.

Their interaction balances chance, strategy and storytelling throughout the game.

## 🎲 Dice

Dice represent the element of chance in the system. They measure the success, failure or power of an action.

### Uses

- The **d20** is mainly used for **skill checks** and **initiative rolls**.
- Other dice (**d4, d6, d8, d10, d12**) are mainly used for **weapons**, **abilities** or certain **special effects**.
- The GM is free to use any type of die to represent a particular event or narrative effect.

### Modifiers

Dice rolls are often influenced by the **character's attributes**.

**Rounding convention:** unless a rule explicitly says otherwise, all calculations and fractional results are always rounded down.

- Example: for a Strength check, roll **1d20 + the character's Strength Mod**.
- Example: a magical attack might deal **1d8 + Spirit Mod** damage.

**Notation: Attribute Score, Attribute Mod and Skill Mod**

- **Attribute Score**: the Strength, Agility, Spirit or Social value. Formulas that explicitly use the score, such as HP, still use that score.
- **Attribute Mod**: `(score − 10) ÷ 2`, rounded down. Example: Strength 16 gives **Strength Mod = +3**.
- **Skill Mod**: the skill bonus, including proficiency. It equals the associated attribute modifier, or **twice that modifier if you are proficient in the skill**. Do not add the Attribute Mod again to the roll.
- Example: with Strength 16, **Athletics Mod = +3**, or **+6** if you are proficient in Athletics. Resisting physical crowd control that calls for Athletics uses **d20 + Athletics Mod**.
- When a check names only an attribute, without naming a skill, use **d20 + that Attribute Mod**: a “Spirit check” means **d20 + Spirit Mod**, and a “Strength check” means **d20 + Strength Mod**. No skill proficiency applies to that check.

### Success and failure

A die roll can be interpreted as a **direct result** (e.g. damage) or as an **attempt** whose success depends on a **difficulty threshold** set by the GM or the situation.

- On a d20, a **natural 1** is always a **critical failure**: modifiers are ignored.
- On a d20, a **natural 20** is always a **critical success**, regardless of modifiers.
- On a saving throw, a **natural 20 completely negates the ability’s effect**, even if that ability would normally have a partial effect on a successful save.
- Example of success: a character jumps across a chasm and rolls **18 on 1d20**; the GM decides this is enough to succeed.
- Example of failure: a character tries to open a locked door and rolls **7 on 1d20**; they fail and may make a noise or trigger a trap.

### 🎲 Advantage

An **advantage** represents favorable circumstances, preparation, precision or a situation that increases the chance of getting a better result on a die roll.

Conversely, a **disadvantage** represents interference, fatigue or unfavorable circumstances.

- On a **d20**, one advantage adds **1 die** to the roll; keep the **best result**.
- On **any other type of die** (d4, d6, d8, d10, d12), one advantage adds **2 dice** to the roll; keep the **original number of dice** specified by the action.
- Disadvantage follows the same logic, but you keep the **worst results**.

### Stacking

Advantages and disadvantages can **stack**.

Each additional advantage adds the corresponding dice to the roll (+1 on a d20, +2 on other dice).

Disadvantages cancel advantages and also stack.

### Criticals with advantage

When a critical occurs, make its reroll with **one less advantage** than the previous roll. Each new critical removes another advantage. At 0 advantage, criticals continue with 1 die.

### Narrative consistency

Dice are not only used to resolve actions.

They are also a tool for the GM and players to decide how a scene or unexpected event unfolds.

A die result can guide the story, introduce a risk or create an opportunity—even when no specific rule requires it.

## 🃏 Cards

Cards represent the character's mental, physical or symbolic resources. They are used to perform most important actions in the game.

### Hand and draw pile

- The draw pile is **shared by all players** and treated as **theoretically infinite**. For physical play, use as many standard **52-card decks** as possible, preferably **3 decks shuffled together**, with no jokers.
- Face-card values: **Jack = 11, Queen = 12, King = 13, Ace = 14**.
- When the physical draw pile is empty, shuffle the discard pile to form a new shared draw pile.
- Each player may have at most **3 normal cards in hand at any time**, unless this limit is explicitly modified, notably by Spirit Slots or a racial trait.
- In combat, at the start of each turn, you may **draw 1 card** only if a hand slot is free. If your hand is full, discard one first to make room before drawing.
- Outside combat, cards are drawn at regular intervals or at a pace set by the GM.
- All cards may be **treated as a 1 of any suit**.

### Types of cards

- **Normal Cards**: basic cards, drawn and discarded throughout the game.
- **Crystallized Cards**: the card is replaced by its crystallized version, represented in red, while keeping its value and suit. It does not count towards the maximum hand limit, cannot be exchanged, does not interact with tokens or the Totem, and can be played like a normal card.

### Suits and associated abilities

1. **Hearts**: healing, buffs and protection. Example: **Magic Shield** (damage reduction).
2. **Diamonds**: raw damage and destruction. Example: **Fireball** (Raw Power: Spirit Mod d6).
3. **Clubs**: control and manipulation. Example: **Vegetal Entanglement** (immobilization).
4. **Spades**: special magic, subtlety and mobility. Examples: teleportation, curses.

### General uses

- Cards **activate powers** and **interact with the Totem**, the character's central mechanic.
- To pay for an ability, the card total must meet or exceed its cost, using the appropriate suits. Payment, reductions and surcharge are detailed in [[en/capacites|Abilities and Totems]].
- They can also be used **narratively**, to represent an initiative, emotion, memory or significant action. Aspects, Bonds and flashbacks are detailed in [[en/narration|Narration]].
- Cards are **drawn** and **discarded** regularly as situations require. The GM can use them as an indicator of tension, resources or opportunities, depending on the scene.

## 🪙 Tokens

Tokens are resources linked to attributes. They support card management and improve basic attacks.

### Reserve and recovery

- Each player has a reserve of **tokens per attribute**.
- **Number of available tokens = max(0, 1 + associated attribute modifier).** Then add any racial bonuses.
- Tokens are consumed when used and **reset after a short or long rest**.

### Tokens for cards

- **Strength Tokens:** draw a card.
- **Agility Tokens:** draw a card of a specific suit instead of a random one.
- **Social Tokens:** exchange one of your cards with an ally's card.
- **Spirit Tokens:** create Spirit Slots and crystallize cards, following the rules below.

### Spirit Slots and crystallization

- Spend one Spirit Token to create a **Spirit Slot**. Each slot increases your hand limit by 1.
- You cannot have fewer **non-crystallized cards** than Spirit Slots, because a slot cannot be freed.
- You may crystallize a card by bursting, and therefore consuming, one Spirit Slot. Crystallizing a card means replacing it with its crystallized version, represented in red: it does not count towards the hand limit, cannot be exchanged, and cannot interact with tokens or the Totem. It keeps its value and suit.

### Combat tokens

These rules are also repeated in [[en/combat|Combat]] for reference during an attack.

- **Strength:** after a basic attack, or after an ability that uses base damage, allows performing **a second complete attack** (double strike).
- **Agility:** on a basic attack, allows **curving** the attack to hit up to **3 different targets** with the same damage (possible during an uninterrupted movement).
- **Spirit:** on a magical/elemental basic attack, applies a **Reverberation**: at the start of your next turn, calculate **2× the attack’s raw damage, before any reduction**, then apply damage reductions to the Reverberation normally.
- **Social:** without making an attack yourself, have an ally within **20 m** make a **basic attack**. You may modify that attack with another of your combat tokens. The ally may also use their own tokens.

Using a combat token is **free**: it costs no action, bonus action or reaction. You may decide to use it **after the roll**, but its effect must involve a **basic attack**. You may spend at most **1 combat token of each attribute per round**. A single attack may receive at most **1 combat token of each attribute**, regardless of who spends it.

### Combining combat tokens

Tokens combine **multiplicatively**, their effects applying to each other:

- **Strength + Agility** → Two attacks, each able to hit up to 3 targets (×6).
- **Strength + Spirit** → Two attacks, each reverberating (×6).
- **Strength + Social** → An ally performs two attacks.
- **Agility + Spirit** → Three targets, each suffering a reverberation (×9).
- **Agility + Social** → An ally attacks up to 3 targets.
- **Spirit + Social** → The ally's attack is reverberated (×3).

In summary: **Strength** multiplies attacks (×2), **Agility** multiplies targets (up to ×3), **Spirit** multiplies damage (×3 with reverberation), and **Social** transfers the attack to an ally, who benefits from the effects of other tokens.

## Rest

- **Cards, for both types of rest:** you may discard as many normal cards from your hand as you wish, then draw back up to your hand limit. You do not have to discard them all. All your Spirit Slots are consumed and their cards become crystallized. You keep all cards that were already crystallized.
- **Short rest:** 1 hour of uninterrupted rest in a quiet place, consuming rations. It restores all tokens, restores half of maximum HP without exceeding the maximum, and removes 1 Fatigue level.
- **Long rest:** 7 hours of uninterrupted sleep in a quiet place, consuming rations. It restores all tokens and all HP, and removes 2 Fatigue levels.
