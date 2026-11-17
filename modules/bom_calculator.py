import streamlit as st
import pandas as pd


def calculate_bom(all_components, recommended_components=None):
    recommended_components = recommended_components or []

    st.write(
        "Choose quantities for your project. Recommended components "
        "are included first; you can add other catalog components too."
    )

    budget = st.number_input(
        "Enter your project budget (₹)",
        min_value=0,
        value=3000,
        step=100,
        key="project_budget"
    )

    selected_items = {}

    # Recommended components
    if recommended_components:
        st.subheader("⭐ AI-recommended components")

        for index, component in enumerate(recommended_components):
            name = component.get("name", "Unknown component")
            price = float(component.get("price", 0) or 0)

            quantity = st.number_input(
                f"{name} — ₹{price:.0f} each",
                min_value=0,
                max_value=100,
                value=1,
                step=1,
                key=f"recommended_quantity_{index}_{component.get('id', index)}"
            )

            if quantity > 0:
                selected_items[component.get("id", name)] = {
                    "name": name,
                    "price": price,
                    "quantity": quantity
                }
    else:
        st.info(
            "No catalog recommendations have been detected yet. "
            "You can build a BOM manually below."
        )

    # Manual component selection
    recommended_ids = {
        component.get("id") for component in recommended_components
    }

    with st.expander("➕ Add more components manually"):
        for index, component in enumerate(all_components):
            component_id = component.get("id", str(index))

            if component_id in recommended_ids:
                continue

            name = component.get("name", "Unknown component")
            price = float(component.get("price", 0) or 0)

            quantity = st.number_input(
                f"{name} — ₹{price:.0f} each",
                min_value=0,
                max_value=100,
                value=0,
                step=1,
                key=f"manual_quantity_{component_id}"
            )

            if quantity > 0:
                selected_items[component_id] = {
                    "name": name,
                    "price": price,
                    "quantity": quantity
                }

    # Build BOM
    if selected_items:
        rows = []

        for item in selected_items.values():
            total_price = item["price"] * item["quantity"]

            rows.append({
                "Component": item["name"],
                "Quantity": item["quantity"],
                "Unit Price (₹)": item["price"],
                "Total Price (₹)": total_price
            })

        dataframe = pd.DataFrame(rows)

        total_cost = dataframe["Total Price (₹)"].sum()
        remaining = budget - total_cost

        st.subheader("📋 Your Bill of Materials")
        st.dataframe(dataframe, use_container_width=True, hide_index=True)

        col1, col2 = st.columns(2)

        with col1:
            st.metric("Estimated project cost", f"₹{total_cost:,.2f}")

        with col2:
            st.metric(
                "Budget remaining",
                f"₹{remaining:,.2f}" if remaining >= 0
                else f"₹{abs(remaining):,.2f} over budget"
            )

        if total_cost > budget:
            st.error("Your selected components exceed your budget.")
        elif total_cost == budget:
            st.success("Your selected components use your full budget.")
        else:
            st.success("Your selected components are within your budget.")

        if budget > 0:
            st.progress(min(total_cost / budget, 1.0))

        csv_data = dataframe.to_csv(index=False).encode("utf-8")

        st.download_button(
            label="⬇️ Download BOM as CSV",
            data=csv_data,
            file_name="electromind_project_bom.csv",
            mime="text/csv"
        )

    else:
        st.info("Select at least one component to generate your BOM.")
