"""Response models for the blood components a request can ask for."""

from pydantic import BaseModel, ConfigDict


class ComponentRead(BaseModel):
    """A blood component that can currently be requested.

    Only the identifier and the label are exposed. The waiting periods between donations
    are rules applied by the server and are not needed to raise a request.

    Attributes:
        code: Stable machine identifier, sent back as ``component_code`` on a request.
        name: Human-readable label, such as "Whole blood".
    """

    model_config = ConfigDict(from_attributes=True)

    code: str
    name: str
