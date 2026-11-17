
from modules.component_database import get_all_components


def match_recommendations(recommended_names):
    """
    Match Gemini's suggested component names
    with components stored in our database.
    """

    database = get_all_components()
    matched_components = []
    unverified_components = []

    for recommended_name in recommended_names:
        search_name = recommended_name.strip().lower()

        if not search_name:
            continue

        matches = [
            component
            for component in database
            if search_name == component.get("name", "").lower()
            or search_name == component.get("id", "").lower()
        ]

        if matches:
            matched_components.extend(matches)
        else:
            unverified_components.append(recommended_name)

    return {
        "verified_components": matched_components,
        "unverified_components": unverified_components
    }


def get_recommendation_summary(recommended_names):
    """Create a simple summary of recommendation matching."""

    results = match_recommendations(recommended_names)

    return {
        "total_requested": len(recommended_names),
        "total_verified": len(results["verified_components"]),
        "total_unverified": len(results["unverified_components"]),
        "details": results
    }
