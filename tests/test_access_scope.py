"""Access scope service unit tests."""

from __future__ import annotations

import pandas as pd
import pytest

from app.services.access_scope_service import AccessScopeError, AccessScopeService


def test_filial_scope_filters_dataframe():
    svc = AccessScopeService()
    viewer = svc.from_session(profile="filial", branch="SPO", login="u1")
    df = pd.DataFrame({"filial": ["SPO", "CWB", "SPO"], "x": [1, 2, 3]})
    out = svc.apply_dataframe_scope(df, viewer)
    assert list(out["filial"].unique()) == ["SPO"]
    assert len(out) == 2


def test_admin_sees_all():
    svc = AccessScopeService()
    viewer = svc.from_session(profile="admin", branch=None, login="admin")
    df = pd.DataFrame({"filial": ["SPO", "CWB"], "x": [1, 2]})
    out = svc.apply_dataframe_scope(df, viewer)
    assert len(out) == 2


def test_filial_cannot_request_other_branch():
    svc = AccessScopeService()
    viewer = svc.from_session(profile="filial", branch="SPO", login="u1")
    assert svc.resolve_branch_filter(viewer, ["CWB", "SPO"]) == ["SPO"]


def test_filial_without_branch_fails():
    svc = AccessScopeService()
    with pytest.raises(AccessScopeError):
        svc.from_session(profile="filial", branch="", login="u1")
