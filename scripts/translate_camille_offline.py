"""Install Camille’s manually reviewed English prose offline, preserving all numerical mechanics."""
import hashlib
import json
from pathlib import Path
import re
from translate_site import strings

ROOT = Path(__file__).resolve().parents[1]
ENGLISH = [
    '0.5 × Spirit Mod d6',
    '0.5 × the deflected attack’s damage',
    '1 double (2 in crow form), 3 rounds maximum',
    '1 × base damage + 3 × base damage',
    '2.5 × base damage',
    'A Murder of Crows',
    'Athletics (no effect on a successful save)',
    'Attack a creature, then leap 7 m backward. On the next round, use your Reaction to leap at that same creature and deliver a second devastating attack.\n\nFirst attack: 1 × base damage. Second attack: 3 × base damage.\n\nCrow Form: The retreat distance increases to 10.5 m.\nThe target must be within 20 m to be targeted, and you cannot do anything before the Reaction.',
    'Blindness',
    'Blackout',
    'Bonus Action / Reaction (crow form only)',
    'Camille',
    'Camille is a 37-year-old half-elf who can transform into a flock of crows through her A Murder of Crows totem.',
    'Flexible Channeling: You freely choose your channeling suit, regardless of the weapon used.',
    'Free Channeling: When you use a weapon (attack, parry, etc.), you automatically channel for 1 round, with a value equal to the weapon’s Parry.',
    'Defensive Focus: You can use a Focus to parry, using its channeling value instead of a weapon’s Parry.',
    'This agile character uses mobility, teleportation and crowd control through blindness and levitation to dominate the battlefield.',
    'Concentrate so your birds blind all enemy creatures entering or remaining within your Zone of Control.\n\nThe effect moves with you: enemies crossing your Zone of Control are also affected.\n\nWhen you attack a creature in your Zone of Control, blindness applies before the attack is resolved.\n\nEach creature can make only one saving throw per round against this effect.\n\nCrow Form: The range is multiplied by 1.5.',
    'Crimson Talons',
    'Death Omen',
    'As a Reaction to an attack within your Zone of Control, you can deflect it according to its type. The deflected attack’s damage is always halved.\n\nPhysical projectile: Redirect the projectile toward another creature within range if possible.\n\nMelee attack: Redirect the attack toward another creature within your Zone of Control.\n\nArea attack (AOE): Choose a new impact point for the attack within 3 m of you. Damage is halved.\n\nCrow Form: The range becomes 5 m instead of your usual Zone of Control.',
    'Enchant your weapons for 3 rounds. Each successful attack deals an additional 0.5 × Spirit Mod d6 damage.',
    'Send your crows at a creature 20 m away to lift it into the air (3 m high). The target levitates for 1 round.\n\nCrow Form: While your totem is active, you can use this ability as an AOE, affecting all enemy creatures within a 5 m radius of you.',
    'Featherstep',
    'Rush 10 m in a straight line, dealing 2.5 × base damage to every creature you pass through.\n\nCrow Form: The distance increases to 15 m.',
    'Summon a double of yourself that reproduces your appearance. It persists until destroyed, for a maximum of 3 rounds.\n\nThe double disappears immediately when attacked. When a creature attacks your double in melee, you can make an opportunity attack against it with advantage.\n\nCrow Form: You can place your double anywhere within a 5 m radius of you and summon a second double.',
    'Levitation for 1 round',
    'Mark a creature. You immediately analyze the target without a roll and learn its HP threshold. You have advantage on attacks against this target.\n\nIf the target dies, you immediately gain a free Action.\n\nOn subsequent rounds, you can use your Bonus Action to spread the mark to all creatures on a line between you and the original marked target. Each newly marked creature is analyzed for free.',
    'Murderous Waltz',
    'Long Black',
    "Raven's Grasp",
    "Raven's Passage",
    'Resilience (no effect on a successful save)',
    'Shadow Echoes',
    'Transformation: Lock a card to transform into a flock of crows. In this form, you can float, your movement is multiplied by 1.5 and the range of your melee abilities is multiplied by 1.5. If you are outside an enemy creature’s field of vision, you are automatically considered hidden.\n\nDodge: In crow form, you can discard a card and use your Reaction along with your next Action to dodge a targeted attack or halve the damage of an area attack (AOE).',
    'Twisted Fate',
    '18 m teleportation',
    'Use your Bonus Action to teleport to a location of your choice up to 18 m away.\n\nCrow Form: You can also use this ability as a Reaction to dodge a targeted attack. In this case, you teleport to a random location within an 18 m radius.',
    'Mixed Scholarship: +1 proficient skill.',
]


def main():
    """Apply reviewed translations only when the exact expected missing entries are present."""
    directory = ROOT / 'web/i18n'
    data = json.loads((ROOT / 'web/public/data/characters.json').read_text(encoding='utf-8'))
    character = next(c for c in data if c['id'] == 'camille')
    path = directory / 'characters.en.json'
    translations = json.loads(path.read_text(encoding='utf-8'))
    missing = sorted(set(strings(character)) - translations.keys())
    if missing:
        assert len(missing) == len(ENGLISH) == 39
        assert missing[0] == '0,5 × Mod Esprit d6' and missing[-1] == 'Érudition mixte : +1 compétence maîtrisée.'
        for before, after in zip(missing, ENGLISH, strict=True):
            numbers = lambda s: sorted(re.findall(r'\d+(?:[.,]\d+)?', s.replace(',', '.')))
            assert numbers(before) == numbers(after), before
            translations[before] = after
        path.write_text(json.dumps(translations, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    hashes_path = directory / 'characters.sources.json'
    hashes = json.loads(hashes_path.read_text(encoding='utf-8'))
    hashes['camille'] = hashlib.sha256(json.dumps(character, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
    hashes_path.write_text(json.dumps(hashes, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('Camille: English translation ready; all numerical values preserved.')


if __name__ == '__main__':
    main()
