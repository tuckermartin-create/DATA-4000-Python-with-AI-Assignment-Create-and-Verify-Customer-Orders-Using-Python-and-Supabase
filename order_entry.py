"""Interactive terminal program for creating and verifying Supabase orders."""

from __future__ import annotations

import os
from datetime import date
from typing import Any, Callable


InputFunction = Callable[[str], str]
OutputFunction = Callable[[str], None]


def find_value(record: dict[str, Any], *names: str) -> Any:
    """Return the first present, non-null value from a record."""
    for name in names:
        if name in record and record[name] is not None:
            return record[name]
    raise ValueError(f"Missing expected field: {' or '.join(names)}")


def customer_name(customer: dict[str, Any]) -> str:
    for name in ("customer_name", "full_name", "name"):
        if customer.get(name):
            return str(customer[name])
    first = customer.get("first_name")
    last = customer.get("last_name")
    if first or last:
        return " ".join(str(part) for part in (first, last) if part)
    raise ValueError("Customer records must include a customer name.")


def customer_id(customer: dict[str, Any]) -> int:
    return int(find_value(customer, "customer_id", "id"))


def product_id(product: dict[str, Any]) -> int:
    return int(find_value(product, "product_id", "id"))


def product_name(product: dict[str, Any]) -> str:
    return str(find_value(product, "product_name", "name"))


def product_price(product: dict[str, Any]) -> float:
    return float(find_value(product, "price", "current_price", "unit_price"))


def fetch_records(client: Any, table_name: str) -> list[dict[str, Any]]:
    response = client.table(table_name).select("*").execute()
    if response.data is None:
        raise RuntimeError(f"No data was returned from the {table_name} table.")
    return response.data


def display_table(headers: list[str], rows: list[list[str]], output_fn: OutputFunction) -> None:
    widths = [
        max(len(header), *(len(row[index]) for row in rows))
        for index, header in enumerate(headers)
    ]
    output_fn(" | ".join(header.ljust(widths[index]) for index, header in enumerate(headers)))
    output_fn("-+-".join("-" * width for width in widths))
    for row in rows:
        output_fn(" | ".join(value.ljust(widths[index]) for index, value in enumerate(row)))


def display_customers(customers: list[dict[str, Any]], output_fn: OutputFunction = print) -> None:
    rows = [[str(customer_id(row)), customer_name(row)] for row in customers]
    output_fn("\nCustomers")
    display_table(["Customer ID", "Customer Name"], rows, output_fn)


def display_products(products: list[dict[str, Any]], output_fn: OutputFunction = print) -> None:
    rows = [
        [str(product_id(row)), product_name(row), f"${product_price(row):.2f}"]
        for row in products
    ]
    output_fn("\nProducts")
    display_table(["Product ID", "Product Name", "Current Price"], rows, output_fn)


def prompt_existing_id(
    label: str,
    records: list[dict[str, Any]],
    get_id: Callable[[dict[str, Any]], int],
    input_fn: InputFunction = input,
    output_fn: OutputFunction = print,
) -> tuple[int, dict[str, Any]]:
    records_by_id = {get_id(record): record for record in records}
    while True:
        answer = input_fn(f"Enter {label} ID: ").strip()
        try:
            selected_id = int(answer)
        except ValueError:
            output_fn(f"{label} ID must be a whole number. Please try again.")
            continue
        if selected_id not in records_by_id:
            output_fn(f"No {label.lower()} with ID {selected_id} exists. Please try again.")
            continue
        return selected_id, records_by_id[selected_id]


def prompt_quantity(
    input_fn: InputFunction = input,
    output_fn: OutputFunction = print,
) -> int:
    while True:
        answer = input_fn("Enter quantity: ").strip()
        try:
            quantity = int(answer)
        except ValueError:
            output_fn("Quantity must be a positive whole number. Please try again.")
            continue
        if quantity <= 0:
            output_fn("Quantity must be greater than zero. Please try again.")
            continue
        return quantity


def prompt_yes_no(
    prompt: str,
    input_fn: InputFunction = input,
    output_fn: OutputFunction = print,
) -> bool:
    while True:
        answer = input_fn(prompt).strip().lower()
        if answer in ("y", "n"):
            return answer == "y"
        output_fn("Please enter Y or N.")


def display_order_summary(
    customer: dict[str, Any],
    product: dict[str, Any],
    quantity: int,
    output_fn: OutputFunction = print,
) -> None:
    price = product_price(product)
    output_fn("\nOrder Summary")
    display_table(
        ["Customer", "Product", "Quantity", "Unit Price", "Order Total"],
        [[
            customer_name(customer),
            product_name(product),
            str(quantity),
            f"${price:.2f}",
            f"${quantity * price:.2f}",
        ]],
        output_fn,
    )


def insert_order(
    client: Any,
    selected_customer_id: int,
    selected_product_id: int,
    quantity: int,
    unit_price: float,
) -> int:
    response = (
        client.table("orders")
        .insert({
            "customer_id": selected_customer_id,
            "product_id": selected_product_id,
            "quantity": quantity,
            "order_date": date.today().isoformat(),
            "unit_price": unit_price,
        })
        .select("order_id")
        .single()
        .execute()
    )
    if not response.data:
        raise RuntimeError("Supabase did not return the generated order ID.")
    return int(find_value(response.data, "order_id", "id"))


def retrieve_order(client: Any, generated_order_id: int) -> dict[str, Any] | None:
    response = (
        client.table("orders")
        .select("*")
        .eq("order_id", generated_order_id)
        .maybe_single()
        .execute()
    )
    return response.data


def display_verified_order(
    order: dict[str, Any],
    customer: dict[str, Any],
    product: dict[str, Any],
    output_fn: OutputFunction = print,
) -> None:
    stored_price = float(find_value(order, "unit_price"))
    quantity = int(find_value(order, "quantity"))
    output_fn("\nVerified Saved Order")
    display_table(
        ["Order ID", "Customer", "Product", "Quantity", "Unit Price", "Total", "Order Date"],
        [[
            str(find_value(order, "order_id", "id")),
            customer_name(customer),
            product_name(product),
            str(quantity),
            f"${stored_price:.2f}",
            f"${stored_price * quantity:.2f}",
            str(find_value(order, "order_date")),
        ]],
        output_fn,
    )


def process_order(
    client: Any,
    customers: list[dict[str, Any]],
    products: list[dict[str, Any]],
    input_fn: InputFunction = input,
    output_fn: OutputFunction = print,
) -> None:
    selected_customer_id, customer = prompt_existing_id(
        "customer", customers, customer_id, input_fn, output_fn
    )
    selected_product_id, product = prompt_existing_id(
        "product", products, product_id, input_fn, output_fn
    )
    quantity = prompt_quantity(input_fn, output_fn)
    display_order_summary(customer, product, quantity, output_fn)

    if not prompt_yes_no("Confirm this order? (Y/N): ", input_fn, output_fn):
        output_fn("Order cancelled. No order was inserted.")
        return

    try:
        generated_order_id = insert_order(
            client,
            selected_customer_id,
            selected_product_id,
            quantity,
            product_price(product),
        )
    except Exception:
        output_fn("Could not save the order. Check the Supabase connection and database settings.")
        return

    output_fn(f"Order {generated_order_id} was saved successfully.")
    try:
        saved_order = retrieve_order(client, generated_order_id)
    except Exception:
        output_fn("The order was saved, but verification could not be completed.")
        return
    if saved_order is None:
        output_fn("The order was saved, but verification could not find the new order.")
        return
    display_verified_order(saved_order, customer, product, output_fn)


def create_supabase_client() -> Any:
    """Create a client from local environment settings without printing credentials."""
    from dotenv import load_dotenv
    from supabase import create_client

    load_dotenv()
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    if not url or not key:
        raise ValueError("Set SUPABASE_URL and SUPABASE_KEY in your .env file.")
    return create_client(url, key)


def main() -> None:
    try:
        client = create_supabase_client()
        customers = fetch_records(client, "customers")
        products = fetch_records(client, "products")
        if not customers or not products:
            print("The database must contain at least one customer and one product.")
            return
        while True:
            display_customers(customers)
            display_products(products)
            process_order(client, customers, products)
            if not prompt_yes_no("\nWould you like to enter another order? (Y/N): "):
                print("Goodbye.")
                return
            customers = fetch_records(client, "customers")
            products = fetch_records(client, "products")
    except Exception:
        print("Could not load the Supabase data. Check your connection, settings, and table access.")


if __name__ == "__main__":
    main()
