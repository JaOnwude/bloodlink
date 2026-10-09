"""Tests of the blood component list that the request form reads."""

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.models import ComponentType
from tests.helpers import API

COMPONENTS = f"{API}/components"


def test_lists_active_components_alphabetically_without_signing_in(
    client: TestClient, reference_data: None
) -> None:
    response = client.get(COMPONENTS)

    assert response.status_code == 200
    assert response.json() == [
        {"code": "plasma", "name": "Plasma"},
        {"code": "platelets", "name": "Platelets"},
        {"code": "whole_blood", "name": "Whole blood"},
    ]


def test_an_inactive_component_is_left_out(
    client: TestClient, db_session: Session, reference_data: None
) -> None:
    plasma = db_session.exec(select(ComponentType).where(ComponentType.code == "plasma")).one()
    plasma.is_active = False
    db_session.add(plasma)
    db_session.commit()

    codes = [item["code"] for item in client.get(COMPONENTS).json()]

    assert codes == ["platelets", "whole_blood"]


def test_waiting_periods_are_not_exposed(client: TestClient, reference_data: None) -> None:
    for item in client.get(COMPONENTS).json():
        assert set(item) == {"code", "name"}
