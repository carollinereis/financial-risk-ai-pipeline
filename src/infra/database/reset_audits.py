"""Clears stored audit runs so the committee pipeline can be tested from scratch.

Run from the repository root:

    python -m src.infra.database.reset_audits            # reset to first-boot state
    python -m src.infra.database.reset_audits --no-seed  # leave the tables empty

Customers, their trained risk scores, and the saved XGBoost model are untouched;
only what the agent committee produced is cleared. Stop the API first - DuckDB is
single-writer, and a running uvicorn holds the handle.
"""

import argparse

from src.infra.database.database import reset_audit_runs


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--no-seed",
        dest="reseed",
        action="store_false",
        help=(
            "Leave the tables empty instead of restoring the fixture rows. The next "
            "API startup re-seeds them anyway, since seeding triggers on an empty table."
        ),
    )
    args = parser.parse_args()

    result = reset_audit_runs(reseed=args.reseed)
    print(
        f"Deleted {result['evaluations_deleted']} agent evaluations and "
        f"{result['applications_deleted']} loan applications."
    )
    print("Fixture rows restored." if result["reseeded"] else "Tables left empty.")


if __name__ == "__main__":
    main()
