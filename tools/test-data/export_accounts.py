"""Export a manual-test account sheet from a fixture manifest; never exports passwords."""

import argparse
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    data = json.loads(args.manifest.read_text(encoding="utf-8"))
    lines = [
        "# Priveo manual-test accounts",
        "",
        f"Admin login: **{data['admin_login']}**. Admin password is the value chosen at initialization.",
        "Customer/Crew passwords come from TEST_DATA_PASSWORD; retained scenarios keep their old password.",
        "Use docs/testing/test-data-plan.md for setup, checks and scenario limitations.",
        "",
        "| Scenario | Date anchor | Case | Customer | Manager | Member | Trainee |",
        "|---|---|---|---|---|---|---|",
    ]
    for item in data["scenarios"]:
        columns = [
            item["id"],
            item["as_of"],
            item["name"],
            item["customer_login"],
            *item["crew_logins"][:3],
        ]
        lines.append(
            "| " + " | ".join(value.replace("|", "\\|") for value in columns) + " |"
        )
    lines += ["", "Extra Crew variants:", ""]
    for item in data["scenarios"]:
        if len(item["crew_logins"]) > 3:
            lines.append(f"- {item['id']}: " + ", ".join(item["crew_logins"][3:]))
    lines += ["", "Dataset limitations:", ""]
    lines += ["- " + limitation for limitation in data.get("limitations", [])]
    if args.output.resolve() == args.manifest.resolve():
        parser.error("Output must not overwrite the JSON manifest.")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
