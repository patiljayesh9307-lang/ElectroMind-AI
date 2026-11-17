import streamlit as st
from modules.compatibility import check_component_compatibility


def display_recommendations(result, all_components):
    verified = result.get("verified_components", [])
    unverified = result.get("unverified_components", [])

    if verified:
        st.subheader("✅ Components found in ElectroMind database")

        for component in verified:
            with st.container(border=True):
                st.markdown(f"**{component.get('name', 'Unknown component')}**")
                st.write(component.get("description", "No description available."))

                col1, col2 = st.columns(2)

                with col1:
                    st.write(f"**Category:** {component.get('category', 'Not listed')}")

                with col2:
                    st.write(f"**Estimated price:** ₹{component.get('price', 0)}")

                st.caption(
                    f"Voltage information: {component.get('voltage', 'Not listed')}"
                )

        st.subheader("🔌 Preliminary compatibility review")

        controllers = [
            component
            for component in all_components
            if component.get("id") in [
                "ESP32-DEVKIT",
                "ARDUINO-UNO",
                "NODEMCU-ESP8266"
            ]
        ]

        if controllers:
            controller_names = [
                component["name"] for component in controllers
            ]

            selected_name = st.selectbox(
                "Choose a controller to compare against:",
                controller_names,
                key="compatibility_controller"
            )

            selected_controller = next(
                component
                for component in controllers
                if component["name"] == selected_name
            )

            for component in verified:
                if component.get("id") == selected_controller.get("id"):
                    continue

                result_check = check_component_compatibility(
                    selected_controller,
                    component
                )

                with st.expander(
                    f"{selected_controller['name']} + {component['name']}"
                ):
                    st.write(
                        "**Interface:**",
                        result_check["interface"]["message"]
                    )
                    st.write(
                        "**Voltage:**",
                        result_check["voltage"]["message"]
                    )
                    st.warning(result_check["message"])

    if unverified:
        st.subheader("⚠️ Components not found in the database")

        for name in unverified:
            st.write(f"• {name}")

        st.caption(
            "These names were mentioned by the AI but were not matched "
            "to a component in the current database."
        )

    if not verified and not unverified:
        st.info(
            "No catalog component names were detected in the latest AI response."
        )
