
import streamlit as st
import pandas as pd


def calculate_bom(components):

    st.subheader("🧾 Project Bill of Materials")

    if not components:
        st.info("No components available.")
        return

    bom_items = []

    st.write("Enter the quantity required for each component:")

    for component in components:

        component_id = component.get("id", "")
        name = component.get("name", "Unknown component")
        price = component.get("price", 0)

        quantity = st.number_input(
            f"{name} — ₹{price} each",
            min_value=0,
            max_value=100,
            value=0,
            step=1,
            key=f"bom_{component_id}"
        )

        if quantity > 0:

            bom_items.append({
                "Component": name,
                "Quantity": quantity,
                "Unit Price (₹)": price,
                "Total Price (₹)": quantity * price
            })

    if bom_items:

        st.divider()

        st.markdown("### 📋 Your Selected Components")

        bom_df = pd.DataFrame(bom_items)

        st.dataframe(
            bom_df,
            use_container_width=True,
            hide_index=True
        )

        grand_total = bom_df["Total Price (₹)"].sum()

        st.metric(
            "Estimated Project Cost",
            f"₹{grand_total:,.2f}"
        )

        # Download BOM as CSV
        csv_data = bom_df.to_csv(index=False).encode("utf-8")

        st.download_button(
            label="📥 Download BOM as CSV",
            data=csv_data,
            file_name="ElectroMind_Project_BOM.csv",
            mime="text/csv"
        )

    else:

        st.info(
            "Select quantities above to generate your Bill of Materials."
        )
