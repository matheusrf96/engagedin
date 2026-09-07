from __future__ import annotations

import pytest

from engagedin.core.languages import (
    has_case,
    language_display_name,
    resolve_language,
)


def test_resolve_language_simple_tag() -> None:
    assert resolve_language("en") == "en"


def test_resolve_language_trims_whitespace() -> None:
    assert resolve_language("  ru  ") == "ru"


def test_resolve_language_normalizes_primary_case() -> None:
    assert resolve_language("EN") == "en"
    assert resolve_language("Ru") == "ru"


def test_resolve_language_normalizes_region_subtag() -> None:
    assert resolve_language("PT-br") == "pt-BR"
    assert resolve_language("en-gb") == "en-GB"


def test_resolve_language_normalizes_script_subtag() -> None:
    assert resolve_language("zh-hans") == "zh-Hans"
    assert resolve_language("ZH-HANT") == "zh-Hant"


def test_resolve_language_three_letter_primary() -> None:
    assert resolve_language("fra") == "fra"


def test_resolve_language_preserves_private_subtags() -> None:
    assert resolve_language("en-x-custom") == "en-x-custom"


def test_resolve_language_empty_raises() -> None:
    with pytest.raises(ValueError, match="Invalid language tag"):
        resolve_language("")


def test_resolve_language_whitespace_only_raises() -> None:
    with pytest.raises(ValueError, match="Invalid language tag"):
        resolve_language("   ")


def test_resolve_language_invalid_characters_raise() -> None:
    with pytest.raises(ValueError, match="Invalid language tag"):
        resolve_language("not a tag!")


def test_resolve_language_too_short_primary_raises() -> None:
    with pytest.raises(ValueError, match="Invalid language tag"):
        resolve_language("e")


def test_resolve_language_numeric_primary_raises() -> None:
    with pytest.raises(ValueError, match="Invalid language tag"):
        resolve_language("123")


def test_language_display_name_known_primary() -> None:
    assert language_display_name("en") == "English"
    assert language_display_name("ru") == "Russian"
    assert language_display_name("ar") == "Arabic"
    assert language_display_name("zh") == "Chinese"


def test_language_display_name_full_tag_override() -> None:
    assert language_display_name("pt-BR") == "Brazilian Portuguese"
    assert language_display_name("pt-PT") == "European Portuguese"
    assert language_display_name("zh-Hans") == "Simplified Chinese"
    assert language_display_name("zh-Hant") == "Traditional Chinese"


def test_language_display_name_unknown_tag_falls_back_to_tag() -> None:
    assert language_display_name("zz") == "zz"
    assert language_display_name("xx-Yyyy") == "xx-Yyyy"


def test_language_display_name_resolves_before_lookup() -> None:
    assert language_display_name("pt-br") == "Brazilian Portuguese"


def test_has_case_caseless_scripts() -> None:
    for tag in ("zh", "zh-Hans", "ja", "ko", "ar", "he", "fa", "hi", "th", "bn"):
        assert has_case(tag) is False, tag


def test_has_case_case_bearing_scripts() -> None:
    for tag in ("en", "ru", "pt-BR", "de", "tr", "uk", "el"):
        assert has_case(tag) is True, tag


def test_has_case_decides_on_primary_subtag() -> None:
    assert has_case("zh-Hant") is False
    assert has_case("AR-EG") is False
    assert has_case("en-GB") is True
