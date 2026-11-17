def check_voltage_compatibility(controller, component):
    controller_voltage = str(controller.get("voltage", "")).lower()
    component_voltage = str(component.get("voltage", "")).lower()

    if not controller_voltage or not component_voltage:
        return {
            "status": "unknown",
            "message": "Voltage information is missing. Check both datasheets."
        }

    return {
        "status": "review_required",
        "message": (
            f"Controller voltage information: {controller_voltage}. "
            f"Component voltage information: {component_voltage}. "
            "Verify supply voltage, logic levels and current requirements."
        )
    }


def check_interface_compatibility(controller, component):
    controller_interfaces = controller.get("interfaces", [])
    component_interfaces = component.get("interfaces", [])

    if isinstance(controller_interfaces, str):
        controller_interfaces = [controller_interfaces]

    if isinstance(component_interfaces, str):
        component_interfaces = [component_interfaces]

    shared_interfaces = [
        interface
        for interface in controller_interfaces
        if interface in component_interfaces
    ]

    if shared_interfaces:
        return {
            "status": "possible_match",
            "message": "Shared interface listed: " + ", ".join(shared_interfaces)
        }

    return {
        "status": "no_match",
        "message": (
            "No shared interface was found in the database. "
            "Check whether an adapter or additional circuit is required."
        )
    }


def check_component_compatibility(controller, component):
    voltage_result = check_voltage_compatibility(controller, component)
    interface_result = check_interface_compatibility(controller, component)

    return {
        "status": "review_required",
        "voltage": voltage_result,
        "interface": interface_result,
        "message": (
            "This is a preliminary database check, not an electrical "
            "compatibility or safety certification."
        )
    }
