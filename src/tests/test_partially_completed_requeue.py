"""Regression for the 'no transition; re-queued' infinite loop.

A PartiallyCompleted show/season whose only incomplete children are Failed/Paused
produces an empty fan-out from process_event (those children return
no_further_processing). Before the fix, program.run re-queued such events with
run_at=now, which next() re-popped immediately -> a tight infinite loop spamming
"Pipeline event had no transition; re-queued ...".

process_event must return no service and no items for these cases so program.run
drops the event instead of re-queuing it.
"""

from __future__ import annotations

import datetime
from unittest.mock import Mock, patch

import pytest

from program.media.item import Episode, Season, Show
from program.media.state import States
from program.program import Program
from program.services.downloaders.realdebrid import RealDebridDownloader
from program.services.filesystem import FilesystemService
from program.services.indexers import IndexerService
from program.services.post_processing import PostProcessing
from program.services.scrapers import Scraping
from program.services.updaters.plex import PlexUpdater
from program.state_transition import process_event


@pytest.fixture
def show() -> Show:
    show = Show(
        {
            "imdb_id": "tt0903747",
            "requested_by": "pytest",
            "title": "Breaking Bad",
            "aired_at": datetime.datetime(2008, 1, 20),
        }
    )
    season = Season({"number": 1, "aired_at": datetime.datetime(2008, 1, 20)})
    episode = Episode({"number": 1, "aired_at": datetime.datetime(2008, 1, 20)})
    season.add_episode(episode)
    show.add_season(season)
    return show


@pytest.fixture
def season(show: Show) -> Season:
    return show.seasons[0]


@pytest.fixture
def episode(season: Season) -> Episode:
    return season.episodes[0]


def _mock_program() -> Mock:
    services = Mock()
    services.indexer = Mock(spec=IndexerService)
    services.scraping = Mock(spec=Scraping)
    services.scraping.should_submit = Mock(return_value=True)
    services.downloader = Mock(spec=RealDebridDownloader)
    services.filesystem = Mock(spec=FilesystemService)
    services.updater = Mock(spec=PlexUpdater)
    services.post_processing = Mock(spec=PostProcessing)
    program = Mock(spec=Program)
    program.services = services
    return program


def test_partially_completed_season_with_only_failed_child_yields_no_transition(
    season: Season, episode: Episode
):
    season.last_state = States.PartiallyCompleted
    episode.last_state = States.Failed
    program = _mock_program()

    with patch("program.state_transition.di") as mock_di:
        mock_di.__getitem__.return_value = program
        result = process_event("StateTransition", season, None, None)

    assert result.service is None
    assert result.related_media_items == []


def test_partially_completed_show_with_only_failed_child_yields_no_transition(
    show: Show,
):
    show.last_state = States.PartiallyCompleted
    show.seasons[0].last_state = States.PartiallyCompleted
    show.seasons[0].episodes[0].last_state = States.Failed
    program = _mock_program()

    with patch("program.state_transition.di") as mock_di:
        mock_di.__getitem__.return_value = program
        result = process_event("StateTransition", show, None, None)

    assert result.service is None
    assert result.related_media_items == []
