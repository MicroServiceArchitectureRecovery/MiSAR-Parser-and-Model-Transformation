from conftest import TRANSFORMATION_TRANSFORMS_DIR


def test_qvto_transformation_file_exists_and_is_not_empty():
    transform = TRANSFORMATION_TRANSFORMS_DIR / 'MisarTransformationEngine.qvto'

    assert transform.is_file()
    assert transform.stat().st_size > 0


def test_qvto_transformation_mentions_psm_and_pim_modeltypes():
    transform = TRANSFORMATION_TRANSFORMS_DIR / 'MisarTransformationEngine.qvto'
    content = transform.read_text(encoding='utf-8', errors='ignore')

    assert 'modeltype' in content
    assert 'PSM' in content
    assert 'PIM' in content
