import unittest
from types import SimpleNamespace

import order_entry


CUSTOMERS = [
    {"customer_id": 1, "customer_name": "Avery Adams"},
    {"customer_id": 2, "customer_name": "Jordan Lee"},
]
PRODUCTS = [{"product_id": 10, "product_name": "Notebook", "price": 4.5}]


class FakeQuery:
    def __init__(self, client, table):
        self.client = client
        self.table_name = table
        self.payload = None
        self.selected = None
        self.order_id = None

    def select(self, fields):
        self.selected = fields
        return self

    def insert(self, payload):
        self.payload = payload
        return self

    def single(self):
        return self

    def maybe_single(self):
        return self

    def eq(self, field, value):
        self.order_id = value
        return self

    def execute(self):
        self.client.calls.append((self.table_name, self.payload, self.order_id))
        if self.table_name == "orders" and self.payload is not None:
            saved = dict(self.payload, order_id=42)
            self.client.orders[42] = saved
            return SimpleNamespace(data={"order_id": 42})
        if self.table_name == "orders":
            if self.client.hide_verified_orders:
                return SimpleNamespace(data=None)
            return SimpleNamespace(data=self.client.orders.get(self.order_id))
        return SimpleNamespace(data=[])


class FakeClient:
    def __init__(self):
        self.orders = {}
        self.calls = []
        self.hide_verified_orders = False

    def table(self, table_name):
        return FakeQuery(self, table_name)


class OrderEntryTests(unittest.TestCase):
    def input_sequence(self, answers):
        iterator = iter(answers)
        return lambda _prompt: next(iterator)

    def test_text_and_unknown_customer_are_reprompted(self):
        messages = []
        selected_id, _ = order_entry.prompt_existing_id(
            "customer", CUSTOMERS, order_entry.customer_id,
            self.input_sequence(["hello", "99", "1"]), messages.append,
        )
        self.assertEqual(selected_id, 1)
        self.assertEqual(len(messages), 2)

    def test_unknown_product_is_reprompted(self):
        messages = []
        selected_id, _ = order_entry.prompt_existing_id(
            "product", PRODUCTS, order_entry.product_id,
            self.input_sequence(["999", "10"]), messages.append,
        )
        self.assertEqual(selected_id, 10)
        self.assertEqual(len(messages), 1)

    def test_invalid_quantities_are_reprompted(self):
        messages = []
        quantity = order_entry.prompt_quantity(
            self.input_sequence(["0", "-2", "1.5", "hello", "3"]),
            messages.append,
        )
        self.assertEqual(quantity, 3)
        self.assertEqual(len(messages), 4)

    def test_confirmation_reprompts_and_accepts_lowercase(self):
        messages = []
        confirmed = order_entry.prompt_yes_no(
            "Confirm? ", self.input_sequence(["maybe", "y"]), messages.append
        )
        self.assertTrue(confirmed)
        self.assertEqual(messages, ["Please enter Y or N."])

    def test_cancel_does_not_insert(self):
        client = FakeClient()
        messages = []
        order_entry.process_order(
            client,
            CUSTOMERS,
            PRODUCTS,
            self.input_sequence(["1", "10", "2", "n"]),
            messages.append,
        )
        self.assertEqual(client.orders, {})
        self.assertIn("Order cancelled. No order was inserted.", messages)

    def test_confirmed_order_is_inserted_then_queried_again(self):
        client = FakeClient()
        messages = []
        order_entry.process_order(
            client,
            CUSTOMERS,
            PRODUCTS,
            self.input_sequence(["1", "10", "2", "Y"]),
            messages.append,
        )
        self.assertEqual(len(client.orders), 1)
        self.assertEqual(
            [call[0] for call in client.calls if call[0] == "orders"],
            ["orders", "orders"],
        )
        self.assertTrue(any("Verified Saved Order" in message for message in messages))
        self.assertTrue(any("$9.00" in message for message in messages))

    def test_missing_verification_result_is_reported_without_reinsert(self):
        client = FakeClient()
        client.hide_verified_orders = True
        messages = []
        order_entry.process_order(
            client,
            CUSTOMERS,
            PRODUCTS,
            self.input_sequence(["1", "10", "2", "Y"]),
            messages.append,
        )
        self.assertTrue(any("verification could not find" in message for message in messages))
        self.assertEqual(len(client.orders), 1)
        self.assertEqual(
            [call[0] for call in client.calls if call[0] == "orders"],
            ["orders", "orders"],
        )


if __name__ == "__main__":
    unittest.main()
