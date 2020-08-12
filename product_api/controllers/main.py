# -*- coding: utf-8 -*-

import re
import json
import logging
import werkzeug

from odoo.http import request, route, Controller
from odoo import fields, _

_logger = logging.getLogger(__name__)


class Authonticate(Controller):

    def _authenticate(self, **kwargs):
        """Method to Check Authorization"""

        headers = request.httprequest.headers
        if headers.has_key('Authorization') and headers.get('Authorization') == "AAAAE2VjZHNhLXNo":
            resp = {
                'success': True,
                'responseCode': 200
            }
        else:
            resp = {
                'success': False,
                'responseCode': 401,
                'message': _("Authorization Failed")
            }
        return resp


class ProductApi(Controller):

    @route('/v1/products', csrf=False, type='http', auth="none")
    def getProducts(self, **kwargs):
        "Get Product List"
        data = json.loads(request.httprequest.data)
        response = Authonticate._authenticate(data)
        if response.get('success') and request.httprequest.method == "GET":
            product_ids = request.env['product.template'].sudo().search([], order="id")
            products = []
            for product in product_ids:
                products.append({
                    'id': product.id,
                    'name': product.name or '',
                    'salePrice': product.list_price or 0.0,
                    # 'cost': product.standard_price or 0.0,
                    'onHandQty': product.qty_available or 0.0,
                    'category': [{'id': product.categ_id and product.categ_id.id or False,
                                  'name': product.categ_id and product.categ_id.name or ''}]
                })
            response.update({
                'message': _("Product List"),
                'data': {'products': products}
            })

        mime = 'application/json; charset=utf-8'
        body = json.dumps(response)
        headers = [
            ('Content-Type', mime),
            ('Content-Length', len(body))
        ]
        return werkzeug.wrappers.Response(body, headers=headers)

    @route('/v1/product/<int:product_id>', csrf=False, type='http', auth="none")
    def getProductDetail(self, product_id, **kwargs):
        """Get full Detail of product"""
        data = json.loads(request.httprequest.data)
        response = Authonticate._authenticate(data)
        if response.get('success') and request.httprequest.method == "GET":
            Product = request.env['product.template'].sudo().browse(product_id)
            variants = []
            result = {}
            if Product and Product.exists():
                base_url = request.env["ir.config_parameter"].sudo().get_param("web.base.url")
                image = base_url + "/web/image/product.template/" + str(Product.id) + "/image_1920?unique=" + re.sub(
                    '[^\d]', '', fields.Datetime.to_string(Product.write_date))
                result.update({
                    'id': Product.id,
                    'name': Product.name or '',
                    'default_code': Product.default_code or '',
                    'image': image,
                    'type': Product.type,
                    'salePrice': Product.list_price or 0.0,
                    # 'cost': Product._compute_standard_price() or 0.0,
                    'cost': self.compute_standard_price(Product),
                    'onHandQty': Product.qty_available or 0.0,
                    'category': [{'id': Product.categ_id and Product.categ_id.id or False,
                                  'name': Product.categ_id and Product.categ_id.name or ''}],
                })
                if Product.currency_id:
                    result.update({
                        'currency': [{
                            'id': Product.currency_id.id,
                            'name': Product.currency_id.name or '',
                            'symbol': Product.currency_id.symbol or ''}]
                    })
                for variant in Product.attribute_line_ids:
                    variants.append({'id': variant.attribute_id.id,
                                     'name': variant.attribute_id.name or '',
                                     'value_ids': [{'id': val.id, 'name': val.name} for val in variant.value_ids]})
                result.update({'variants': variants})
                response.update({
                    'message': _("Product Detail"),
                    'data': {'product': result}
                })
            else:
                response.update({'success': False,
                                 'responseCode': 404,
                                 'message': _("Product Not Found!!")})

        mime = 'application/json; charset=utf-8'
        body = json.dumps(response)
        headers = [
            ('Content-Type', mime),
            ('Content-Length', len(body))
        ]
        return werkzeug.wrappers.Response(body, headers=headers)

    def compute_standard_price(self, product):
        """ Calculate cost of the product """
        unique_variants = product.filtered(lambda template: len(template.product_variant_ids) == 1)
        standard_price = 0.0
        if product.company_id:
            company_ids = [product.company_id.id]
        else:
            company_ids = request.env['res.company'].sudo().search([], order="id").ids
        for template in unique_variants:
            standard_price = template.product_variant_ids.with_context({'allowed_company_ids': company_ids}).standard_price
        for template in (product - unique_variants):
            standard_price = 0.0

        return standard_price
