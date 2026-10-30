"""Restore Anain's visible PDF illustrations, excluding obsolete overlapping artwork."""

import zipfile
from pathlib import Path

from apply_october_updates import rewrite
from cardenveil.serialization import character_from_archive

ROOT = Path(__file__).resolve().parents[1]
# Confirmed visually against page 2 of Toconvert/Fiche Anain Proviste.pdf.
ROWS = [
    ('Hache Virevoltante', 1), ('Spirit, HELP!', 3), ('Nain Sonore', 6),
    ('Nainbulance', 8), ('Naimpregnation', 9), ('Secousse Tellurique', 12),
    ('Justice de la Confrérie des Nains Puissants !', 13), ('Inainretable', 14),
]


def main():
    """Reassign existing compressed bytes using an original backup as a stable source."""
    archive = ROOT / 'Final/anain-proviste.zip'
    backup = ROOT / 'Final/Backups/anain-images-visible-pdf'
    original = backup / archive.name
    source = original if original.exists() else archive
    sheet = character_from_archive(archive)
    assert [a.name for a in sheet.capacities] == [name for name, _ in ROWS]
    with zipfile.ZipFile(source) as z:
        assets = {f'assets/anain-proviste/capacity-{i}.png':
                  z.read(f'assets/anain-proviste/capacity-{source_index}.png')
                  for i, (_, source_index) in enumerate(ROWS, 1)}
    rewrite(archive, backup, lambda sheet: None, assets=assets)
    with zipfile.ZipFile(archive) as z:
        assert all(z.read(name) == data for name, data in assets.items())
    print('Eight visible PDF illustrations assigned; original backed up:', original)


if __name__ == '__main__':
    main()
