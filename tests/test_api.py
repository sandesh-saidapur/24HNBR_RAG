"""API tests against the real timing database. Skipped if the database has not been built."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.api.main import create_app
from src.indexing.tabular_store import DEFAULT_DB

pytestmark = pytest.mark.skipif(not Path(DEFAULT_DB).exists(), reason="timing.duckdb not built")


@pytest.fixture(scope="module")
def client() -> TestClient:
    return TestClient(create_app())


def test_health_reports_expected_counts(client: TestClient) -> None:
    body = client.get("/api/health").json()
    assert body["status"] == "ok"
    assert body["counts"] == {"classification": 159, "penalties": 19, "sectors": 17201,
                              "media_timeline": 99}


def test_cars_are_in_official_order(client: TestClient) -> None:
    cars = client.get("/api/cars").json()
    assert len(cars) == 159
    assert cars[0]["car_number"] == 80
    assert cars[0]["status"] == "classified"
    assert cars[0]["laps"] == 156
    classified = [c["position"] for c in cars if c["status"] == "classified"]
    assert classified == list(range(1, 111))


def test_car_status_and_class_field_name(client: TestClient) -> None:
    car84 = client.get("/api/cars/84").json()
    assert car84["status"] == "DSQ"
    assert car84["class"] == "SP 9"
    assert "car_class" not in car84
    assert car84["penalties"][0]["penalty_seconds"] == 86.0


def test_car_detail_returns_penalties_for_the_car(client: TestClient) -> None:
    car63 = client.get("/api/cars/63").json()
    assert sum(p["penalty_seconds"] for p in car63["penalties"]) == 90.0


def test_laps_endpoint_returns_every_official_lap(client: TestClient) -> None:
    laps = client.get("/api/cars/80/laps", params={"limit": 2000}).json()
    assert len(laps) == 156
    assert [row["lap"] for row in laps] == list(range(1, 157))
    assert all(row["lap_time_s"] is not None for row in laps)


def test_penalties_list_and_filter(client: TestClient) -> None:
    all_penalties = client.get("/api/penalties").json()
    assert len(all_penalties) == 19
    only_95 = client.get("/api/penalties", params={"car_number": 95}).json()
    assert [p["penalty_seconds"] for p in only_95] == [45.0, 45.0]


def test_standings_by_split(client: TestClient) -> None:
    hours = client.get("/api/standings/hours").json()
    assert hours == [1, 3, 5, 7, 9, 11, 13, 15, 17, 19, 21, 23]
    rows = client.get("/api/standings/13").json()
    assert rows and rows[0]["overall_rank"] == 1


def test_media_timeline_filters(client: TestClient) -> None:
    all_media = client.get("/api/media").json()
    assert len(all_media) == 99
    on_course = client.get("/api/media", params={"on_course": True}).json()
    assert len(on_course) == 23
    times = [m["race_elapsed_s"] for m in all_media]
    assert times == sorted(times)


def test_not_found_and_validation(client: TestClient) -> None:
    assert client.get("/api/cars/1000").status_code == 404
    assert client.get("/api/standings/2").status_code == 404
    assert client.get("/api/cars/80/laps", params={"limit": 0}).status_code == 422
    assert client.get("/api/media", params={"phase": "warmup"}).status_code == 422
