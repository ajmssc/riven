"""Tests for Downloader.match_file_to_item() — the successor to RealDebridDownloader._matches_item()."""
from unittest.mock import MagicMock, patch

import pytest
from RTN import parse

from program.media.item import Episode, Movie, Season, Show
from program.services.downloaders import Downloader
from program.services.downloaders.models import (
    DebridFile,
    DownloadedTorrent,
    TorrentContainer,
    TorrentInfo,
)


def _make_downloader() -> Downloader:
    dl = Downloader.__new__(Downloader)
    dl.service = MagicMock()
    return dl


def _debrid_file(filename: str, filesize: int = 1_000_000_000) -> DebridFile:
    return DebridFile(file_id=1, filename=filename, filesize=filesize)


def _download_result(infohash: str = "abc123") -> DownloadedTorrent:
    info = TorrentInfo(id=1, name="Test")
    container = TorrentContainer(infohash=infohash)
    return DownloadedTorrent(id=1, infohash=infohash, container=container, info=info)


def _show_tree(title: str, season_num: int, ep_nums: list[int]):
    show = Show({"title": title, "imdb_id": "tt1405406", "type": "show"})
    season = Season({"number": season_num, "type": "season"})
    episodes = [Episode({"number": n, "type": "episode"}) for n in ep_nums]
    for ep in episodes:
        season.add_episode(ep)
        ep.parent = season
    show.add_season(season)
    season.parent = show
    return show, season, episodes


def test_matches_item_movie():
    dl = _make_downloader()
    item = Movie({"imdb_id": "tt1375666", "title": "Inception", "type": "movie"})
    file = _debrid_file("Inception.2010.1080p.mkv", 2_000_000_000)
    file_data = parse("Inception.2010.1080p.mkv")
    result_obj = _download_result()

    with patch.object(dl, "_update_attributes"):
        result = dl.match_file_to_item(item, file_data, file, result_obj)

    assert result is True


def test_matches_item_episode():
    dl = _make_downloader()
    show, season, episodes = _show_tree("The Vampire Diaries", 1, [1, 2])
    ep = episodes[0]

    file = _debrid_file("The.Vampire.Diaries.S01E01.mkv", 800_000_000)
    file_data = parse("The.Vampire.Diaries.S01E01.mkv")
    result_obj = _download_result()

    with patch.object(dl, "_update_attributes"):
        result = dl.match_file_to_item(ep, file_data, file, result_obj, show=show)

    assert result is True


def test_matches_item_season():
    dl = _make_downloader()
    show, season, episodes = _show_tree("The Vampire Diaries", 1, [1, 2])

    file = _debrid_file("The.Vampire.Diaries.S01E01.mkv", 800_000_000)
    file_data = parse("The.Vampire.Diaries.S01E01.mkv")
    result_obj = _download_result()

    with patch.object(dl, "_update_attributes"):
        result = dl.match_file_to_item(season, file_data, file, result_obj, show=show)

    assert result is True


def test_matches_item_episode_not_in_show():
    """A file for episode 5 returns False when only episodes 1-2 exist in the show."""
    dl = _make_downloader()
    show, season, episodes = _show_tree("Test Show", 1, [1, 2])
    ep1 = episodes[0]

    file = _debrid_file("Test.Show.S01E05.mkv", 800_000_000)
    file_data = parse("Test.Show.S01E05.mkv")
    result_obj = _download_result()

    with patch.object(dl, "_update_attributes"):
        result = dl.match_file_to_item(ep1, file_data, file, result_obj, show=show)

    assert result is False


def test_matches_item_movie_with_tv_file():
    """A TV-episode file does not match a movie item."""
    dl = _make_downloader()
    item = Movie({"imdb_id": "tt1375666", "title": "Inception", "type": "movie"})

    file = _debrid_file("Inception.S01E01.mkv", 800_000_000)
    file_data = parse("Inception.S01E01.mkv")
    result_obj = _download_result()

    with patch.object(dl, "_update_attributes"):
        result = dl.match_file_to_item(item, file_data, file, result_obj)

    assert result is False
