import json

from cardenveil import Character
from cardenveil.domain import SheetIdentity, SheetStats
from cardenveil.serialization import character_from_json, character_to_json

mimyr = Character(
    id="mimyr",
    identity=SheetIdentity(nom="Mimyr", alignement="Chaotique Bon", race="Aasimar"),
    stats=SheetStats(force=16, agilite=8, esprit=16, social=6),
)

payload = character_to_json(mimyr)
print(payload)
with open("data.json", "w", encoding="utf-8") as file:
    json.dump(json.loads(payload), file, ensure_ascii=False, indent=4)

restored = character_from_json(payload)

assert restored == mimyr
