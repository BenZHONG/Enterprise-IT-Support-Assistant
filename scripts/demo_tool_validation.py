"""Demo: python -m scripts.demo_tool_validation

Shows five pretend tool calls from a model being accepted or refused.
"""

from assistant_app.schemas.tools import ToolInputError, parse_tool_arguments

CASES = (
    ("check_user", "{}"),
    ("check_user", '{"employee_id": "E1002"}'),
    ("check_network_outage_by_region", '{"region": "melbourne"}'),
    ("create_support_ticket", '{"summary": "Hi", "description": "Too short summary"}'),
    ("create_ticket", "{}"),
)


def main() -> int:
    for tool, raw in CASES:
        try:
            arguments = parse_tool_arguments(tool, raw)
            print(f"ACCEPTED  {tool} {arguments.model_dump()}")
        except ToolInputError as exc:
            print(f"REJECTED  {tool} [{exc.code}] {exc.message}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
