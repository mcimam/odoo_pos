
import logging
import random
from itertools import permutations, combinations

from odoo import models, fields

_logger = logging.getLogger(__name__)

class POSSimulationProduct(models.Model):
    """ This model list all product use in simulation
    """
    _name = "pos.simulation.product"
    _description = "POS Simulation Product List"

    simulation_id = fields.Many2one("pos.simulation", string="Simulation")
    category_ids = fields.Many2many("product.category", string="Category", help="Category from which the product is used. Only available if product is empty.")
    product_ids = fields.Many2many("product.template", string="Product", help="Use these product in simulation")
    random_type = fields.Selection([
        ("permutation", "Permutation"),
        ("combination", "Combination")
    ], help="Select which random combination it will generate. Only available if product is empty")

    max_product = fields.Integer(help="Max product in one order")

    def get_product_list(self, item_number):
        """
               Create combination and permutation of existing list
               if product_ids is not listed
               otherwise return product_ids
        """
        # Compile all product list
        if self.product_ids:
            products = self.env['product.product'].search([('product_tmpl_id', 'in', self.product_ids.ids)])
        else:
            products = self.env['product.product'].search([('categ_id', 'in', self.category_ids.ids)], limit=self.max_product)

        if len(products) < item_number:
            item_number = len(products)
            _logger.warning("Product is less than item number")

        rops = combinations if self.random_type == 'combination' else permutations
        product_combination = random.choice(list(rops(products, item_number)))
        return product_combination
