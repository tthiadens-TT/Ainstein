"""_apply_basic_formatting() moet Minkowski-merkkleur en -fonts toepassen op elk
Google Doc dat Ainstein aanmaakt — vóór deze fix kregen documenten alleen Google's
generieke kopstijlen, geen merkidentiteit. Getest via een fake Docs-service die de
batchUpdate-payload onderschept, geen echte API-call."""
import gdoc_tools


class _FakeDocuments:
    def __init__(self, doc_body):
        self._doc_body = doc_body
        self.batch_requests = None

    def get(self, documentId):
        return self

    def execute(self):
        return {"body": {"content": self._doc_body}}

    def batchUpdate(self, documentId, body):
        self.batch_requests = body["requests"]
        return self

    # execute() is reused for both get() and batchUpdate() chains via the same object;
    # batchUpdate().execute() must not overwrite the stored get()-result, so guard here.
    def _execute_batch(self):
        return {}


class _FakeService:
    def __init__(self, doc_body):
        self.documents_obj = _FakeDocuments(doc_body)

    def documents(self):
        return self.documents_obj


def _paragraph(start, end, text):
    return {
        "startIndex": start,
        "endIndex": end,
        "paragraph": {"elements": [{"textRun": {"content": text}}]},
    }


def test_heading_gets_brand_color_and_font():
    body = [_paragraph(1, 20, "# Titel van het document\n")]
    service = _FakeService(body)

    # batchUpdate().execute() would overwrite get()'s stored result via the same
    # _FakeDocuments.execute — split responsibilities explicitly to avoid that clash.
    calls = {}

    def batch_update(documentId, body):
        calls["requests"] = body["requests"]

        class _Exec:
            def execute(self_inner):
                return {}

        return _Exec()

    service.documents_obj.batchUpdate = batch_update

    gdoc_tools._apply_basic_formatting(service, "doc123")

    requests = calls["requests"]
    para_style = next(r for r in requests if "updateParagraphStyle" in r)
    assert para_style["updateParagraphStyle"]["paragraphStyle"]["namedStyleType"] == "HEADING_1"

    text_style = next(r for r in requests if "updateTextStyle" in r)
    style = text_style["updateTextStyle"]["textStyle"]
    assert style["weightedFontFamily"]["fontFamily"] == gdoc_tools._BRAND_FONT_HEADING
    assert style["foregroundColor"]["color"]["rgbColor"] == gdoc_tools._BRAND_HEADING_COLOR_RGB


def test_body_text_gets_brand_font_but_not_forced_color():
    body = [_paragraph(1, 30, "Gewone body-tekst zonder kopmarkering.\n")]
    service = _FakeService(body)
    calls = {}

    def batch_update(documentId, body):
        calls["requests"] = body["requests"]

        class _Exec:
            def execute(self_inner):
                return {}

        return _Exec()

    service.documents_obj.batchUpdate = batch_update

    gdoc_tools._apply_basic_formatting(service, "doc123")

    requests = calls["requests"]
    assert len(requests) == 1
    style = requests[0]["updateTextStyle"]["textStyle"]
    assert style["weightedFontFamily"]["fontFamily"] == gdoc_tools._BRAND_FONT_BODY
    assert "foregroundColor" not in style
    assert requests[0]["updateTextStyle"]["fields"] == "weightedFontFamily"


def test_empty_paragraph_generates_no_requests():
    body = [_paragraph(1, 2, "\n")]
    service = _FakeService(body)
    calls = {}

    def batch_update(documentId, body):
        calls["requests"] = body["requests"]

        class _Exec:
            def execute(self_inner):
                return {}

        return _Exec()

    service.documents_obj.batchUpdate = batch_update

    gdoc_tools._apply_basic_formatting(service, "doc123")
    assert "requests" not in calls  # batchUpdate niet aangeroepen als er niets te doen is


def test_create_doc_via_drive_applies_brand_formatting(monkeypatch):
    """Regressietest voor het Meetingnote-gat (2026-07-06): create_doc_via_drive()
    sloeg formatting historisch over ("geen Docs API toegang") — die beperking
    bestaat niet meer (documents-scope zit al in _get_service_account_creds()),
    maar niemand had de opmaakstap teruggezet. Elke Meetingnote bleef daardoor
    onbestyled terwijl create_gdoc()-documenten al wel gebrand werden."""
    created_file = {"id": "doc456", "webViewLink": "https://docs.google.com/document/d/doc456/edit", "name": "Meetingnote test"}

    class _FakeFilesCreate:
        def execute(self):
            return created_file

    class _FakeDriveFiles:
        def create(self, **kwargs):
            return _FakeFilesCreate()

    class _FakeDriveService:
        def files(self):
            return _FakeDriveFiles()

    apply_calls = []

    def fake_apply_basic_formatting(docs_service, doc_id):
        apply_calls.append((docs_service, doc_id))

    monkeypatch.setattr(gdoc_tools, "_get_drive_write_service", lambda: _FakeDriveService())
    monkeypatch.setattr(gdoc_tools, "_get_docs_service", lambda: "fake-docs-service")
    monkeypatch.setattr(gdoc_tools, "_apply_basic_formatting", fake_apply_basic_formatting)

    result = gdoc_tools.create_doc_via_drive("Meetingnote test", "# Meetingnote\n\nInhoud.", "folder123")

    assert result["doc_id"] == "doc456"
    assert apply_calls == [("fake-docs-service", "doc456")]


def test_create_doc_via_drive_survives_formatting_failure(monkeypatch):
    """Formatting-fout mag het aanmaken van de Meetingnote nooit blokkeren —
    zelfde non-fatal contract als create_gdoc()."""
    created_file = {"id": "doc789", "webViewLink": "https://docs.google.com/document/d/doc789/edit", "name": "Meetingnote test"}

    class _FakeFilesCreate:
        def execute(self):
            return created_file

    class _FakeDriveFiles:
        def create(self, **kwargs):
            return _FakeFilesCreate()

    class _FakeDriveService:
        def files(self):
            return _FakeDriveFiles()

    def boom(docs_service, doc_id):
        raise RuntimeError("Docs API onbereikbaar")

    monkeypatch.setattr(gdoc_tools, "_get_drive_write_service", lambda: _FakeDriveService())
    monkeypatch.setattr(gdoc_tools, "_get_docs_service", lambda: "fake-docs-service")
    monkeypatch.setattr(gdoc_tools, "_apply_basic_formatting", boom)

    result = gdoc_tools.create_doc_via_drive("Meetingnote test", "# Meetingnote\n\nInhoud.", "folder123")
    assert result["doc_id"] == "doc789"  # document bestaat alsnog, ondanks de formatting-fout
