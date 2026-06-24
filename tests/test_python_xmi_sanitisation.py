import xml.etree.ElementTree as ET

from MisarParserPython import set_python_element_fields, to_xmi_safe_text


class FakeElement:
    pass


def test_xmi_safe_text_preserves_utf8_and_removes_forbidden_xml_characters():
    value = 'Ofgem & NCSC CAF 4.0 – “é” <tag> \x01\x08'
    cleaned = to_xmi_safe_text(value)

    assert 'Ofgem & NCSC CAF 4.0' in cleaned
    assert 'é' in cleaned
    assert '\x01' not in cleaned
    assert '\x08' not in cleaned

    element = ET.Element('test')
    element.set('value', cleaned)
    xml_text = ET.tostring(element, encoding='unicode')

    assert '&amp;' in xml_text
    assert '&lt;tag&gt;' in xml_text


def test_set_python_element_fields_sanitises_model_text_fields():
    element = FakeElement()

    set_python_element_fields(
        element,
        'ke-ingest',
        'src/قانون & caf.py',
        'handler <unsafe> \x02',
        'COMPILE',
        12,
    )

    assert element.ParentProjectName == 'ke-ingest'
    assert element.ArtifactFileName == 'src/قانون & caf.py'
    assert element.ElementIdentifier == 'handler <unsafe>'
    assert element.ElementProfile == 'COMPILE'
    assert element.LineNumber == 12
