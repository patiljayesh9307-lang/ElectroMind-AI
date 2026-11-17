import json
from pathlib import Path


DATABASE_PATH = (
    Path(__file__).resolve().parent.parent
    / "data"
    / "components.json"
)


def get_all_components():
    try:
        with open(DATABASE_PATH, "r", encoding="utf-8") as file:
            data = json.load(file)

        return data.get("components", [])

    except FileNotFoundError:
        return []

    except json.JSONDecodeError:
        return []


def search_components(keyword):
    keyword = keyword.lower()

    return [
        component
        for component in get_all_components()
        if keyword in component.get("name", "").lower()
        or keyword in component.get("category", "").lower()
        or keyword in component.get("description", "").lower()
    ]


def get_component_by_id(component_id):
    for component in get_all_components():
        if component.get("id") == component_id:
            return component

    return None
