"""Scan-time recovery for stale CDN links that still answer HTTP 200/206.

Regression for the bug where a Completed/symlinked item plays fine from the web
(the /stream/file endpoint refreshes the unrestricted URL) yet fails from the
filesystem with "Input/output error". The provider returns a successful status
with an empty/short body for a ranged scan request; that previously surfaced as a
hard EIO (EmptyDataException/ByteLengthMismatchException -> errno.EIO).

_fetch_discrete_byte_range must refresh the URL and retry once, and only degrade
to a link-unavailable error (RivenVFS maps it to ENOENT + rescrape) if a fresh URL
still yields a bad body.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, patch

import pytest
import trio

from program.services.streaming.exceptions import DebridServiceLinkUnavailable
from program.services.streaming.media_stream import MediaStream


class _FakeResponse:
    def __init__(self, data: bytes) -> None:
        self._data = data

    async def aread(self) -> bytes:
        return self._data

    async def aclose(self) -> None:
        return None


def _fake_establish_connection(bodies: list[bytes]):
    """Yield a fake response body per call, repeating the last one."""

    state = {"i": 0}

    @asynccontextmanager
    async def establish_connection(*, start: int, end: int):  # noqa: ARG001
        body = bodies[min(state["i"], len(bodies) - 1)]
        state["i"] += 1
        yield _FakeResponse(body)

    return establish_connection


@pytest.fixture
def media_stream_kwargs() -> dict:
    return dict(
        fh=1,
        file_size=1_000_000,
        path="/movies/Test.mkv",
        original_filename="Test.mkv",
        provider="torbox",
        initial_url="https://cdn.example/old?token=abc",
    )


async def _make_stream(nursery: trio.Nursery, **kwargs) -> MediaStream:
    with patch(
        "program.services.streaming.media_stream.shutting_down", return_value=False
    ):
        return MediaStream(nursery=nursery, **kwargs)


def test_empty_body_refreshes_url_and_retries(media_stream_kwargs):
    async def _run() -> None:
        async with trio.open_nursery() as nursery:
            stream = await _make_stream(nursery, **media_stream_kwargs)
            refresh = AsyncMock(return_value=True)

            with (
                patch.object(
                    stream,
                    "establish_connection",
                    _fake_establish_connection([b"", b"x" * 10]),
                ),
                patch.object(stream, "_refresh_download_url", refresh),
            ):
                data = await stream._fetch_discrete_byte_range(
                    start=0, size=10, should_cache=False
                )

            assert data == b"x" * 10
            refresh.assert_awaited_once()

    trio.run(_run)


def test_short_body_refreshes_url_and_retries(media_stream_kwargs):
    async def _run() -> None:
        async with trio.open_nursery() as nursery:
            stream = await _make_stream(nursery, **media_stream_kwargs)
            refresh = AsyncMock(return_value=True)

            with (
                patch.object(
                    stream,
                    "establish_connection",
                    _fake_establish_connection([b"short", b"x" * 10]),
                ),
                patch.object(stream, "_refresh_download_url", refresh),
            ):
                data = await stream._fetch_discrete_byte_range(
                    start=0, size=10, should_cache=False
                )

            assert data == b"x" * 10
            refresh.assert_awaited_once()

    trio.run(_run)


def test_persistent_bad_body_raises_link_unavailable_not_eio(media_stream_kwargs):
    """When even a refreshed URL yields a bad body, surface ENOENT (link
    unavailable) rather than a hard EIO."""

    async def _run() -> None:
        async with trio.open_nursery() as nursery:
            stream = await _make_stream(nursery, **media_stream_kwargs)

            with (
                patch.object(
                    stream,
                    "establish_connection",
                    _fake_establish_connection([b""]),
                ),
                patch.object(
                    stream, "_refresh_download_url", AsyncMock(return_value=False)
                ),
            ):
                with pytest.raises(DebridServiceLinkUnavailable):
                    await stream._fetch_discrete_byte_range(
                        start=0, size=10, should_cache=False
                    )

    trio.run(_run)


def test_refresh_only_attempted_once(media_stream_kwargs):
    """A refresh that returns a still-bad URL must not loop forever."""

    async def _run() -> None:
        async with trio.open_nursery() as nursery:
            stream = await _make_stream(nursery, **media_stream_kwargs)
            refresh = AsyncMock(return_value=True)

            with (
                patch.object(
                    stream,
                    "establish_connection",
                    _fake_establish_connection([b"", b""]),
                ),
                patch.object(stream, "_refresh_download_url", refresh),
            ):
                with pytest.raises(DebridServiceLinkUnavailable):
                    await stream._fetch_discrete_byte_range(
                        start=0, size=10, should_cache=False
                    )

            refresh.assert_awaited_once()

    trio.run(_run)
