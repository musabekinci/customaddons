from openerp import models
from openerp.tools import float_is_zero

class StockMove(models.Model):
    _inherit= 'stock.move'

    def _get_invoice_line_vals(self, cr, uid, move, partner, inv_type, context=None):
        res = super(StockMove, self)._get_invoice_line_vals(cr, uid, move, partner, inv_type, context=context)
        if inv_type in ('out_invoice', 'out_refund') and not move.procurement_id:
            operation_move = move.mapped('linked_move_operation_ids.operation_id.linked_move_operation_ids.move_id').filtered(lambda m:m.product_id.id == move.product_id.id and m.procurement_id.sale_line_id.id)

            try:
                sale_move = operation_move[0]
            except IndexError:
                try:
                    sale_moves = move.picking_id.move_lines.filtered(lambda m:m.product_id.id == move.product_id.id and m.procurement_id.sale_line_id.id and m.id != move.id)
                    sale_move = sale_moves[0]
                except IndexError:
                    pass
                    return res

            sale_line = sale_move.procurement_id.sale_line_id
            res['invoice_line_tax_id'] = [(6, 0, [x.id for x in sale_line.tax_id])]
            res['account_analytic_id'] = sale_line.order_id.project_id and sale_line.order_id.project_id.id or False
            res['discount'] = sale_line.discount
            if move.product_id.id != sale_line.product_id.id:
                precision = self.env['decimal.precision'].precision_get(cr, uid, 'Discount')
                if float_is_zero(sale_line.discount, precision_digits=precision):
                    res['price_unit'] = self.pool['product.pricelist'].price_get(
                        cr, uid, [sale_line.order_id.pricelist_id.id],
                        move.product_id.id, move.product_uom_qty or 1.0,
                        sale_line.order_id.partner_id, context=context)[sale_line.order_id.pricelist_id.id]
                else:
                    res['price_unit'] = move.product_id.lst_price
            else:
                res['price_unit'] = sale_line.price_unit
            uos_coeff = move.product_uom_qty and move.product_uos_qty / move.product_uom_qty or 1.0
            res['price_unit'] = res['price_unit'] / uos_coeff

        return res