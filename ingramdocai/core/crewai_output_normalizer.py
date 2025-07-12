import json
import re
from typing import Any, List, Union
from pydantic import BaseModel


def normalize_crewai_output(result: Any) -> List[dict]:
    """
    Normalizes CrewAI output into a list of plain dicts.

    Handles:
    - result.pydantic: flat model, list model, or wrapped list
    - result.raw: markdown-wrapped or plain JSON string
    - direct list of BaseModel instances
    - flat single BaseModel

    Returns:
        List[dict] - always safe for downstream processing and state storage

    Raises:
        ValueError if format is unsupported or malformed
    """
    # Case 1: CrewResult-style object with .pydantic
    if hasattr(result, "pydantic") and result.pydantic is not None:
        return _extract_and_serialize(result.pydantic)

    # Case 2: CrewResult-style object with .raw
    if hasattr(result, "raw"):
        raw_str = result.raw
        parsed = _parse_json_from_raw(raw_str)
        return _extract_and_serialize(parsed)

    # Case 3: Already a list
    if isinstance(result, list):
        return _extract_and_serialize(result)

    # Case 4: A single BaseModel
    if isinstance(result, BaseModel):
        return _extract_and_serialize(result)

    raise ValueError("Unsupported CrewAI output format. Must be model, list, or have .pydantic/.raw.")


def _extract_and_serialize(obj: Union[BaseModel, List[BaseModel], Any]) -> List[dict]:
    """
    Safely extracts a list of dicts from a BaseModel, a list of BaseModels, or a wrapped model.
    This function ensures downstream flow steps can iterate and store outputs without crash.
    """
    # Case: already a list
    if isinstance(obj, list):
        return [
            item.model_dump() if hasattr(item, "model_dump") else dict(item)
            for item in obj
        ]

    # Case: a single BaseModel
    if isinstance(obj, BaseModel):
        list_fields = [(k, v) for k, v in obj.__dict__.items() if isinstance(v, list)]
        if len(list_fields) == 1:
            _, items = list_fields[0]
            return [
                item.model_dump() if hasattr(item, "model_dump") else dict(item)
                for item in items
            ]

        model_fields = [(k, v) for k, v in obj.__dict__.items() if isinstance(v, BaseModel)]
        if len(model_fields) == 1:
            _, inner_model = model_fields[0]
            return [inner_model.model_dump() if hasattr(inner_model, "model_dump") else dict(inner_model)]

        return [obj.model_dump() if hasattr(obj, "model_dump") else dict(obj)]

    # ✅ NEW CASE: already a flat dict
    if isinstance(obj, dict):
        return [obj]

    raise ValueError("Cannot serialize: input must be list, BaseModel, or dict.")


def _parse_json_from_raw(raw_str: str) -> Any:
    """
    Extracts JSON from a markdown-style wrapped string such as:
    ```json
    {...}
    ```
    or raw JSON starting with `{`
    """
    start = raw_str.find("{")
    if start == -1:
        raise ValueError("Malformed raw output: no opening '{' found.")

    json_str = raw_str[start:]
    json_str = re.sub(r"(```(?:json)?\n?)|(```)$", "", json_str, flags=re.MULTILINE).strip()

    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in raw output: {e}") from e
