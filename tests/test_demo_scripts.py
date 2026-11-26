from scripts import demo_permissions, whoami

EXPECTED_DEMO_LINES = [
    "Priya (employee) reads her own ticket TCK-1001 -> allowed (own)",
    "Priya reads Mei's ticket TCK-1006 -> denied: not_found",
    "Priya reads a ticket that does not exist, TCK-9999 -> denied: not_found",
    "Aisha (support agent) reads TCK-1001 with no grant -> denied: not_found",
    "Aisha reads TCK-1001 after a 15-minute grant -> allowed (delegation)",
    "Tom (administrator) reads Mei's ticket TCK-1006 -> allowed (admin)",
    "Daniel (inactive employee) reads his own profile -> denied: permission_denied",
    "Nobody is signed in, request for TCK-1001 -> denied: authentication_required",
]


def test_permission_demo_prints_the_expected_decisions(capsys):
    assert demo_permissions.main() == 0
    assert capsys.readouterr().out.splitlines() == EXPECTED_DEMO_LINES


def test_whoami_rejects_bad_arguments():
    assert whoami.main(["alice"]) == 2
    assert whoami.main([]) == 2


def test_whoami_prints_the_trusted_context(monkeypatch, capsys):
    monkeypatch.setattr(whoami, "load_dotenv", lambda: None)
    monkeypatch.setattr(
        whoami, "load_demo_tokens", lambda: {"E1001": "tok-E1001-aaaaaaaaaa"}
    )
    assert whoami.main(["E1001"]) == 0
    assert capsys.readouterr().out.strip() == (
        "Authenticated: E1001 role=employee region=parramatta active=True"
    )


def test_whoami_explains_a_missing_token(monkeypatch, capsys):
    monkeypatch.setattr(whoami, "load_dotenv", lambda: None)
    monkeypatch.setattr(whoami, "load_demo_tokens", dict)
    assert whoami.main(["E1001"]) == 1
    assert "make_demo_tokens" in capsys.readouterr().out
