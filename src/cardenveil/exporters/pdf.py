"""Deterministic two-page A4 PDF export for canonical Cardenveil archives."""

from __future__ import annotations

import base64
import binascii
import html
import io
import re
import unicodedata
import zipfile
from dataclasses import fields
from pathlib import Path

from cardenveil.domain import Character
from cardenveil.errors import SerializationError
from cardenveil.serialization import character_from_archive

PAGE_WIDTH = 595.276
PAGE_HEIGHT = 841.89
MARGIN = 24.0
GAP = 10.0
INK = (0.10, 0.12, 0.15)
MUTED = (0.38, 0.40, 0.44)
LINE = (0.76, 0.78, 0.81)
ACCENT = (0.55, 0.36, 0.10)
PALE = (0.96, 0.96, 0.95)
SUIT_COLORS = {
    "heart": (0.72, 0.16, 0.18),
    "diamond": (0.72, 0.16, 0.18),
    "club": (0.12, 0.18, 0.16),
    "spade": (0.12, 0.18, 0.16),
}
SUIT_SYMBOLS = {
    "heart": "Cœur",
    "diamond": "Carreau",
    "club": "Trèfle",
    "spade": "Pique",
}


def character_archive_to_pdf(archive_path: str | Path, output_path: str | Path) -> Path:
    """Render one ZIP archive as exactly two white A4 pages and validate the result."""

    pymupdf = _load_pymupdf()
    source = Path(archive_path)
    destination = Path(output_path)
    character = character_from_archive(source)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    try:
        with zipfile.ZipFile(source) as archive:
            document = pymupdf.open()
            document.new_page(width=PAGE_WIDTH, height=PAGE_HEIGHT)
            document.new_page(width=PAGE_WIDTH, height=PAGE_HEIGHT)
            first_page = document[0]
            second_page = document[1]
            _register_fonts(first_page)
            _register_fonts(second_page)
            _render_overview(first_page, archive, character)
            _render_capacities(second_page, archive, character)
            document.set_metadata({})
            document.save(temporary, garbage=4, deflate=True, clean=True)
            document.close()
        with pymupdf.open(temporary) as check:
            if len(check) != 2:
                raise SerializationError("Character PDF export must contain exactly two pages")
            if any(
                abs(page.rect.width - PAGE_WIDTH) > 0.1
                or abs(page.rect.height - PAGE_HEIGHT) > 0.1
                for page in check
            ):
                raise SerializationError("Character PDF export is not A4 portrait")
        temporary.replace(destination)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
    return destination


def _render_overview(page: object, archive: zipfile.ZipFile, character: Character) -> None:
    """Render identity, statistics, combat data, narrative, equipment, and other sheet fields."""

    portrait_rect = _rect(24, 24, 82, 96)
    _draw_image(page, archive, character.portrait, portrait_rect)
    _stroke_rect(page, portrait_rect)
    _text(page, 118, 34, character.identity.nom or character.id, 20, bold=True, color=INK)
    identity_lines = [
        _join_values(character.identity.race, character.identity.alignement),
        _join_values(
            f"Niveau {character.identity.niveau}" if character.identity.niveau != "" else "",
            f"Joueur : {character.identity.joueur}" if character.identity.joueur else "",
        ),
        _join_values(
            f"Âge {character.identity.age}" if character.identity.age else "",
            character.identity.taille,
            character.identity.poids,
        ),
        _join_values(character.identity.yeux, character.identity.peau, character.identity.cheveux),
    ]
    _paragraph(page, 118, 61, 447, "\n".join(line for line in identity_lines if line), 7.2)

    stat_y = 130.0
    stat_width = (PAGE_WIDTH - 2 * MARGIN - 3 * 8) / 4
    for index, (label, value) in enumerate(
        (
            ("FORCE", character.stats.force),
            ("AGILITÉ", character.stats.agilite),
            ("ESPRIT", character.stats.esprit),
            ("SOCIAL", character.stats.social),
        )
    ):
        x = MARGIN + index * (stat_width + 8)
        _fill_rect(page, _rect(x, stat_y, stat_width, 42), PALE)
        _stroke_rect(page, _rect(x, stat_y, stat_width, 42))
        _text(page, x + 7, stat_y + 12, label, 6.5, bold=True, color=MUTED)
        _text(page, x + stat_width - 30, stat_y + 10, str(value), 18, bold=True, color=INK)

    blocks = _overview_blocks(character)
    top = 184.0
    bottom = PAGE_HEIGHT - 34.0
    column_width = (PAGE_WIDTH - 2 * MARGIN - GAP) / 2
    font_size, placements = _fit_blocks(blocks, column_width, bottom - top)
    columns_y = [top, top]
    for block, column in placements:
        x = MARGIN + column * (column_width + GAP)
        height = _block_height(block[1], column_width, font_size, block[2])
        _draw_block(
            page,
            archive,
            x,
            columns_y[column],
            column_width,
            height,
            block[0],
            block[1],
            font_size,
            block[2],
        )
        columns_y[column] += height + 6
    _footer(page, character.identity.nom, 1)


def _render_capacities(page: object, archive: zipfile.ZipFile, character: Character) -> None:
    """Render every complete capacity and remaining mechanics on the second A4 page."""

    _text(page, MARGIN, 30, f"Capacités — {character.identity.nom}", 16, bold=True, color=INK)
    _text(
        page,
        PAGE_WIDTH - 145,
        34,
        f"{len(character.capacities)} capacité(s)",
        7,
        color=MUTED,
    )
    top = 55.0
    bottom = PAGE_HEIGHT - 34.0
    column_width = (PAGE_WIDTH - 2 * MARGIN - GAP) / 2
    cards = [_capacity_card(capacity) for capacity in character.capacities]
    if not cards:
        cards = [("Aucune capacité", "Aucune capacité renseignée sur cette fiche.", "")]
    font_size, placements = _fit_blocks(cards, column_width, bottom - top, minimum=3.8)
    columns_y = [top, top]
    for index, (card, column) in enumerate(placements):
        x = MARGIN + column * (column_width + GAP)
        image = character.capacities[index].image if index < len(character.capacities) else ""
        height = _block_height(card[1], column_width, font_size, image)
        _draw_capacity_card(
            page,
            archive,
            x,
            columns_y[column],
            column_width,
            height,
            card[0],
            card[1],
            font_size,
            image,
            card[2],
        )
        columns_y[column] += height + 6
    _footer(page, character.identity.nom, 2)


def _overview_blocks(character: Character) -> list[tuple[str, str, str]]:
    """Convert all meaningful non-capacity fields into printable overview blocks."""

    blocks: list[tuple[str, str, str]] = []
    combat = _lines(
        ("PV max", character.derived.pvMax),
        ("PV actuels", character.derived.pvActuels),
        ("PV temporaires", character.derived.pvTemporaires),
        ("Mouvement", character.derived.mouvement),
        ("Initiative", character.derived.initiative),
        ("Parade", character.defense.parade),
        ("Armure", character.defense.armure),
        ("Déflexion", character.defense.deflexion),
        ("Volonté", character.derived.volonte),
        ("Perception passive", character.derived.perceptionPassive),
        ("Seuil sauvegarde", character.derived.seuilSauvegarde),
        ("Fatigue", character.derived.fatigue),
        ("Mort", character.derived.mort),
        ("Bonus PV", character.derived.bonusPv),
        ("Seuil de miss", character.derived.seuilMiss),
        ("Canalisation", character.derived.canalisation),
        ("Bonus d'attaque", character.derived.bonusAttaque),
        ("Inspiration", character.derived.inspiration),
        ("Bonus d'initiative", character.derived.initiativeBonus),
        ("Bonus de mouvement", character.derived.mouvementBonus),
        ("Bonus de garde", character.defense.gardeBonus),
        ("Bonus de défense", character.defense.bonus),
        ("XP dépensés", character.progression.xpDepenses),
        ("XP disponibles", character.progression.xpDisponibles),
        ("Or", character.resources.gold),
        ("Rations", character.resources.rations),
        ("Tokens de Force", character.resources.tokens.force),
        ("Tokens d'Agilité", character.resources.tokens.agilite),
        ("Tokens d'Esprit", character.resources.tokens.esprit),
        ("Tokens de Social", character.resources.tokens.social),
    )
    if combat:
        blocks.append(("Combat et ressources", combat, ""))

    skill_lines = []
    for item in fields(character.skills):
        skill = getattr(character.skills, item.name)
        if skill is None:
            continue
        marker = "[x]" if skill.trained else "[ ]"
        bonus = f"  +{skill.bonus}" if skill.bonus not in (0, "", None) else ""
        skill_lines.append(f"{marker} {item.name.replace('_', ' ').title()}{bonus}")
    blocks.append(("Compétences", "\n".join(skill_lines), ""))

    weapons = "\n".join(
        _join_values(
            weapon.nom,
            f"Dé {weapon.de}" if _present(weapon.de) else "",
            f"Force/Agi. {weapon.forceAgi}" if _present(weapon.forceAgi) else "",
            f"Crit. {weapon.critique}" if _present(weapon.critique) else "",
            f"Avantage {weapon.avantage}" if _present(weapon.avantage) else "",
            f"Bonus {weapon.bonus}" if _present(weapon.bonus) else "",
            f"Perfection {weapon.perfection}" if _present(weapon.perfection) else "",
            weapon.notes,
        )
        for weapon in character.weapons
        if any(_present(getattr(weapon, item.name)) for item in fields(weapon))
    )
    if weapons:
        blocks.append(("Armes", weapons, ""))

    equipment_lines = []
    for item in fields(character.equipment):
        piece = getattr(character.equipment, item.name)
        values = [
            f"{field.name} : {getattr(piece, field.name)}"
            for field in fields(piece)
            if _present(getattr(piece, field.name))
        ]
        if values:
            equipment_lines.append(f"{item.name.title()} — {' · '.join(values)}")
    if equipment_lines:
        blocks.append(("Équipement", "\n".join(equipment_lines), ""))

    if character.totem.nom or character.totem.description or character.totem.image:
        blocks.append(
            (
                f"Totem — {character.totem.nom}" if character.totem.nom else "Totem",
                _plain(character.totem.description),
                character.totem.image,
            )
        )

    narrative_labels = {
        "background": "Background",
        "objectif": "Objectif",
        "liens": "Liens",
        "traitsSpeciaux": "Traits spéciaux",
        "personnalite": "Personnalité",
        "reputation": "Réputation",
        "education": "Éducation",
        "croyances": "Croyances",
        "cicatrices": "Cicatrices",
        "pulsion": "Pulsion",
        "maniesEtTics": "Manies et tics",
        "instinct": "Instinct",
    }
    for key, label in narrative_labels.items():
        value = getattr(character.narrative, key)
        if isinstance(value, list):
            value = "\n".join(f"• {_plain(item)}" for item in value if _present(item))
        else:
            value = _plain(value)
        if value:
            blocks.append((label, value, ""))

    other = _other_mechanics(character)
    if other:
        blocks.append(("Autres informations", other, ""))
    if character.statBonuses is not None:
        bonuses = _lines(
            ("Force", character.statBonuses.force),
            ("Agilité", character.statBonuses.agilite),
            ("Esprit", character.statBonuses.esprit),
            ("Social", character.statBonuses.social),
        )
        if bonuses:
            blocks.append(("Bonus de caractéristiques", bonuses, ""))
    return blocks


def _other_mechanics(character: Character) -> str:
    """Collect masteries, feats, inventory, controls, notes, actions, and reactions."""

    lines: list[str] = []
    lines.extend(
        f"Maîtrise d'arme : {item.family} {item.perfection}"
        for item in character.weaponMasteries
    )
    lines.extend(
        f"Maîtrise élémentaire : {item.element} {item.level}"
        for item in character.elementalMasteries
    )
    lines.extend(
        _join_values(f"Feat : {item.title}" if item.title else "Feat", _plain(item.description))
        for item in character.feats
    )
    controls = character.abilityControls
    control_values = _lines(
        ("Carte minimale", controls.cardMin),
        ("Carte maximale", controls.cardMax),
        ("Capacités connues", controls.knownAbilities),
        ("Capacités préparées max", controls.maxPreparedAbilities),
        ("Réduction pique", controls.colorReductions.spade),
        ("Réduction cœur", controls.colorReductions.heart),
        ("Réduction carreau", controls.colorReductions.diamond),
        ("Réduction trèfle", controls.colorReductions.club),
    )
    if control_values:
        lines.append("Contrôles de capacités :\n" + control_values)
    for item in character.inventoryItems:
        values = [
            f"{field.name} : {_plain(getattr(item, field.name))}"
            for field in fields(item)
            if field.name != "equipmentData" and _present(getattr(item, field.name))
        ]
        equipment_values = [
            f"{field.name} : {_plain(getattr(item.equipmentData, field.name))}"
            for field in fields(item.equipmentData)
            if _present(getattr(item.equipmentData, field.name))
        ]
        values.extend(equipment_values)
        if values:
            lines.append("Objet : " + " · ".join(values))
    for label, value in (
        ("Équipement libre", character.inventory.equipement),
        ("Inventaire", character.inventory.inventaire),
        ("Totem libre", character.inventory.totem),
        ("Cartes et tokens", character.resources.cartesEtTokens),
        ("Notes", character.notes),
    ):
        if _present(value):
            lines.append(f"{label} : {_plain(value)}")
    if character.actions:
        lines.append(f"Actions : {_plain(character.actions)}")
    if character.reactions:
        lines.append(f"Réactions : {_plain(character.reactions)}")
    if character.tokens:
        lines.append(f"Tokens : {_plain(character.tokens)}")
    return "\n".join(line for line in lines if line)


def _capacity_card(capacity: object) -> tuple[str, str, str]:
    """Convert one capacity into a title, full printable body, and suit marker."""

    suit = SUIT_SYMBOLS.get(capacity.cost.color, "")  # type: ignore[attr-defined]
    cost = capacity.cost.total  # type: ignore[attr-defined]
    title = _join_values(capacity.name, f"{suit} {cost}" if suit or cost else "")  # type: ignore[attr-defined]
    lines = []
    if _present(capacity.description):  # type: ignore[attr-defined]
        lines.append(_plain(capacity.description))  # type: ignore[attr-defined]
    values = _join_values(capacity.value.main, capacity.value.bonus)  # type: ignore[attr-defined]
    if values:
        lines.append(f"Valeur : {values}")
    cost_values = [
        f"base {capacity.cost.base}",  # type: ignore[attr-defined]
        f"incantation -{capacity.cost.incantationReduction}",  # type: ignore[attr-defined]
        f"couleur -{capacity.cost.colorReduction}",  # type: ignore[attr-defined]
        f"éveil -{capacity.cost.awakeningReduction}",  # type: ignore[attr-defined]
        f"maîtrise -{capacity.cost.weaponMasteryReduction}",  # type: ignore[attr-defined]
        f"total {capacity.cost.total}",  # type: ignore[attr-defined]
    ]
    lines.append("Coût : " + " · ".join(cost_values))
    for label, value in (
        ("Incantation", capacity.incantation),  # type: ignore[attr-defined]
        ("Sauvegarde", capacity.save),  # type: ignore[attr-defined]
        ("Utilisation", capacity.usage),  # type: ignore[attr-defined]
    ):
        if _present(value):
            lines.append(f"{label} : {_plain(value)}")
    return title or "Capacité", "\n".join(lines), capacity.cost.color  # type: ignore[attr-defined]


def _fit_blocks(
    blocks: list[tuple[str, str, str]],
    width: float,
    available_height: float,
    *,
    minimum: float = 4.2,
) -> tuple[float, list[tuple[tuple[str, str, str], int]]]:
    """Choose the largest readable font and greedily balance blocks across two columns."""

    size = 7.2
    while size >= minimum:
        placements: list[tuple[tuple[str, str, str], int]] = []
        heights = [0.0, 0.0]
        for block in blocks:
            column = 0 if heights[0] <= heights[1] else 1
            height = _block_height(block[1], width, size, block[2]) + 6
            heights[column] += height
            placements.append((block, column))
        if max(heights) <= available_height:
            return size, placements
        size -= 0.2
    raise SerializationError(
        f"Character content cannot fit on the requested two-page PDF at {minimum} pt"
    )


def _block_height(text: str, width: float, size: float, image: str = "") -> float:
    """Estimate a bordered block height using the same wrapping rules used for drawing."""

    text_width = width - 16 - (48 if image else 0)
    lines = _wrap(_plain(text), text_width, size)
    text_height = len(lines) * size * 1.24
    return max(28 + text_height, 62 if image else 0)


def _draw_block(
    page: object,
    archive: zipfile.ZipFile,
    x: float,
    y: float,
    width: float,
    height: float,
    title: str,
    body: str,
    size: float,
    image: str,
) -> None:
    """Draw one bordered overview section with an optional thumbnail."""

    rectangle = _rect(x, y, width, height)
    _stroke_rect(page, rectangle)
    _fill_rect(page, _rect(x, y, width, 20), PALE)
    _text(page, x + 7, y + 7, title, size + 0.8, bold=True, color=INK)
    offset = 0.0
    if image:
        image_rect = _rect(x + 7, y + 25, 42, 42)
        _draw_image(page, archive, image, image_rect)
        offset = 48.0
    _paragraph(page, x + 7 + offset, y + 25, width - 14 - offset, body, size)


def _draw_capacity_card(
    page: object,
    archive: zipfile.ZipFile,
    x: float,
    y: float,
    width: float,
    height: float,
    title: str,
    body: str,
    size: float,
    image: str,
    suit: str,
) -> None:
    """Draw one complete capacity card using a subtle suit-colored title rule."""

    color = SUIT_COLORS.get(suit, ACCENT)
    _stroke_rect(page, _rect(x, y, width, height), color=color)
    _fill_rect(page, _rect(x, y, width, 20), PALE)
    _text(page, x + 7, y + 7, title, size + 0.9, bold=True, color=color)
    offset = 0.0
    if image:
        image_rect = _rect(x + 7, y + 25, 42, 42)
        _draw_image(page, archive, image, image_rect)
        offset = 48.0
    _paragraph(page, x + 7 + offset, y + 25, width - 14 - offset, body, size)


def _paragraph(
    page: object,
    x: float,
    y: float,
    width: float,
    value: str,
    size: float,
) -> float:
    """Draw wrapped plain text and return the y position immediately after its final line."""

    cursor = y
    for line in _wrap(_plain(value), width, size):
        _text(page, x, cursor, line, size, color=INK)
        cursor += size * 1.24
    return cursor


def _wrap(value: str, width: float, size: float) -> list[str]:
    """Wrap paragraphs with a deterministic width approximation suitable for Arial."""

    if not value:
        return []
    maximum = max(8, int(width / (size * 0.52)))
    output: list[str] = []
    for paragraph in value.splitlines() or [""]:
        words = paragraph.split()
        if not words:
            output.append("")
            continue
        line = words[0]
        for word in words[1:]:
            candidate = f"{line} {word}"
            if len(candidate) <= maximum:
                line = candidate
            else:
                output.append(line)
                line = word
        output.append(line)
    return output


def _text(
    page: object,
    x: float,
    y: float,
    value: object,
    size: float,
    *,
    bold: bool = False,
    color: tuple[float, float, float] = INK,
) -> None:
    """Insert one line with the embedded regular or bold Arial font."""

    page.insert_text(  # type: ignore[attr-defined]
        (x, y + size),
        _printable_pdf_text(value),
        fontsize=size,
        fontname="hebo" if bold else "helv",
        color=color,
        overlay=True,
    )


def _footer(page: object, character_name: str, number: int) -> None:
    """Draw a small print-safe footer containing only sheet identity and pagination."""

    _text(page, MARGIN, PAGE_HEIGHT - 22, character_name, 5.5, color=MUTED)
    _text(page, PAGE_WIDTH - 76, PAGE_HEIGHT - 22, f"Page {number} / 2", 5.5, color=MUTED)


def _draw_image(page: object, archive: zipfile.ZipFile, reference: str, rectangle: object) -> None:
    """Insert one referenced archive image, or leave a neutral white placeholder when absent."""

    payload = _archive_image(archive, reference)
    if payload is not None:
        payload = _print_image(payload, rectangle)
        page.insert_image(  # type: ignore[attr-defined]
            rectangle,
            stream=payload,
            keep_proportion=True,
            overlay=True,
        )


def _archive_image(archive: zipfile.ZipFile, reference: str) -> bytes | None:
    """Read an image reference case-insensitively from its source archive."""

    if reference.startswith("data:"):
        header, separator, payload = reference.partition(",")
        if not separator or ";base64" not in header:
            return None
        try:
            return base64.b64decode(payload, validate=True)
        except (ValueError, binascii.Error):
            return None
    if not reference or not reference.startswith("/assets/"):
        return None
    names = {name.casefold(): name for name in archive.namelist()}
    actual = names.get(reference.lstrip("/").casefold())
    return archive.read(actual) if actual is not None else None


def _print_image(payload: bytes, rectangle: object) -> bytes:
    """Downsample one source image to its printed dimensions and flatten it onto white."""

    try:
        from PIL import Image
    except ImportError as error:  # pragma: no cover - installed with the PDF export extra
        raise RuntimeError(
            "Install cardenveil-core[pdf-assets] to compress printable character images"
        ) from error
    width = max(1, round(rectangle.width * 4))  # type: ignore[attr-defined]
    height = max(1, round(rectangle.height * 4))  # type: ignore[attr-defined]
    with Image.open(io.BytesIO(payload)) as source:
        source.thumbnail((width, height), Image.Resampling.LANCZOS)
        converted = source.convert("RGBA")
        flattened = Image.new("RGB", converted.size, "white")
        flattened.paste(converted, mask=converted.getchannel("A"))
        output = io.BytesIO()
        flattened.save(output, format="JPEG", quality=78, optimize=True, progressive=True)
        return output.getvalue()


def _register_fonts(page: object) -> None:
    """Register portable PDF Base-14 fonts without depending on host system files."""

    page.insert_font(fontname="helv")  # type: ignore[attr-defined]
    page.insert_font(fontname="hebo")  # type: ignore[attr-defined]


def _plain(value: object) -> str:
    """Convert stored HTML and arbitrary scalars into compact, printable plain text."""

    if value is None:
        return ""
    if isinstance(value, list):
        return " · ".join(_plain(item) for item in value if _present(item))
    text = html.unescape(str(value))
    text = re.sub(r"<\s*br\s*/?\s*>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</\s*(p|div|li)\s*>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    return "\n".join(" ".join(line.split()) for line in text.splitlines() if line.strip())


def _printable_pdf_text(value: object) -> str:
    """Normalize typography unsupported by portable PDF Base-14 fonts without changing data."""

    text = str(value).translate(
        str.maketrans(
            {
                "’": "'",
                "‘": "'",
                "“": '"',
                "”": '"',
                "–": "-",
                "—": "-",
                "−": "-",
                "Œ": "OE",
                "œ": "oe",
                "•": "-",
                "\N{NO-BREAK SPACE}": " ",
            }
        )
    )
    return "".join(character for character in text if not unicodedata.combining(character))


def _lines(*items: tuple[str, object]) -> str:
    """Format non-empty label-value pairs on separate lines."""

    return "\n".join(f"{label} : {_plain(value)}" for label, value in items if _present(value))


def _join_values(*values: object) -> str:
    """Join non-empty compact values with a centered printable separator."""

    return " · ".join(_plain(value) for value in values if _present(value))


def _present(value: object) -> bool:
    """Return whether a value contains printable information, while preserving numeric zero."""

    return value is not None and value != "" and value != []


def _rect(x: float, y: float, width: float, height: float) -> object:
    """Create a PyMuPDF rectangle without importing the optional dependency at module import."""

    return _load_pymupdf().Rect(x, y, x + width, y + height)


def _stroke_rect(
    page: object,
    rectangle: object,
    *,
    color: tuple[float, float, float] = LINE,
) -> None:
    """Draw a thin rectangular print boundary."""

    page.draw_rect(rectangle, color=color, width=0.55, overlay=True)  # type: ignore[attr-defined]


def _fill_rect(page: object, rectangle: object, color: tuple[float, float, float]) -> None:
    """Draw a pale solid rectangle while keeping the page background white."""

    page.draw_rect(rectangle, color=color, fill=color, width=0, overlay=True)  # type: ignore[attr-defined]


def _load_pymupdf() -> object:
    """Load the optional PDF engine lazily with a clear installation error."""

    try:
        import pymupdf
    except ImportError as error:  # pragma: no cover - depends on optional environment
        raise RuntimeError(
            "Install cardenveil-core[pdf-assets] to export printable character PDFs"
        ) from error
    return pymupdf
