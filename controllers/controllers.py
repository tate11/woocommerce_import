# -*- coding: utf-8 -*-
from odoo import http

# class WoocommerceImport(http.Controller):
#     @http.route('/woocommerce_import/woocommerce_import/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/woocommerce_import/woocommerce_import/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('woocommerce_import.listing', {
#             'root': '/woocommerce_import/woocommerce_import',
#             'objects': http.request.env['woocommerce_import.woocommerce_import'].search([]),
#         })

#     @http.route('/woocommerce_import/woocommerce_import/objects/<model("woocommerce_import.woocommerce_import"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('woocommerce_import.object', {
#             'object': obj
#         })