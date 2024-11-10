from odoo import fields, models

class PosOrder(models.Model):
    _inherit = "pos.order"

    simulation_id = fields.Many2one("pos.simulation", ondelete="set null", copy=False)
