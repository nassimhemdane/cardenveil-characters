# Totem, Abilities & Cards

# **Abilities and Cards**

To use an ability, the total value of cards spent must be **greater than or equal to its cost: card total ≥ cost**. The ability becomes usable as soon as their combined value reaches at least the **ability's cost**. Exact payment is valid. Each card played must match the **ability type** (Heart, Diamond, Club or Spade). For example, a total of 15 is enough to use a healing ability that costs 15.

An ability always requires spending **at least 1 card**. If its final cost is 0 or less, it may be used with **any card**, regardless of its suit or value.

## **Card and Ability Management**

- **Number of known abilities** = (Spirit ÷ 2, rounded down) + 1.
- **Hand limit** = **3 normal cards at any time**. At the start of your turn, you need a free slot to draw; if your hand is full, discard one card first.
- You can use **crystallized cards** as normal cards.
- All cards can be **considered** as **1** of **any** suit.
- **An ability** can for example be a mage spell (dependent on **spirit**) like a complex warrior maneuver (dependent on **agility**), a very brutal blow cracking the ground under the adversary (dependent on **strength**) or even an inspiring chant from a bard (dependent on **social**).
- **The cost** of an ability is first reduced by `(associated attribute − 10)`.
- A player may **derive** an existing ability to change how it works on the fly. The GM then sets a multiplier from **×1.5 to ×3**, applied **after the associated-attribute reduction**.
- If range is not specified, a **base-damage** ability uses the **zone of control**; an ability described as ranged has a range of **20 m**.
- At the **start** of your turn, draw **one** card if a slot is free. If your hand is full, discard one card first to make room before drawing.
- When you cast a **ranged** ability (targeting a creature more than **1.5 m** away) while inside an enemy creature’s zone of control, that creature may make an **opportunity attack**.
- **Crystallized cards** cannot be used for the **totem** and do not interact with **tokens**.

---

## **Card Types and Associated Abilities**

1. **Hearts**: Healing, buffs, and protection.
    - Example: **Magic Shield** (damage reduction).
2. **Diamonds**: Raw damage and destruction.
    - Example: **Fireball** (2d6 + Spirit Mod).
3. **Clubs**: Control and manipulation.
    - Example: **Vegetal Entanglement** (immobilization).
4. **Spades**: Special magic, subtlety, and mobility.
    - Example: Teleportation, curses etc.

You will find below indications to create an ability

---

## **Save DC**

The threshold to reach or exceed (result ≥ threshold) for adversaries to dodge your abilities:

**Save DC = Incantation Attribute (e.g. Spirit) + Surcharge** 

**Surcharge = total value of cards paid − final ability cost.** Every excess point counts, even when unavoidable. Example: for a final cost of 10, paying 13 gives a surcharge of 3.

---

## **Ability Saves**

When you are the target of an ability, make a **saving throw using the appropriate Skill Mod** (**Acrobatics** [Agility] for **AOE**, **Athletics** [Strength] for physical controls, **Arcana** [Spirit] for magical controls and **Insight** [Social] for psychic controls):

- **d20 + the associated Skill Mod**: Acrobatics Mod for AOE, Athletics Mod for physical crowd control, Arcana Mod for magical crowd control and Insight Mod for psychic crowd control. Proficiency is already included. If only an attribute is specified, without a named skill, use that Attribute Mod.
- A target may choose to **fail its save voluntarily**, except on an **Insight** save.
- A **natural 20** always succeeds on the save and completely negates the ability’s effect, regardless of its description.
- The ability must state the outcome of a successful save. If it does not, use the default rule:
    - **Athletics:** half damage and no control effect.
    - **Acrobatics:** half damage.
    - **Arcana:** resist the effect and take half damage.
    - **Insight:** resist the effect and take half damage.
- On a failure, the target suffers the full effect.

---

## **Concentration**

- A character has only **one concentration** and may extend only one ability with it.
- They may use several concentration abilities during the same round. Their effects may coexist during that round, but the character chooses which one to extend with concentration; the others are not extended into the next round.
- After taking damage, make a **Willpower check: d20 + Resilience Mod + any bonuses**. The threshold equals half the damage actually taken after all reductions, rounded down. A result greater than or equal to the threshold maintains concentration; a failure loses it.

---

## **Creating an Ability**

- **Name**: *(The name of the ability, for example, "Fireball")*
- **Description**: *(A narrative and technical description of the ability. For example: "An explosion of flames erupts, dealing damage in a zone with a 6-meter radius.")*
- **Action Type**: *(Action, bonus action, reaction, etc. This field must always be specified.)*
- **Value**: *(What the ability measures, for example: "Damage = 4d10", "Healing = 2d8", "Distance traveled = 10 meters", "Duration = 2 turns", etc.)*
- **Associated Attribute**: *(The attribute used for calculation, for example: "Spirit", "Strength", "Agility")*
- **Range**: *(If absent: zone of control for base damage; 20 m for a ranged ability.)*
- **Duration**: *(If a non-instantaneous effect does not specify its duration, it lasts 1 round.)*
- **Concentration**: *(If not specified, the ability does not require concentration.)*
- **Targets**: *(If not specified, the ability targets one creature.)*
- **Global Cost**: *(The total cost in cards to activate the ability. For example: 12.)*
- **Save**: *(State the skill used and the outcome of a success. If it is not stated and cannot be inferred, no save applies.)*
- **Reduced Cost**: *(The cost after reduction for the player using the ability, based on their special abilities or totem. For example: 9 if the reduction is 3.)*
- **Ability Suit**: *(The suit of cards needed to activate the ability. For example: "Diamonds", "Spades", "Hearts", or "Clubs.")*

If the save is not written, infer it as follows: **Athletics** for physical control, including an AOE; otherwise **Acrobatics** for an AOE; **Insight** for a psychic effect; **Arcana** for a magical effect. Athletics takes priority for physical control in an AOE.

---

## **Making an Ability Roll**

When a character uses an **ability**, they rely on two reference values:

- **Raw Power (contextual Mod d6)**: roll a **number of six-sided dice equal to the contextual attribute modifier**, and add their results (Strength, Agility, Spirit or Social depending on the ability). This value does not depend on the weapon.
- **Base Damage**: equivalent to an **attack damage roll** with the equipped weapon (weapon die, mod, bonus, crits, advantages).

Abilities then apply a **multiplier** to one of these two values:

- **Raw Power (contextual Mod d6) Ability**: the multiplier increases the **number of dice rolled**.
    > Example: Explosion – deals 2× Raw Power (contextual Mod d6).
    > 
- **Base Damage Ability**: applies a **multiplier** to the character's **base damage** (e.g. *2.5 base damage* or *3 base damage*), following the rules of a **base damage roll** (see section Attacks & Damage).

---

### 🔸 **Making a Raw Power (contextual Mod d6) Ability Roll**

1. 🌀 **Identify the ability**
   - Check the **multiplier (K)** indicated.
   - Determine the **contextual modifier (Mod)** used (Strength, Agility, Spirit or Social).
   - The ability value is defined by:

     **Value = (K × Mod)d6.** The multiplier increases the number of dice; it does not multiply their sum. Example: **3 × 2d6 = 6d6**.

   - If the contextual modifier is zero or negative, Raw Power is **0d6**, therefore 0.

   - This roll does not depend on the **weapon** and **cannot crit**.

---

### ➕ **Advantages and Disadvantages**

- **Advantage**: Repeat the entire dice-pool roll **3 times** and keep the **highest total**.
- **Disadvantage**: Repeat the entire dice-pool roll **3 times** and keep the **lowest total**.
- **Cumulative**: Each additional advantage or disadvantage adds **2 rolls**.
- **Cancellation**: Advantages and disadvantages cancel each other out one by one.
- **Critical Hits**: None of these rolls can trigger a critical hit.

### 🔸 **Make an Ability Roll for Base Damage**

1. ⚔️ **Identify the ability**
    - Check the **Base Damage Multiplier (K)** indicated.
2. 🎲 **Make a Base Damage Roll**
    - Make a single **normal base damage roll**: weapon die, modifier, weapon bonus, advantages, critical hits, etc.
    - (The full procedure is described in the *Base Damage* section.)
3. ✖️ **Apply Multiplier K**
    - Simply multiply the result of your **base damage roll** by **K**.

---

# **Tokens**

Tokens are resources linked to attributes, used exclusively to facilitate card management, such as drawing extra cards, choosing their suit, or optimizing their use during your actions.

### **General Rules:**

- Each player has a certain number of **tokens** per attribute.
- **Number of available tokens = max(0, 1 + associated attribute modifier).** Then add any racial bonuses.
- Tokens **reset after a short or long rest**.

---

### **Types of Tokens and Their Effects**

- **Strength Tokens:** Draw a card.
- **Agility Tokens:** Draw a card of a specific suit instead of a random one.
- **Social Tokens:** Exchange one of your cards with an ally's card.
- **Spirit Token:**
    - Spend one Spirit Token to create a **Spirit Slot**. Each slot increases your hand limit by 1.
    - You cannot have fewer **non-crystallized cards** than Spirit Slots, because a slot cannot be freed.
    - You may crystallize a card by bursting, and therefore consuming, one Spirit Slot. Crystallizing a card means replacing it with its crystallized version, represented in red: it does not count towards the hand limit, cannot be exchanged, and cannot interact with tokens or the Totem. It keeps its value and suit.

---

### **Tokens to Improve Basic Attacks**

- **Strength Tokens:**
    
    After a basic attack, or after an ability that uses base damage, allows performing **a second complete attack** (double strike).
    
- **Agility Tokens:**
    
    On a basic attack, allows **curving** the attack to hit up to **3 different targets** with the same damage (possible during an uninterrupted movement).
    
- **Spirit Tokens:**
    
    On a magical/elemental basic attack, applies a **Reverberation**: at the start of your next turn, calculate **2× the attack’s raw damage, before any reduction**, then apply damage reductions to the Reverberation normally.
    
- **Social Tokens:**
    
    Without making an attack yourself, have an ally within **20 m** make a **basic attack**. You may modify that attack with another of your combat tokens. The ally may also use their own tokens.
    
⚡ Using a combat token is **free**: it costs no action, bonus action or reaction. You may decide to use it **after the roll**, but its effect must involve a **basic attack**. You may spend at most **1 combat token of each attribute per round**. A single attack may receive at most **1 combat token of each attribute**, regardless of who spends it.

---

### **Token Multiplicativity**

Tokens combine **multiplicatively**, their effects applying to each other:

- **Strength + Agility** → Two attacks, each able to hit up to 3 targets (×6).
- **Strength + Spirit** → Two attacks, each reverberating (×6).
- **Strength + Social** → An ally performs two attacks.
- **Agility + Spirit** → Three targets, each suffering a reverberation (×9).
- **Agility + Social** → An ally attacks up to 3 targets.
- **Spirit + Social** → The ally's attack is reverberated (×3).

👉 **In summary:**

- **Strength** multiplies attacks (×2).
- **Agility** multiplies targets (up to ×3).
- **Spirit** multiplies damage (×3 with reverberation).
- **Social** transfers the attack to an ally, who benefits from the effects of other tokens.

# Totems

**Totems** are unique **META abilities** that modify the usual game rules and the way cards are used. They constitute **the core of the character's mechanical identity**: their abilities are generally designed to interact with their Totem, creating a playstyle unique to them.

### General Rules

- **Unique Totem:** Each character can possess only one Totem.
- **META Mechanic:** A Totem modifies or enriches the game's classic mechanics rather than simply providing an additional ability.
- **Card Management:** Every Totem must interact with cards, notably by allowing them to be blocked, discarded, or exploiting their values and suits. **Crystallized Cards** can never be used to activate a Totem.
- **Custom Totem:** A player may propose their own Totem, in agreement with the GM. Otherwise, they can draw inspiration from the archetypes presented below.

## The 7 Pillars of a Totem

The Totem is **the heart of the character**: it defines its main mechanic and influences its playstyle. To design a Totem, one can rely on seven elements:

1. **Archetype:** The type of power upon which the Totem relies: invocation, transformation, charge accumulation, rule manipulation, etc.
2. **Activation:** The way to use the Totem, notably the cards to block or discard, and any necessary actions.
3. **Central Mechanic:** The unique rule that defines how the Totem functions and distinguishes the character from others.
4. **Evolution:** How the Totem functions over time: immediate effect, persistent effect, resource accumulation, progression, or delayed triggering.
5. **Application:** The concrete effects of the Totem: damage, protection, movement, control, exploration, or social interactions.
6. **Limits:** The constraints that frame its use: cost, duration, range, number of uses, special conditions, or weaknesses.
7. **Interaction with Abilities:** The way the character's abilities use, reinforce, or extend the Totem's mechanic.

**A good Totem does not need to be complex.** It should primarily offer an original central mechanic, rich enough for several abilities to be built around it.

## 10 Totem Archetypes

The following archetypes are **non-exhaustive creation molds**. They can be adapted or combined to create original Totems.

### 1. Invocation

**Example — Mystical Companion**

- **Activation:** Lock a card to summon a companion.
- **Mechanic:** The companion has different behavior depending on the card's suit.
- **Evolution:** It can gain new properties over the course of combat.
- **Application:** Attack, protect, or assist its invoker.
- **Limits:** Only one active summoning, maintained by the locked card.
- **Interaction:** Abilities allow commanding, moving, or improving the companion.

### 2. Transformation

**Example — Metamorphosis**

- **Activation:** Lock a card to adopt a particular form.
- **Mechanic:** Each suit corresponds to a different transformation.
- **Evolution:** The transformation can be reinforced or replaced.
- **Application:** Modify characteristics, attacks, or mobility.
- **Limits:** Transformations are mutually exclusive and possess weaknesses.
- **Interaction:** Abilities produce additional effects depending on the active form.

### 3. Accumulation

**Example — Kinetic Energy**

- **Activation:** Lock a card to begin accumulating charges.
- **Mechanic:** Certain successful actions generate charges.
- **Evolution:** Charges accumulate up to a limit.
- **Application:** Improve damage, defense, or movement.
- **Limits:** Charges can be lost or consumed.
- **Interaction:** Abilities spend charges to amplify their effects.

### 4. Marking

**Example — Progressive Curse**

- **Activation:** Discard a card to mark a creature.
- **Mechanic:** The mark applies a particular condition.
- **Evolution:** Marks can accumulate or become more powerful over time.
- **Application:** Weaken, control, or inflict damage.
- **Limits:** Marks can be dissipated and their accumulation is limited.
- **Interaction:** Abilities exploit, propagate, or consume marks.

### 5. Space Manipulation

**Example — Spatial Distortion**

- **Activation:** Discard a card to modify a portion of the environment.
- **Mechanic:** Create passages, move surfaces, or alter distances.
- **Evolution:** Multiple alterations can interact with each other.
- **Application:** Modify movement, ranges, and positioning.
- **Limits:** Range, duration, and number of alterations are limited.
- **Interaction:** Abilities use alterations to produce new trajectories or effect zones.

### 6. Weapons and Objects

**Example — Linked Arsenal**

- **Activation:** Discard a card to summon a particular weapon.
- **Mechanic:** Each suit determines a weapon and its properties.
- **Evolution:** Weapons can be improved, exchanged, or combined.
- **Application:** Diversify attacks and defensive options.
- **Limits:** Number of active weapons is limited.
- **Interaction:** Abilities exploit the properties of each weapon.

### 7. Tempo

**Example — Temporal Echo**

- **Activation:** Lock a card to memorize an action.
- **Mechanic:** Allow reproducing or deferring this action.
- **Evolution:** The action can remain stored until its triggering.
- **Application:** Modify the rhythm of actions and reactions.
- **Limits:** Only one stored action, with limited duration.
- **Interaction:** Abilities can be memorized then triggered under particular circumstances.

### 8. Metarules

**Example — Fate Manipulation**

- **Activation:** Discard a card to modify a roll.
- **Mechanic:** The value or suit of the card determines the allowed modification.
- **Evolution:** The effect is generally immediate.
- **Application:** Influence attack, saving throw, or skill rolls.
- **Limits:** Modification capped and triggering limited.
- **Interaction:** Abilities can exploit the successes or failures thus caused.

### 9. Mental Influence

**Example — Emotional Aura**

- **Activation:** Lock a card to emit an aura.
- **Mechanic:** The suit determines the emotion transmitted to nearby creatures.
- **Evolution:** The effect can intensify or change depending on interactions.
- **Application:** Influence behaviors, decisions, and performances.
- **Limits:** Limited range and possibility of resistance.
- **Interaction:** Abilities exploit emotions present in targets.

### 10. Randomness

**Example — Chaotic Magic**

- **Activation:** Discard a card to trigger an unpredictable effect.
- **Mechanic:** A die determines the nature or power of the effect.
- **Evolution:** Some results can be retained or combined.
- **Application:** Produce offensive, defensive, or utility effects.
- **Limits:** The player does not fully control the result.
- **Interaction:** Abilities allow influencing, combining, or exploiting random effects.

---

**Design Principle:** The Totem defines the character's central mechanic; its abilities represent different applications of it. Two characters can share the same archetype while having radically different playstyles.
