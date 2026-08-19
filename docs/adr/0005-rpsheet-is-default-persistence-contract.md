# ADR 0005 — rpsheet comme contrat persistant par défaut

## Contexte

Six archives de référence contiennent le format réellement échangé par les applications
Cardenveil. La première maquette du core utilisait une enveloppe différente et perdait de nombreux
champs.

## Décision

`Character` et ses sous-objets correspondent désormais 1:1 au JSON `*.rpsheet.json`. Le
sérialiseur préserve les types, chaînes HTML, valeurs vides et valeurs dérivées persistées. Une clé
inconnue provoque une erreur au lieu d'être ignorée. Cette décision remplace le schéma expérimental
`schema_version/character` de la première maquette.

## Conséquences

Les six archives effectuent un roundtrip exact. Le modèle assume explicitement le contrat de
persistance demandé; les définitions de contenu et règles naturelles restent dans leurs couches
séparées.

