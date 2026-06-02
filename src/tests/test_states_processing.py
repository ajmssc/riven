"""Tests for media item state transitions and process_event routing."""
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from kink import di

from program.media.item import Episode, MediaItem, Movie, Season, Show
from program.media.state import States
from program.state_transition import process_event
from program.types import ProcessedEvent


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def movie():
    return Movie({"imdb_id": "tt1375666", "requested_by": "Iceberg"})


@pytest.fixture
def show():
    s = Show({"imdb_id": "tt0903747", "requested_by": "Iceberg"})
    season = Season({"number": 1})
    ep = Episode({"number": 1})
    season.add_episode(ep)
    s.add_season(season)
    ep.parent = season
    season.parent = s
    return s


@pytest.fixture
def season(show):
    return show.seasons[0]


@pytest.fixture
def episode(season):
    return season.episodes[0]


# ---------------------------------------------------------------------------
# Helper: build a mock di[Program] with mock services
# ---------------------------------------------------------------------------

def _mock_program_services():
    """Return (program_mock, services_mock) with all service slots as MagicMocks."""
    from program.program import Program

    services = MagicMock()
    services.indexer = MagicMock()
    services.scraping = MagicMock()
    services.downloader = MagicMock()
    services.filesystem = MagicMock()
    services.updater = MagicMock()
    services.post_processing = MagicMock()

    program = MagicMock(spec=Program)
    program.services = services
    return program, services


# ---------------------------------------------------------------------------
# State determination tests
# ---------------------------------------------------------------------------

def test_initial_state_movie_requested(movie):
    """Movie with imdb_id + requested_by starts in Requested."""
    assert movie.state == States.Requested


def test_initial_state_show_unreleased(show):
    """Show with no aired_at on seasons starts in Unreleased."""
    # Show._determine_state returns Unreleased when all seasons have no released episodes
    assert show.state == States.Unreleased


def test_indexed_state_movie():
    """Movie with title and a past aired_at transitions to Indexed."""
    m = Movie({"imdb_id": "tt1375666", "requested_by": "Iceberg"})
    m.set("title", "Inception")
    m.set("aired_at", datetime(2010, 7, 16))
    assert m.state == States.Indexed


def test_unreleased_state_movie():
    """Movie with title but no aired_at stays in Unreleased."""
    m = Movie({"imdb_id": "tt1375666", "requested_by": "Iceberg"})
    m.set("title", "Inception")
    assert m.state == States.Unreleased


def test_requested_state_movie():
    """Movie with only imdb_id + requested_by is in Requested state."""
    m = Movie({"imdb_id": "tt1375666", "requested_by": "Iceberg"})
    assert m.state == States.Requested


def test_episode_initial_state(episode):
    """Episode without parent show context starts in Unknown."""
    assert episode.state == States.Unknown


# ---------------------------------------------------------------------------
# process_event routing tests
# Uses item.last_state (the persisted DB column) for routing decisions.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("last_state,expected_service_attr", [
    (States.Unknown, "indexer"),
    (States.Requested, "indexer"),
    (States.Scraped, "downloader"),
    (States.Downloaded, "filesystem"),
    (States.Symlinked, "updater"),
])
def test_process_event_routes_by_last_state(last_state, expected_service_attr, movie):
    """process_event routes to the correct service based on item.last_state."""
    from program.program import Program

    program, services = _mock_program_services()
    di[Program] = program

    movie.last_state = last_state
    result = process_event("StateTransition", existing_item=movie)

    expected_service = getattr(services, expected_service_attr)
    assert result.service is expected_service

    di._services.pop(Program, None)


def test_process_event_completed_routes_to_post_processing(movie):
    """A Completed item is routed to post_processing (first time)."""
    from program.program import Program

    program, services = _mock_program_services()
    di[Program] = program

    movie.last_state = States.Completed
    # emitted_by is NOT post_processing
    result = process_event("StateTransition", existing_item=movie)

    assert result.service is services.post_processing

    di._services.pop(Program, None)


def test_process_event_completed_no_reprocess(movie):
    """A Completed item emitted by post_processing returns no_further_processing."""
    from program.program import Program

    program, services = _mock_program_services()
    di[Program] = program

    movie.last_state = States.Completed
    result = process_event(services.post_processing, existing_item=movie)

    assert result.service is None

    di._services.pop(Program, None)


def test_process_event_failed_returns_no_processing(movie):
    """Failed/Paused items get no further processing."""
    from program.program import Program

    program, services = _mock_program_services()
    di[Program] = program

    for blocked_state in (States.Failed, States.Paused):
        movie.last_state = blocked_state
        result = process_event("StateTransition", existing_item=movie)
        assert result.service is None, f"Expected None for {blocked_state}"

    di._services.pop(Program, None)


def test_process_event_with_content_item_routes_to_indexer():
    """New content items (no existing_item) always go to indexer."""
    from program.program import Program

    program, services = _mock_program_services()
    di[Program] = program

    content = Movie({"imdb_id": "tt9999999", "requested_by": "user"})
    result = process_event("TraktContent", content_item=content)

    assert result.service is services.indexer

    di._services.pop(Program, None)


def test_process_event_indexed_routes_to_scraping(movie):
    """Indexed item routes to scraping service."""
    from program.program import Program

    program, services = _mock_program_services()
    services.scraping.should_submit.return_value = True
    di[Program] = program

    movie.last_state = States.Indexed
    result = process_event("IndexerService", existing_item=movie)

    assert result.service is services.scraping

    di._services.pop(Program, None)
