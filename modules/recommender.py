def match_recommendations(recommended_names):
    from modules.component_database import get_all_components

    all_components = get_all_components()

    verified_components = []
    unverified_components = []

    for recommended_name in recommended_names:
        matched = None

        for component in all_components:
            if (
                recommended_name.lower() == component.get("name", "").lower()
                or recommended_name.lower() == component.get("id", "").lower()
            ):
                matched = component
                break

        if matched:
            if matched not in verified_components:
                verified_components.append(matched)
        else:
            if recommended_name not in unverified_components:
                unverified_components.append(recommended_name)

    return {
        "verified_components": verified_components,
        "unverified_components": unverified_components
    }


def get_recommendation_summary(result):
    verified = result.get("verified_components", [])
    unverified = result.get("unverified_components", [])

    return {
        "verified_count": len(verified),
        "unverified_count": len(unverified),
        "verified_components": verified,
        "unverified_components": unverified
    }
