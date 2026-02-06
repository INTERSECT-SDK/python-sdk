from typing import Any

from pydantic import TypeAdapter

GENERIC_MESSAGE_SERIALIZER: TypeAdapter[Any] = TypeAdapter(Any)
