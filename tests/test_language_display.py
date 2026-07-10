from pathlib import Path

from MisarParserLanguage import (
    LanguageScope,
    format_language_summary,
    format_module_display_path,
    strip_language_badge,
)


def test_empty_language_summary_does_not_emit_unknown_label():
    assert format_language_summary([]) == ''


def test_format_module_display_path_does_not_emit_unknown_badge(tmp_path):
    module_dir = tmp_path / 'n8n-sharp'
    module_dir.mkdir()

    display_path = format_module_display_path(module_dir)

    assert display_path == str(module_dir)
    assert '[Unknown' not in display_path
    assert '[unknown' not in display_path


def test_old_unknown_badge_is_stripped_from_saved_paths():
    value = '/tmp/n8n-sharp [Unknown: Node.js]'
    assert strip_language_badge(value) == '/tmp/n8n-sharp'


def test_generic_language_is_not_displayed_as_unknown():
    summary = format_language_summary([LanguageScope(language='generic', framework='GENERIC')])
    assert summary == ''
