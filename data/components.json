
import json
from pathlib import Path


def load_components():
    """Load electronics components from the JSON database."""

    database_path = (
        Path(__file__).resolve().parent.parent
        / "data"
        / "components.json"
    )

    try:
        with open(database_path, "r", encoding="utf-8") as file:
            data = json.load(file)

        return data.get("components", [])

    except FileNotFoundError:
        return []

    except json.JSONDecodeError:
        return []


def get_all_components():
    """Return all components."""

    return load_components()


def search_components(keyword):
    """Search components by name, category, ID, or description."""

    components = load_components()
    keyword = keyword.strip().lower()

    if not keyword:
        return components

    results = []

    for component in components:
        searchable_text = " ".join([
            component.get("id", ""),
            component.get("name", ""),
            component.get("category", ""),
            component.get("description", "")
        ]).lower()

        if keyword in searchable_text:
            results.append(component)

    return results


def get_component_by_id(component_id):
    """Find a component using its unique ID."""

    for component in load_components():
        if component.get("id", "").lower() == component_id.lower():
            return component

    return None
