"""Fail-closed SQLite reservations. Bootstrap is explicit and never overwrites."""

import json
import sqlite3
from contextlib import closing, contextmanager
from decimal import Decimal
from pathlib import Path
from urllib.parse import quote
from uuid import uuid4

from finsight.contracts.budget import BudgetSnapshot, Reservation, dollars, micro_usd
from finsight.contracts.runtime import ProviderUsage
from finsight.runtime.errors import FinsightError

IDENTITY = {
    "schema": "1",
    "budget_id": "finsight-testing-2026-10-18",
    "ceiling": 5_000_000,
    "working": 4_000_000,
    "phase2": 750_000,
}
SCHEMA = (
    "CREATE TABLE identity (key TEXT PRIMARY KEY, value TEXT NOT NULL)",
    "CREATE TABLE attempts (reservation_id TEXT PRIMARY KEY, request_id TEXT UNIQUE NOT NULL, "
    "provider TEXT NOT NULL, model TEXT NOT NULL, phase INTEGER NOT NULL CHECK(phase >= 2), "
    "maximum INTEGER NOT NULL CHECK(maximum >= 0), "
    "state TEXT NOT NULL CHECK(state IN ('reserved','dispatched','settled','unknown')), "
    "observed INTEGER CHECK(observed >= 0), usage_json TEXT, "
    "CHECK((state = 'settled' AND observed IS NOT NULL) OR "
    "(state != 'settled' AND observed IS NULL)))",
)


class BudgetLedger:
    def __init__(self, path: Path, budget_id: str):
        self.path = Path(path).resolve()
        self.budget_id = budget_id
        self.marker = self.path.with_suffix(self.path.suffix + ".identity.json")

    @classmethod
    def initialize(cls, path: Path, budget_id: str) -> "BudgetLedger":
        ledger = cls(path, budget_id)
        if budget_id != IDENTITY["budget_id"]:
            raise FinsightError("budget_identity")
        if ledger.path.exists() or ledger.marker.exists():
            raise FinsightError("budget_exists", "Existing budgets cannot be reset")
        ledger.path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with ledger.marker.open("x", encoding="utf-8") as stream:
                json.dump(IDENTITY, stream, sort_keys=True)
            # Exclusive marker creation serializes competing bootstrap attempts.
            with closing(sqlite3.connect(ledger.path)) as connection, connection:
                for statement in SCHEMA:
                    connection.execute(statement)
                connection.executemany(
                    "INSERT INTO identity VALUES (?,?)", [(k, str(v)) for k, v in IDENTITY.items()]
                )
        except FileExistsError:
            raise FinsightError("budget_exists") from None
        except (OSError, sqlite3.Error):
            # Leave identity marker on failure: never silently recover by resetting money.
            raise FinsightError("budget_unavailable") from None
        return cls.open(ledger.path, budget_id)

    @classmethod
    def open(cls, path: Path, budget_id: str) -> "BudgetLedger":
        ledger = cls(path, budget_id)
        with ledger._transaction():
            pass
        return ledger

    @contextmanager
    def _transaction(self):
        if self.budget_id != IDENTITY["budget_id"]:
            raise FinsightError("budget_identity")
        if not self.path.is_file() or not self.marker.is_file():
            raise FinsightError("budget_unavailable")
        connection = None
        try:
            if json.loads(self.marker.read_text(encoding="utf-8")) != IDENTITY:
                raise FinsightError("budget_identity")
            uri = "file:" + quote(self.path.as_posix(), safe="/:") + "?mode=rw"
            connection = sqlite3.connect(uri, uri=True, timeout=10, isolation_level=None)
            connection.execute("BEGIN IMMEDIATE")
            if connection.execute("PRAGMA integrity_check").fetchall() != [("ok",)]:
                raise FinsightError("budget_integrity")
            schemas = {
                row[0]: row[1]
                for row in connection.execute(
                    "SELECT name,sql FROM sqlite_master WHERE type='table'"
                )
            }
            if schemas != {"identity": SCHEMA[0], "attempts": SCHEMA[1]}:
                raise FinsightError("budget_integrity")
            identity = dict(connection.execute("SELECT key,value FROM identity"))
            if identity != {k: str(v) for k, v in IDENTITY.items()}:
                raise FinsightError("budget_identity")
            yield connection
            connection.commit()
        except sqlite3.OperationalError as error:
            if getattr(error, "sqlite_errorcode", None) in {
                sqlite3.SQLITE_BUSY,
                sqlite3.SQLITE_LOCKED,
            }:
                raise FinsightError("budget_busy") from None
            raise FinsightError("budget_integrity") from None
        except (sqlite3.Error, OSError, ValueError):
            raise FinsightError("budget_integrity") from None
        finally:
            if connection is not None:
                connection.close()  # Rolls back an unsuccessful transaction.

    @staticmethod
    def _totals(connection):
        rows = connection.execute("SELECT phase,maximum,state,observed FROM attempts").fetchall()
        accounted = sum(r[3] for r in rows if r[2] == "settled")
        reserved = sum(r[1] for r in rows if r[2] != "settled")
        phase2 = sum((r[3] if r[2] == "settled" else r[1]) for r in rows if r[0] == 2)
        return accounted, reserved, phase2

    def reserve(
        self,
        request_id: str,
        provider: str,
        model: str,
        maximum_usd: Decimal,
        phase: int,
        *,
        working_usd: Decimal = Decimal("4"),
        phase2_usd: Decimal = Decimal("0.75"),
    ) -> Reservation:
        amount = micro_usd(maximum_usd)
        micro_usd(working_usd)
        micro_usd(phase2_usd)
        working_cap = min(IDENTITY["working"], int(working_usd * 1_000_000))
        phase_cap = min(IDENTITY["phase2"], int(phase2_usd * 1_000_000))
        if not request_id.strip() or not model.strip() or provider not in {"nebius", "anthropic"}:
            raise FinsightError("budget_identity")
        if isinstance(phase, bool) or not isinstance(phase, int) or phase < 2:
            raise FinsightError("budget_identity")
        identity = uuid4().hex
        with self._transaction() as connection:
            if connection.execute(
                "SELECT 1 FROM attempts WHERE request_id=?", (request_id,)
            ).fetchone():
                raise FinsightError("duplicate_request")
            accounted, reserved, phase2 = self._totals(connection)
            if accounted + reserved + amount > working_cap or (
                phase == 2 and phase2 + amount > phase_cap
            ):
                raise FinsightError("budget_exceeded")
            connection.execute(
                "INSERT INTO attempts VALUES (?,?,?,?,?,?,'reserved',NULL,NULL)",
                (identity, request_id, provider, model, phase, amount),
            )
        return Reservation(
            reservation_id=identity,
            request_id=request_id,
            maximum_usd=dollars(amount),
            state="reserved",
        )

    def mark_dispatched(self, reservation_id: str) -> None:
        with self._transaction() as connection:
            result = connection.execute(
                "UPDATE attempts SET state='dispatched' "
                "WHERE reservation_id=? AND state='reserved'",
                (reservation_id,),
            )
            if result.rowcount != 1:
                raise FinsightError("duplicate_request")

    def settle(
        self,
        reservation_id: str,
        observed_usd: Decimal | None,
        *,
        usage: ProviderUsage | None = None,
    ) -> None:
        observed = None if observed_usd is None else micro_usd(observed_usd)
        state = "unknown" if observed is None else "settled"
        with self._transaction() as connection:
            result = connection.execute(
                "UPDATE attempts SET state=?, observed=?, usage_json=? "
                "WHERE reservation_id=? AND state='dispatched'",
                (state, observed, usage.model_dump_json() if usage else None, reservation_id),
            )
            if result.rowcount != 1:
                raise FinsightError("budget_state")

    def snapshot(self) -> BudgetSnapshot:
        with self._transaction() as connection:
            accounted, reserved, phase2 = self._totals(connection)
        return BudgetSnapshot(
            budget_id=self.budget_id,
            accounted_usd=dollars(accounted),
            reserved_usd=dollars(reserved),
            available_usd=dollars(max(0, IDENTITY["working"] - accounted - reserved)),
            phase2_available_usd=dollars(max(0, IDENTITY["phase2"] - phase2)),
        )
