{
    "name": "POS Simulation",
    "version": "17.0.1.0",
    "summary": "Module to simulate Point of Sales sessions and orders",
    "category": "Point of Sale",
    "author": "Mcimam, Sedari Coffee",
    "depends": ["point_of_sale"],
    "data": [
        "security/ir.model.access.csv",
        "views/pos_simulation_views.xml",
        "views/menu.xml",
    ],
    'icon': 'ci_pos_simulation/static/description/icon.png',
    "license": "LGPL-3",
    "installable": True,
    "application": True,
}
