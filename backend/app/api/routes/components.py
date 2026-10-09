"""The list of blood components that requests may ask for.

The components live in the ``component_types`` table, so the request form reads them from
here instead of hard-coding them. Adding or retiring a component is then a change to data
that every screen picks up, with no code change or redeploy.

The list is public: it is reference data, contains nothing personal, and is the same for
every visitor.
"""

from fastapi import APIRouter
from sqlmodel import col, select

from app.api.deps import SessionDep
from app.models import ComponentType
from app.schemas.component import ComponentRead

router = APIRouter(prefix="/components", tags=["reference"])


@router.get("", response_model=list[ComponentRead], summary="Blood components")
def list_components(session: SessionDep) -> list[ComponentRead]:
    """Return the active blood components, in alphabetical order of their names.

    Inactive components are kept in the table for the history of past requests, but are
    left out here because they can no longer be requested.
    """
    components = session.exec(
        select(ComponentType)
        .where(col(ComponentType.is_active).is_(True))
        .order_by(col(ComponentType.name))
    ).all()
    return [ComponentRead.model_validate(component) for component in components]
