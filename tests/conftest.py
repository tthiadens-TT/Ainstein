"""Test-isolatie voor de hele suite.

Waarom dit bestand bestaat:
`tools._is_drive_mode()` geeft True zodra GOOGLE_SERVICE_ACCOUNT_FILE of
GOOGLE_SERVICE_ACCOUNT_JSON in de omgeving staat. Op elke machine met een
geldige .env (lokaal, VM, CI) sprong de testsuite daardoor naar de ECHTE
productie-Drive en schreef testfixture-rommel in het live
`05_Ainstein Knowledge Base/gaps.md` — het bestand dat in elke Ainstein-
conversatie in de systeemprompt wordt geinjecteerd.

Deze autouse-fixture haalt beide sleutels weg voor ELKE test, zodat
`_is_drive_mode()` altijd False teruggeeft tenzij een test dit expliciet
zelf weer zet. Zo schrijft de suite nooit meer naar productiedata.
"""

import pytest


@pytest.fixture(autouse=True)
def _no_drive_writes_in_tests(monkeypatch):
    monkeypatch.delenv("GOOGLE_SERVICE_ACCOUNT_FILE", raising=False)
    monkeypatch.delenv("GOOGLE_SERVICE_ACCOUNT_JSON", raising=False)
    yield
