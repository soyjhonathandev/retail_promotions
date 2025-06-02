# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError

class ApplyPromotionsWizard(models.TransientModel):
    _name = 'apply.promotions.wizard'
    _description = 'Wizard to Apply Promotions'
    
    # ====================================
    # CAMPOS DEL WIZARD
    # ====================================
    
    sale_order_id = fields.Many2one(
        'sale.order',
        string='Sale Order',
        required=True,
        default=lambda self: self.env.context.get('active_id')
    )
    
    promotion_ids = fields.Many2many(
        'retail.promotion',
        string='Available Promotions',
        domain="[('is_valid', '=', True)]"
    )
    
    apply_mode = fields.Selection([
        ('automatic', 'Automatic Application'),
        ('manual', 'Manual Selection'),
        ('best_discount', 'Best Discount'),
    ], string='Application Mode', default='automatic', required=True)
    
    preview_lines = fields.One2many(
        'promotion.preview.line',
        'wizard_id',
        string='Discount Preview'
    )
    
    total_discounts = fields.Monetary(
        string='Total Discounts',
        compute='_compute_total_discounts',
        currency_field='currency_id'
    )
    
    currency_id = fields.Many2one(
        'res.currency',
        related='sale_order_id.currency_id'
    )
    
    # ====================================
    # MÉTODOS COMPUTADOS
    # ====================================
    
    @api.depends('preview_lines.discount_amount')
    def _compute_total_discounts(self):
        for wizard in self:
            wizard.total_discounts = sum(wizard.preview_lines.mapped('discount_amount'))
    
    @api.onchange('sale_order_id', 'apply_mode')
    def _onchange_sale_order(self):
        """Carga promociones disponibles cuando cambia la orden"""
        if self.sale_order_id:
            # Buscar promociones aplicables
            available_promotions = self._get_available_promotions()
            self.promotion_ids = [(6, 0, available_promotions.ids)]
            
            # Generar vista previa
            self._generate_preview()
    
    # ====================================
    # MÉTODOS DE NEGOCIO
    # ====================================
    
    def _get_available_promotions(self):
        """Obtiene promociones aplicables a los productos de la orden"""
        promotions = self.env['retail.promotion']
        
        for line in self.sale_order_id.order_line:
            if line.product_id:
                line_promotions = self.env['retail.promotion'].search_valid_promotions(
                    product=line.product_id
                )
                promotions |= line_promotions
        
        return promotions
    
    def _generate_preview(self):
        """Genera vista previa de descuentos"""
        preview_lines = []
        
        for line in self.sale_order_id.order_line:
            if not line.product_id:
                continue
            
            # Buscar promociones para este producto
            promotions = self.env['retail.promotion'].search_valid_promotions(
                product=line.product_id
            )
            
            best_promotion = None
            best_discount = 0
            
            for promotion in promotions:
                discount = promotion.calculate_discount(line.price_unit, line.product_uom_qty)
                if discount > best_discount:
                    best_promotion = promotion
                    best_discount = discount
            
            if best_promotion and best_discount > 0:
                preview_lines.append((0, 0, {
                    'wizard_id': self.id,
                    'sale_line_id': line.id,
                    'product_id': line.product_id.id,
                    'promotion_id': best_promotion.id,
                    'original_price': line.price_unit,
                    'quantity': line.product_uom_qty,
                    'discount_amount': best_discount,
                    'final_price': line.price_unit - (best_discount / line.product_uom_qty),
                    'apply': True if self.apply_mode == 'automatic' else False,
                }))
        
        self.preview_lines = [(5, 0, 0)] + preview_lines
    
    def action_apply_promotions(self):
        """Aplica las promociones seleccionadas a la orden de venta"""
        if not self.preview_lines.filtered('apply'):
            raise UserError("You must select at least one promotion to apply.")
        
        # Quitar promociones existentes
        self.sale_order_id.remove_promotions()
        
        # Aplicar nuevas promociones
        for preview_line in self.preview_lines.filtered('apply'):
            sale_line = preview_line.sale_line_id
            promotion = preview_line.promotion_id
            
            try:
                sale_line.apply_promotion(promotion)
            except Exception as e:
                raise UserError(f"Error applying promotion {promotion.name}: {str(e)}")
        
        # Actualizar totales
        self.sale_order_id.apply_automatic_promotions()
        
        return {
            'type': 'ir.actions.act_window_close',
        }
    
    def action_preview_update(self):
        """Actualiza la vista previa"""
        self._generate_preview()
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }


class PromotionPreviewLine(models.TransientModel):
    _name = 'promotion.preview.line'
    _description = 'Promotion Preview Line'
    
    wizard_id = fields.Many2one('apply.promotions.wizard', required=True, ondelete='cascade')
    sale_line_id = fields.Many2one('sale.order.line', 'Sale Line', required=True)
    product_id = fields.Many2one('product.product', 'Product', required=True)
    promotion_id = fields.Many2one('retail.promotion', 'Promotion', required=True)
    
    original_price = fields.Float('Original Price')
    quantity = fields.Float('Quantity')
    discount_amount = fields.Monetary('Discount', currency_field='currency_id')
    final_price = fields.Float('Final Price')
    apply = fields.Boolean('Apply', default=True)
    
    currency_id = fields.Many2one('res.currency', related='wizard_id.currency_id')
    
    # Campos computados para mostrar información
    discount_percentage = fields.Float(
        'Discount %',
        compute='_compute_discount_percentage'
    )
    
    @api.depends('original_price', 'discount_amount', 'quantity')
    def _compute_discount_percentage(self):
        for line in self:
            if line.original_price > 0 and line.quantity > 0:
                subtotal = line.original_price * line.quantity
                line.discount_percentage = (line.discount_amount / subtotal) * 100
            else:
                line.discount_percentage = 0