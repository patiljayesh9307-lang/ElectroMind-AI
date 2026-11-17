
import streamlit as st

from modules.compatibility import check_component_compatibility
from modules.component_database import get_all_components


def display_recommendations(result):

    st.subheader("🔧 Component Recommendations")

    verified = result.get("verified_components", [])
    unverified = result.get("unverified_components", [])

    database = get_all_components()

    # Available controller boards
    controllers = [
        component for component in database
        if component.get("id") in [
            "ESP32-DEVKIT",
            "ARDUINO-UNO",
            "NODEMCU-ESP8266"
        ]
    ]

    controller = None

    if controllers:
        controller_names = [
            component["name"] for component in controllers
        ]

        selected_name = st.selectbox(
            "Choose your controller board",
            controller_names,
            key="compatibility_controller"
        )

        controller = next(
            (
                component for component in controllers
                if component["name"] == selected_name
            ),
            None
        )

    if verified:
        st.markdown("### ✅ Components found in our database")

        for component in verified:

            with st.container(border=True):

                st.markdown(f"**{component['name']}**")
                st.caption(
                    f"Category: {component.get('category', 'Unknown')}"
                )

                st.write(f"ID: {component.get('id', 'Unknown')}")
                st.write(f"Voltage: {component.get('voltage', 'Unknown')}")

                st.write(
                    "Interfaces: "
                    + ", ".join(component.get("interfaces", []))
                )

                st.write(component.get("description", ""))

                if (
                    controller
                    and component.get("id") != controller.get("id")
                ):
                    compatibility = check_component_compatibility(
                        controller,
                        component
                    )

                    st.markdown("**Compatibility screening**")

                    st.info(
                        compatibility["interface_check"]["message"]
                    )

                    st.warning(
                        compatibility["voltage_check"]["message"]
                    )

                    st.caption(compatibility["safety_note"])

    if unverified:
        st.markdown("### ⚠️ Components not found in our database")

        for name in unverified:
            st.warning(
                f"{name} — database specifications not verified."
            )

    if not verified and not unverified:
        st.info("No component recommendations to display.")
