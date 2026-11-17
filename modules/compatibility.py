
def check_voltage_compatibility(
    controller_voltage,
    component_voltage
):
    """
    Basic voltage-range comparison.
    Returns a warning when voltage information is unknown.
    """

    if not controller_voltage or not component_voltage:
        return {
            "status": "unknown",
            "message": "Voltage information is incomplete."
        }

    return {
        "status": "review_required",
        "message": (
            "Voltage values need datasheet verification. "
            "A matching voltage value alone does not prove compatibility."
        )
    }


def check_interface_compatibility(
    controller_interfaces,
    component_interfaces
):
    """
    Check whether two components share a listed interface.
    """

    if not controller_interfaces or not component_interfaces:
        return {
            "status": "unknown",
            "message": "Interface information is incomplete."
        }

    common_interfaces = [
        interface
        for interface in controller_interfaces
        if interface in component_interfaces
    ]

    if common_interfaces:
        return {
            "status": "possible_match",
            "interfaces": common_interfaces,
            "message": (
                "A common interface was found. "
                "Pin mapping and electrical levels still need checking."
            )
        }

    return {
        "status": "no_match",
        "interfaces": [],
        "message": "No common interface was found in the database."
    }


def check_component_compatibility(
    controller,
    component
):
    """
    Perform basic database-based compatibility screening.
    This is not a substitute for datasheet verification.
    """

    voltage_result = check_voltage_compatibility(
        controller.get("voltage"),
        component.get("voltage")
    )

    interface_result = check_interface_compatibility(
        controller.get("interfaces", []),
        component.get("interfaces", [])
    )

    return {
        "controller": controller.get("name", "Unknown"),
        "component": component.get("name", "Unknown"),
        "voltage_check": voltage_result,
        "interface_check": interface_result,
        "overall_status": "review_required",
        "safety_note": (
            "This is preliminary screening only. "
            "Verify supply voltage, logic levels, current limits, "
            "pin assignments and datasheets before connecting hardware."
        )
    }
