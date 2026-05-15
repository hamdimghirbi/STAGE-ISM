"""Tests for the seed-data idempotency."""
from __future__ import annotations

from sqlmodel import Session, select

import app.db as db_module
from app.models import User
from app.seed import seed_demo_data


def test_seed_is_idempotent(client) -> None:  # noqa: ARG001
    """Calling seed twice should not duplicate the demo user."""
    # The `client` fixture already triggers seeding via lifespan.
    # Run it again — the early-return path should fire.
    seed_demo_data()

    with Session(db_module.engine) as s:
        users = list(s.exec(select(User)).all())
    assert len(users) == 1
