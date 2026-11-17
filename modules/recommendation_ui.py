
import streamlit as st


def display_recommendations(result):
    """Display verified and unverified component recommendations."""

    st.subheader("🔧 Component Recommendations")

    verified = result.get("verified_components", [])
    unverified = result.get("unverified_components", [])

    if verified:
        st.markdown("### ✅ Components found in our database")

        for component in verified:
            with st.container(border=True):
                st.markdown(f"**{component['name']}**")
                st.caption(f"Category: {component['category']}")
                st.write(f"ID: {component['id']}")
                st.write(f"Voltage: {component['voltage']}")
                st.write(
                    "Interfaces: "
                    + ", ".join(component.get("interfaces", []))
                )
                st.write(component["description"])

    if unverified:
        st.markdown("### ⚠️ Components not found in our database")

        for name in unverified:
            st.warning(f"{name} — specifications not verified.")

    if not verified and not unverified:
        st.info("No component recommendations to display.")
