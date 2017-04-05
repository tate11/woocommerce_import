# -*- coding: utf-8 -*-

import base64, requests, logging
from odoo import models, fields, api

import time
from woocommerce import API

_logger = logging.getLogger(__name__)


class woocommerce_import(models.Model):
    _name = 'woocommerce_import.woocommerce_import'

    title = fields.Char(required=True)
    url = fields.Char(required=True)
    consumer_key = fields.Char(required=True)
    consumer_secret = fields.Char(required=True)
    limit = fields.Integer(required=True, default=5000)
    timeout = fields.Integer(required=True, default=60000)

    @api.multi
    def name_get(self):
        result = []
        for item in self:
            result.append((item.id, item.title))
        return result

    def api(self, endpoint):
        try:
            wcapi = API(
                url=self.url,
                consumer_key=self.consumer_key,
                consumer_secret=self.consumer_secret,
                timeout=self.timeout
            )

            result = wcapi.get(endpoint + "?filter[limit]=" + str(self.limit)).json()

            return result

        except ImportError:
            _logger.error('Error retrieving data')
            return {}

    def action_import_product(self):

        products = self.api("products")

        if products:

            self.warehouse = self.env['stock.warehouse'].search([
                ('code', '=', 'WC')
            ])

            if not self.warehouse:
                self.warehouse = self.env['stock.warehouse'].create({
                    'name': 'WooCommerce',
                    'reception_steps': 'one_step',
                    'delivery_steps': 'ship_only',
                    'code': 'WC'})

            for item in products['products']:

                ir_data = self.env['ir.model.data'].search([
                    ('module', '=', 'product.template'),
                    ('name', '=', item['id'])
                ])

                if not ir_data:
                    image = requests.get(item['images'][0]['src'])

                    product = self.env['product.template'].create({
                        'name': item['title'],
                        'list_price': item['regular_price'],
                        'type': 'product',
                        'volume': item['stock_quantity'],
                        'image': base64.b64encode(image.content),
                        'default_code': item['sku'],
                        'description_sale': item['description'],
                        'weight': item['weight']
                    })

                    self.env['ir.model.data'].create({
                        'module': 'product.template',
                        'name': item['id'],
                        'res_id': product.id,
                        'model': 'product.template'
                    })

                    self.existing_inventories = self.env['stock.inventory'].search([])
                    self.existing_quants = self.env['stock.quant'].search([])

                    inventory_wizard = self.env['stock.change.product.qty'].create({
                        'product_id': product.id,
                        'new_quantity': float(item['stock_quantity']),
                        'location_id': self.warehouse.lot_stock_id.id,
                    })
                    inventory_wizard.change_product_qty()
        else:
            _logger.debug('Error retrieving data')

    def action_import_customers(self):
        customers = self.api("customers")

        if customers:
            for item in customers['customers']:
                ir_data = self.env['ir.model.data'].search([
                    ('module', '=', 'res.partner'),
                    ('name', '=', item['id'])
                ])

                if not ir_data:
                    customers = self.env['res.partner'].create({
                        'name': item['first_name'],
                        'email': item['email'],
                        'phone': item['billing_address']['phone'],
                        'street': item['billing_address']['address_1'],
                        'street2': item['billing_address']['address_2'],
                        'city': item['billing_address']['city'],
                        'zip': item['billing_address']['postcode'],
                    })

                    self.env['ir.model.data'].create({
                        'module': 'res.partner',
                        'name': item['id'],
                        'res_id': customers.id,
                        'model': 'res.partner'
                    })
        else:
            _logger.debug('Error retrieving data')

    def action_import_orders(self):
        orders = self.api("orders")

        if orders:
            for item in orders['orders']:
                ir_data = self.env['ir.model.data'].search([
                    ('module', '=', 'sale.order'),
                    ('name', '=', item['id'])
                ])

                if not ir_data:
                    customer_data = self.env['ir.model.data'].search([
                        ('module', '=', 'res.partner'),
                        ('name', '=', item['customer_id'])
                    ])

                    orders = self.env['sale.order'].create({
                        'partner_id': customer_data.res_id,
                    })

                    self.env['ir.model.data'].create({
                        'module': 'sale.order',
                        'name': item['id'],
                        'res_id': orders.id,
                        'model': 'sale.order'
                    })

                    for product in item['line_items']:
                        product_data = self.env['ir.model.data'].search([
                            ('module', '=', 'product.template'),
                            ('name', '=', product['product_id'])
                        ])

                        self.env['sale.order.line'].create({
                            'product_id': product_data.res_id,
                            'product_uom_qty': product['quantity'],
                            'order_id': orders.id,
                            'state': 'sale'
                        })

    def action_import_pos(self):
        orders = self.api("orders")

        if orders:
            for item in orders['orders']:
                ir_data = self.env['ir.model.data'].search([
                    ('module', '=', 'pos.order'),
                    ('name', '=', item['id'])
                ])

                if not ir_data:
                    customer_data = self.env['ir.model.data'].search([
                        ('module', '=', 'res.partner'),
                        ('name', '=', item['customer_id'])
                    ])

                    pos_config = self.env['pos.config'].search([
                        ('name', '=', item['pos'])
                    ])

                    pos = self.env['pos.session'].search([
                        ('start_at', '<=', item['created_at'][0:10]),
                        ('start_at', '>=', item['created_at'][0:10])
                    ])

                    if not pos:
                        pos = self.env['pos.session'].create({
                            'name': 'WooPos',
                            'config_id': 1
                        })

                    orders = self.env['pos.order'].create({
                        'partner_id': customer_data.res_id,
                        'pricelist_id': 1,
                        'session_id': pos[0].id
                    })

                    self.env['ir.model.data'].create({
                        'module': 'pos.order',
                        'name': item['id'],
                        'res_id': orders.id,
                        'model': 'pos.order'
                    })

                    for product in item['line_items']:
                        product_data = self.env['ir.model.data'].search([
                            ('module', '=', 'product.template'),
                            ('name', '=', product['product_id'])
                        ])

                        self.env['pos.order.line'].create({
                            'product_id': product_data.res_id,
                            'qty': product['quantity'],
                            'order_id': orders.id,
                            'state': 'sale',
                            'price_unit': product['subtotal']
                        })
