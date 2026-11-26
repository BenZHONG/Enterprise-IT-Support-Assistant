import dataclasses

import pytest

from assistant_app.security.authn import TokenAuthenticator, load_demo_tokens
from assistant_app.security.context import EmployeeContext
from assistant_app.security.errors import ServiceError
from mock_itsm import seed_data
from scripts.demo_wiring import SeedEmployeeDirectory
from scripts.make_demo_tokens import generate_lines

DIRECTORY = SeedEmployeeDirectory()


def token_for(employee_id):
    return f"tok-{employee_id}-aaaaaaaaaa"


ALL_TOKENS = {e.employee_id: token_for(e.employee_id) for e in seed_data.EMPLOYEES}
AUTH = TokenAuthenticator(ALL_TOKENS, DIRECTORY)


@pytest.mark.parametrize(
    ("employee_id", "role", "region"),
    [
        ("E1001", "employee", "parramatta"),
        ("E1005", "it_support_agent", "sydney"),
        ("E1006", "it_administrator", "melbourne"),
    ],
)
def test_valid_token_builds_the_context_from_the_directory(employee_id, role, region):
    context = AUTH.authenticate(token_for(employee_id))
    assert (context.employee_id, context.role, context.region_id) == (
        employee_id,
        role,
        region,
    )
    assert context.active is True


def test_inactive_employee_still_gets_a_context_marked_inactive():
    assert AUTH.authenticate(token_for("E1008")).active is False


@pytest.mark.parametrize(
    "bad_token",
    [
        "wrong-token-value-123",
        "",
        None,
        12345,
        "x" * 1000,
        token_for("E1001").upper(),
        token_for("E1001") + " ",
    ],
)
def test_bad_tokens_are_refused(bad_token):
    with pytest.raises(ServiceError) as info:
        AUTH.authenticate(bad_token)
    assert info.value.code == "authentication_required"


def test_token_for_an_employee_missing_from_the_directory_is_refused():
    auth = TokenAuthenticator({"E9999": "tok-E9999-aaaaaaaaaa"}, DIRECTORY)
    with pytest.raises(ServiceError) as info:
        auth.authenticate("tok-E9999-aaaaaaaaaa")
    assert info.value.code == "authentication_required"


def test_an_employee_id_is_not_a_credential():
    with pytest.raises(ServiceError) as info:
        AUTH.authenticate("E1006")
    assert info.value.code == "authentication_required"


def test_all_failures_look_identical():
    ghost = TokenAuthenticator({"E9999": "tok-E9999-aaaaaaaaaa"}, DIRECTORY)
    with pytest.raises(ServiceError) as wrong_token:
        AUTH.authenticate("wrong-token-value-123")
    with pytest.raises(ServiceError) as unknown_employee:
        ghost.authenticate("tok-E9999-aaaaaaaaaa")
    assert wrong_token.value.code == unknown_employee.value.code
    assert wrong_token.value.message == unknown_employee.value.message


def test_short_tokens_are_rejected_at_setup():
    with pytest.raises(ValueError):
        TokenAuthenticator({"E1001": "short"}, DIRECTORY)


def test_duplicate_tokens_are_rejected_at_setup():
    token = "tok-shared-aaaaaaaaaa"
    with pytest.raises(ValueError):
        TokenAuthenticator({"E1001": token, "E1002": token}, DIRECTORY)


def test_bad_employee_id_is_rejected_at_setup():
    with pytest.raises(ValueError):
        TokenAuthenticator({"alice": "tok-alice-aaaaaaaaaa"}, DIRECTORY)


def test_plain_tokens_are_not_kept_in_memory_objects():
    token = token_for("E1001")
    assert token not in repr(AUTH)
    assert token not in str(vars(AUTH))


def test_context_is_immutable():
    context = AUTH.authenticate(token_for("E1001"))
    with pytest.raises(dataclasses.FrozenInstanceError):
        context.role = "it_administrator"


def test_context_rejects_unknown_roles():
    with pytest.raises(ValueError):
        EmployeeContext("E1001", "wizard", "sydney", True)


def test_loader_reads_prefixed_variables_and_skips_blank_and_other_ones():
    env = {
        "DEMO_TOKEN_E1001": "  tok-E1001-aaaaaaaaaa  ",
        "DEMO_TOKEN_E1002": "",
        "OPENAI_API_KEY": "sk-unrelated",
        "PATH": "C:\\Windows",
    }
    assert load_demo_tokens(env) == {"E1001": "tok-E1001-aaaaaaaaaa"}


def test_loader_rejects_a_badly_named_variable():
    with pytest.raises(ValueError, match="DEMO_TOKEN_alice"):
        load_demo_tokens({"DEMO_TOKEN_alice": "tok-alice-aaaaaaaaaa"})


def test_generated_tokens_round_trip_through_the_loader_and_authenticator():
    env = dict(line.split("=", 1) for line in generate_lines())
    auth = TokenAuthenticator(load_demo_tokens(env), DIRECTORY)
    for employee in seed_data.EMPLOYEES:
        token = env[f"DEMO_TOKEN_{employee.employee_id}"]
        assert auth.authenticate(token).employee_id == employee.employee_id


def test_generated_tokens_differ_every_time():
    assert generate_lines() != generate_lines()
