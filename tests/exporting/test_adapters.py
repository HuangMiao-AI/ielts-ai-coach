"""Adapter-boundary tests with no external network behavior."""

from __future__ import annotations

import socket

import pytest

from tests.exporting.test_contracts import _record

from ielts_ai_coach.exporting.adapters.feishu_stub import FeishuAdapterStub
from ielts_ai_coach.exporting.errors import UnsupportedAdapterError


def test_feishu_stub_never_opens_network_or_reads_credentials(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    network_calls: list[object] = []

    def reject_network(*args: object, **kwargs: object) -> None:
        network_calls.append((args, kwargs))
        raise AssertionError("network must remain unused")

    monkeypatch.setattr(socket, "create_connection", reject_network)
    adapter = FeishuAdapterStub()

    with pytest.raises(UnsupportedAdapterError, match="feishu_not_configured"):
        adapter.preview(_record())
    with pytest.raises(UnsupportedAdapterError, match="feishu_not_configured"):
        adapter.apply(_record())

    assert network_calls == []
    assert not hasattr(adapter, "token")
    assert not hasattr(adapter, "api_key")
