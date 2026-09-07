from __future__ import annotations

import re

LANGUAGE_TAG_RE = re.compile(r"^[A-Za-z]{2,3}(?:-[A-Za-z0-9]{1,8})*$")

LANGUAGE_NAMES: dict[str, str] = {
    "en": "English",
    "pt": "Portuguese",
    "es": "Spanish",
    "fr": "French",
    "de": "German",
    "it": "Italian",
    "nl": "Dutch",
    "ru": "Russian",
    "uk": "Ukrainian",
    "pl": "Polish",
    "tr": "Turkish",
    "ar": "Arabic",
    "he": "Hebrew",
    "fa": "Persian",
    "hi": "Hindi",
    "bn": "Bengali",
    "zh": "Chinese",
    "ja": "Japanese",
    "ko": "Korean",
    "th": "Thai",
    "vi": "Vietnamese",
    "id": "Indonesian",
    "sv": "Swedish",
    "no": "Norwegian",
    "da": "Danish",
    "fi": "Finnish",
    "cs": "Czech",
    "el": "Greek",
    "ro": "Romanian",
    "hu": "Hungarian",
}

LANGUAGE_OVERRIDES: dict[str, str] = {
    "zh-Hans": "Simplified Chinese",
    "zh-Hant": "Traditional Chinese",
    "pt-BR": "Brazilian Portuguese",
    "pt-PT": "European Portuguese",
}

CASELESS_LANGUAGES: frozenset[str] = frozenset(
    {"zh", "ja", "ko", "ar", "he", "fa", "hi", "th", "bn"}
)


def resolve_language(value: str) -> str:
    """Normalize and validate a BCP-47-style language tag.

    Lowercases the primary subtag, uppercases 2-3 letter alphabetic subtags,
    and capitalizes 4-letter script subtags. Raises ``ValueError`` for empty
    or non-conforming tags.
    """
    tag = value.strip()
    if not LANGUAGE_TAG_RE.match(tag):
        raise ValueError(f"Invalid language tag: {value!r}")

    parts = tag.split("-")
    normalized = [parts[0].lower()]
    for subtag in parts[1:]:
        if len(subtag) == 4 and subtag.isalpha():
            normalized.append(subtag.capitalize())
        elif subtag.isalpha() and len(subtag) in (2, 3):
            normalized.append(subtag.upper())
        else:
            normalized.append(subtag.lower())
    return "-".join(normalized)


def language_display_name(tag: str) -> str:
    """Return an English display name for a language tag.

    Tries the full normalized tag (script/region variants) first, then the
    primary subtag, and falls back to the normalized tag itself for unknown
    languages.
    """
    normalized = resolve_language(tag)
    if normalized in LANGUAGE_OVERRIDES:
        return LANGUAGE_OVERRIDES[normalized]
    return LANGUAGE_NAMES.get(normalized.split("-")[0], normalized)


def has_case(tag: str) -> bool:
    """Whether the language's script distinguishes letter case."""
    return tag.split("-")[0].lower() not in CASELESS_LANGUAGES
