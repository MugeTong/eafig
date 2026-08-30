"""Shared pytest fixtures for the eafig test suite."""

import pytest

from eafig import schema, state


@pytest.fixture(autouse=True)
def _reset_state():
    """Reset the global config state before and after each test."""

    def _reset():
        # Keep the object identity stable, just like state.merge(). This also
        # prevents tests from hiding stale-reference regressions.
        state.stored_conf.clear()
        schema.schema_root.children.clear()
        schema.schema_root.fields = ()
        schema.schema_root.registered = False
        schema.schema_root.hidden = False
        schema.schema_root.ignore_unknown_keys = True

    _reset()
    yield
    _reset()
