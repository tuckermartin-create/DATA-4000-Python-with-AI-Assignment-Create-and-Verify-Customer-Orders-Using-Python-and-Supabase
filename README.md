# Create and Verify Customer Orders

Terminal-based Python assignment for creating one-product orders in Supabase.
This is not a web application.

## Setup

1. Install Python 3.10 or newer.
2. From this directory, create and activate a virtual environment if desired:

   ```sh
   python -m venv .venv
   source .venv/bin/activate
   ```

3. Install the dependencies:

   ```sh
   python -m pip install -r requirements.txt
   ```

4. Copy `.env.example` to `.env` and set `SUPABASE_URL` and `SUPABASE_KEY`
   using the Supabase project settings supplied for the course. Do not commit
   `.env` or use a service-role key in a submitted screenshot.
5. Confirm the Supabase project has accessible `customers`, `products`, and
   `orders` tables. The script expects integer customer and product IDs,
   customer names, product names and prices, plus the order columns
   `order_id`, `customer_id`, `product_id`, `quantity`, `order_date`, and
   `unit_price`. Supported customer-name fields are `customer_name`,
   `full_name`, `name`, or `first_name`/`last_name`; product names may be
   `product_name` or `name`, and price fields may be `price`,
   `current_price`, or `unit_price`.

## Run

```sh
python order_entry.py
```

The program fetches customers and products from Supabase, validates each
integer input against those records, validates a positive whole-number
quantity, and asks for confirmation. A confirmed order is submitted through
the Supabase Python client with today's date and the selected product's
database price. The generated order ID is then used in a separate query. The
verification table uses the retrieved row's stored unit price to compute its
total. A cancelled order is not inserted. API error messages are deliberately
generic so database credentials or raw response details are not printed.

The script supports entering multiple orders; reference data is fetched again
between orders so changes to the database are reflected.

## Testing

Run the offline unit tests (no database credentials are needed):

```sh
python -m unittest -v
```

The tests cover non-integer and unknown customer IDs, unknown product IDs,
zero/negative/decimal/text quantities, confirmation reprompting, cancellation
without insertion, insertion followed by a separate verification query, and a
missing verification result. Verified locally with `python3 -m unittest -v`:
**7 tests passed**. Python syntax compilation also passed with
`python3 -m py_compile order_entry.py test_order_entry.py`.

The tests use a fake Supabase client and therefore do not demonstrate a real
database insertion. After configuring `.env`, run the program against the
course database, confirm one order, and save sanitized terminal output or a
screenshot showing the success message and **Verified Saved Order** table here
before submission. Do not include `.env`, API keys, or other credentials.

## Dependencies and references

- `supabase`: official Python client used to query and insert database rows.
- `python-dotenv`: loads local `.env` settings for terminal execution.

References: [Supabase Python client](https://supabase.com/docs/reference/python/introduction)
and [python-dotenv](https://github.com/theskumar/python-dotenv).
