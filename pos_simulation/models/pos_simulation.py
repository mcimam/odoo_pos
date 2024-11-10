import random
import uuid
import logging
import pytz

from datetime import datetime, timedelta
from odoo import models, fields

_logger = logging.getLogger(__name__)

class POSSimulation(models.Model):
    _name = "pos.simulation"
    _description = "POS Simulation"

    name = fields.Char(string="Simulation Name", required=True)
    config_id = fields.Many2one("pos.config", string="Shop", required=True)

    start_date = fields.Date(string="Start Date", required=True)
    end_date = fields.Date(string="End Date", required=True)

    min_items_per_order = fields.Integer(string="Minimum Items per Order", required=True)
    max_items_per_order = fields.Integer(string="Maximum Items per Order", required=True)

    min_daily_revenue = fields.Float(string="Minimum Daily Revenue", required=True)
    opening_cashbox = fields.Float(string="Opening Cashbox Amount", required=True)

    product_ids = fields.One2many("pos.simulation.product", "simulation_id", "Products")
    order_ids = fields.One2many("pos.order", "simulation_id", string="Orders")

    state = fields.Selection([
        ("draft", "Draft"),
        ("done", "Done")
    ], default="draft", required=True, copy=False)

    def _open_session(self, open_time, opening_cashbox=0.0):
        """ Open or select existing open session
        """

        session = self.env["pos.session"].search([
            ("state", "!=", "closed"),
            ("config_id", "=", self.config_id.id)], limit=1)

        if not session:
            session = self.env["pos.session"].create(
                {
                    "config_id": self.config_id.id,
                    "start_at": open_time,
                }
            )

        if session.state == "opened":
            return

        session.load_pos_data()
        cashbox_start = int(session.cash_register_balance_start or opening_cashbox)
        session.set_cashbox_pos(cashbox_start, "")

    def _close_session(self, close_time):
        """ Close POS Session
        """
        session = self.env["pos.session"].search([
            ("state", "=", "opened")
        ], limit=1)

        if not session:
            return

        session.get_closing_control_data()
        session.post_closing_cash_details(session.cash_register_balance_end)
        session.update_closing_control_state_session("")
        session.close_session_from_ui([[1, 0]])

        session.write(
            {
                "stop_at": close_time,
                "state": "closed",
            }
        )

    def _create_order(self, order_time, items_in_order):
        # Mengambil produk yang tersedia di POS

        order_lines = []

        total_amount = 0
        total_tax = 0
        for product in items_in_order:
            tax_amount = sum(product.taxes_id.mapped(lambda x: x.amount * product.lst_price / 100))
            total_tax += tax_amount
            price_incl_tax = product.lst_price + tax_amount
            total_amount += price_incl_tax
            order_lines.append(
                [
                    0,
                    0,
                    {
                        "uuid": str(uuid.uuid4()),
                        "qty": 1,
                        "price_unit": product.lst_price,
                        "price_subtotal": product.lst_price,
                        "price_subtotal_incl": price_incl_tax,
                        "discount": 0,
                        "product_id": product.id,
                        "tax_ids": [(6, 0, product.taxes_id.ids)],
                        "pack_lot_ids": [],
                        "full_product_name": product.name,
                    },
                ]
            )

        order_name = "Order " + str(uuid.uuid4())

        order_data = {
            "id": str(uuid.uuid4()),
            "data": {
                "name": order_name,
                "amount_paid": total_amount,
                "amount_total": total_amount,
                "amount_tax": total_tax,
                "amount_return": 0,
                "lines": order_lines,
                "statement_ids": [
                    [0, 0,
                        {
                            "name": order_time.strftime("%Y-%m-%d %H:%M:%S"),
                            "payment_method_id": self.env.ref("point_of_sale.payment_method").id,  # Select cash method
                            "amount": total_amount,
                        },
                     ]
                ],
                "pos_session_id": self.env["pos.session"].search([("state", "=", "opened")], limit=1).id,
                "user_id": self.env.user.id,
                "partner_id": False,  # Default partner
                "fiscal_position_id": False,  # Default fiscal position
                "uid": str(uuid.uuid4()),
                "sequence_number": 1,
                "date_order": order_time.strftime("%Y-%m-%d %H:%M:%S"),
                "access_token": str(uuid.uuid4()),
                "ticket_code": order_name.replace("Order ", ""),
            },
            "to_invoice": False,
        }

        # Create order with `create_from_ui` function
        order_ids = self.env["pos.order"].create_from_ui([order_data])
        order_ids = list(map(lambda x: x["id"], order_ids))
        orders = self.env["pos.order"].browse(order_ids)

        for order in orders:
            order.simulation_id = self.id

        return orders

    def simulate_orders(self):
        user_tz = pytz.timezone(self.env.user.tz) if self.env.user.tz else pytz.UTC
        for simulation in self:
            current_date = simulation.start_date
            while current_date <= simulation.end_date:
                open_time = datetime.combine(current_date, datetime.min.time()) + timedelta(hours=9)
                open_time = (
                    user_tz.localize(open_time)
                    .astimezone(pytz.UTC)
                    .replace(tzinfo=None)
                )
                self._open_session(open_time, simulation.opening_cashbox)

                # Generate orders and revenue
                daily_revenue = 0
                while daily_revenue < simulation.min_daily_revenue:
                    # Orders between 9 AM to 9 PM
                    order_time = open_time + timedelta(minutes=random.randint(0, 720))
                    order_time = order_time.astimezone(user_tz).replace(tzinfo=None)

                    # Choose item number for each order
                    item_number = random.randint(simulation.min_items_per_order, simulation.max_items_per_order)
                    items_in_order = simulation.product_ids.get_product_list(item_number)

                    order = self._create_order(order_time, items_in_order)

                    # Update daily revenue with random amount for simplicity
                    daily_revenue += (sum(order.mapped(lambda x: x.margin)) or 0)

                # Close session at 9 PM in user's timezone
                close_time = datetime.combine(current_date, datetime.min.time()) + timedelta(hours=21)
                close_time = (
                    user_tz.localize(close_time)
                    .astimezone(pytz.UTC)
                    .replace(tzinfo=None)
                )

                self._close_session(close_time)

                # Prepare for next day
                current_date += timedelta(days=1)

        self.state = "done"

    def action_simulate_pos(self):
        self.ensure_one()
        self.simulate_orders()
