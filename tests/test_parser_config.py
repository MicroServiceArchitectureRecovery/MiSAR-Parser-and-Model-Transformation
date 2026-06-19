from MisarParserConfig import describe_psm_selection, resolve_psm_ecore_path


def test_resolve_psm_ecore_path_accepts_selected_path(tmp_path):
    psm = tmp_path / 'PSM.ecore'
    psm.write_text('<ecore:EPackage />', encoding='utf-8')

    resolved = resolve_psm_ecore_path(psm)

    assert resolved == str(psm)


def test_describe_psm_selection_reports_existing_file(tmp_path):
    psm = tmp_path / 'PSM.ecore'
    psm.write_text('<ecore:EPackage />', encoding='utf-8')

    description = describe_psm_selection(psm)

    assert description['psm_path'] == str(psm)
    assert description['psm_exists'] == 'True'
