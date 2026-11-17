
import streamlit as st
import pandas as pd


def calculate_bom(components):

    st.subheader("🧾 Project Bill of Materials")

    if not components:
        st.info("No components available.")
        return

    # Budget input
    st.markdown("### 💰 Set Your Project Budget")

    budget = st.number_input(
        "Enter your budget (₹)",
        min_value=0,
        value=3000,
        step=100,
        key="project_budget"
    )

    st.divider()

    # Component selection
    st.markdown("### 🔧 Select Required Components")

    bom_items = []

    for component in components:

        component_id = component.get("id", "")
        name = component.get("name", "Unknown")
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

    # Calculate results
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

        # Budget comparison
        st.markdown("### 📊 Budget Analysis")

        if budget > 0:

            remaining = budget - grand_total

            if remaining >= 0:

                st.success(
                    f"✅ Within Budget! You have ₹{remaining:,.2f} remaining."
                )

            else:

                st.error(
                    f"⚠️ Over Budget! You need ₹{abs(remaining):,.2f} extra."
                )

            st.progress(
                min(grand_total / budget, 1.0)
            )

            st.caption(
                f"Budget used: {(grand_total / budget) * 100:.1f}%"
            )

        else:

            st.warning("Enter a budget greater than ₹0 to compare costs.")

        # Download BOM
        csv_data = bom_df.to_csv(index=False).encode("utf-8")

        st.download_button(
            label="📥 Download BOM as CSV",
            data=csv_data,
            file_name="ElectroMind_Project_BOM.csv",
            mime="text/csv"
        )

    else:

        st.info(
            "Select component quantities to generate your BOM."
        )

