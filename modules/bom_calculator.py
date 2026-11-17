
import streamlit as st


def calculate_bom(components):
    """
    Display a Bill of Materials and calculate
    the estimated total project cost.
    """

    st.subheader("🧾 Project Bill of Materials")

    if not components:
        st.info("No components available for the BOM.")
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
                "name": name,
                "quantity": quantity,
                "unit_price": price,
                "total": quantity * price
            })

    if bom_items:

        st.divider()
        st.markdown("### Cost Summary")

        grand_total = 0

        for item in bom_items:
            st.write(
                f"**{item['name']}**: "
                f"{item['quantity']} × ₹{item['unit_price']} "
                f"= ₹{item['total']}"
            )

            grand_total += item["total"]

        st.divider()

        st.metric(
            "Estimated Project Cost",
            f"₹{grand_total:,.2f}"
        )

    else:
        st.info("Select quantities above to calculate your BOM.")
