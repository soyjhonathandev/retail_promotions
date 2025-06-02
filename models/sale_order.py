# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError

class SaleOrder(models.Model):
    _inherit = 'sale.order'
    
    # ====================================
    # CAMPOS RELACIONADOS CON PROMOCIONES
    # ====================================
    
    applied_promotions = fields.Many2many(
        'retail.promotion',
        'sale_order_promotion_rel',
        'order_id',
        'promotion_id',
        string='Applied Promotions',
        readonly=True,
        help='Promotions that have been applied to this order'
    )
    
    total_promotion_discounts = fields.Monetary(
        string='Total Promotion Discounts',
        compute='_compute_total_promotion_discounts',
        store=True,
        currency_field='currency_id',
        help='Total sum of discounts applied by promotions'
    )
    
    # ====================================
    # MÉTODOS COMPUTADOS
    # ====================================
    
    @api.depends('order_line.promotion_discount_amount')
    def _compute_total_promotion_discounts(self):
        for order in self:
            order.total_promotion_discounts = sum(
                line.promotion_discount_amount for line in order.order_line
            )
    
    # ====================================
    # MÉTODOS DE NEGOCIO
    # ====================================
    
    def apply_automatic_promotions(self):
        """Aplica automáticamente las promociones vigentes a las líneas de la orden"""
        for line in self.order_line:
            line.apply_automatic_promotions()
        
        # Actualizar promociones aplicadas a nivel de orden
        applied_promotions = self.order_line.mapped('applied_promotion_id').filtered(lambda p: p)
        self.applied_promotions = [(6, 0, applied_promotions.ids)]
        
        if applied_promotions:
            self.message_post(
                body=f"Automatically applied promotions: {', '.join(applied_promotions.mapped('name'))}"
            )
    
    def remove_promotions(self):
        """Quita todas las promociones aplicadas a la orden"""
        for line in self.order_line:
            line.remove_promotion()
        self.applied_promotions = [(5, 0, 0)]
        self.message_post(body="All promotions have been removed")
    
    # ====================================
    # HOOKS DE CRUD
    # ====================================
    
    @api.model
    def create(self, vals):
        order = super().create(vals)
        # Aplicar promociones automáticamente al crear
        if order.order_line:
            order.apply_automatic_promotions()
        return order


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'
    
    # ====================================
    # CAMPOS DE PROMOCIONES
    # ====================================
    
    applied_promotion_id = fields.Many2one(
        'retail.promotion',
        string='Applied Promotion',
        help='Promotion applied to this line'
    )
    
    promotion_discount_amount = fields.Monetary(
        string='Promotion Discount',
        currency_field='currency_id',
        help='Discount amount applied by promotion'
    )
    
    original_price = fields.Float(
        string='Original Price',
        help='Original price before applying promotion'
    )
    
    # ====================================
    # MÉTODOS DE NEGOCIO
    # ====================================
    
    def apply_automatic_promotions(self):
        """Busca y aplica automáticamente promociones vigentes para el producto"""
        for line in self:
            if not line.product_id:
                continue
            
            # Buscar promociones vigentes para el producto
            promotions = self.env['retail.promotion'].search_valid_promotions(
                product=line.product_id
            )
            
            if promotions:
                # Aplicar la mejor promoción (mayor descuento)
                best_promotion = promotions[0]
                best_discount = 0
                
                for promotion in promotions:
                    discount = promotion.calculate_discount(line.price_unit, line.product_uom_qty)
                    if discount > best_discount:
                        best_promotion = promotion
                        best_discount = discount
                
                if best_discount > 0:
                    line.apply_promotion(best_promotion)
    
    def apply_promotion(self, promotion):
        """Aplica una promoción específica a la línea"""
        self.ensure_one()
        
        # Verificar que la promoción sea aplicable
        if not promotion.is_applicable_to_product(self.product_id):
            raise UserError(
                f"Promotion '{promotion.name}' is not applicable to product '{self.product_id.name}'"
            )
        
        # Guardar precio original si no está guardado
        if not self.original_price:
            self.original_price = self.price_unit
        
        # Calcular descuento
        discount = promotion.calculate_discount(self.price_unit, self.product_uom_qty)
        
        if discount > 0:
            # Aplicar descuento
            self.applied_promotion_id = promotion.id
            self.promotion_discount_amount = discount
            
            # Calcular nuevo precio con descuento
            discounted_price = self.price_unit - (discount / self.product_uom_qty)
            self.price_unit = max(discounted_price, 0)  # No puede ser negativo
            
            # Incrementar contador de uso de la promoción
            promotion.increment_usage()
            
            # Log del cambio
            self.order_id.message_post(
                body=f"Promotion '{promotion.name}' applied to {self.product_id.name}. "
                     f"Discount: {discount} {self.currency_id.symbol}"
            )
    
    def remove_promotion(self):
        """Quita la promoción aplicada y restaura el precio original"""
        for line in self:
            if line.applied_promotion_id:
                # Restaurar precio original
                if line.original_price:
                    line.price_unit = line.original_price
                
                # Log del cambio
                promotion_name = line.applied_promotion_id.name
                
                # Limpiar campos de promoción
                line.applied_promotion_id = False
                line.promotion_discount_amount = 0
                line.original_price = 0
                
                line.order_id.message_post(
                    body=f"Promotion '{promotion_name}' removed from {line.product_id.name}"
                )
    
    # ====================================
    # HOOKS DE CAMBIOS
    # ====================================
    
    @api.onchange('product_id', 'product_uom_qty')
    def _onchange_product_promotions(self):
        """Aplica automáticamente promociones cuando cambia el producto o cantidad"""
        if self.product_id and self.product_uom_qty > 0:
            # Quitar promoción anterior si existe
            if self.applied_promotion_id:
                self.remove_promotion()
            
            # Buscar nuevas promociones
            promotions = self.env['retail.promotion'].search_valid_promotions(
                product=self.product_id
            )
            
            if promotions and self.price_unit > 0:
                # Aplicar la mejor promoción automáticamente
                best_promotion = promotions[0]
                best_discount = 0
                
                for promotion in promotions:
                    discount = promotion.calculate_discount(self.price_unit, self.product_uom_qty)
                    if discount > best_discount:
                        best_promotion = promotion
                        best_discount = discount
                
                if best_discount > 0:
                    # Preparar campos para aplicar promoción (sin incrementar uso aún)
                    self.applied_promotion_id = best_promotion.id
                    self.original_price = self.price_unit
                    self.promotion_discount_amount = best_discount
                    
                    # Calcular nuevo precio
                    discounted_price = self.price_unit - (best_discount / self.product_uom_qty)
                    self.price_unit = max(discounted_price, 0)
    
    @api.model
    def create(self, vals):
        line = super().create(vals)
        # Solo aplicar promociones si no se está creando desde onchange
        if line.product_id and not self.env.context.get('skip_promotion_auto_apply'):
            line.apply_automatic_promotions()
        return line
    
    def write(self, vals):
        # Si se cambia el producto, reaplicar promociones
        if 'product_id' in vals or 'product_uom_qty' in vals:
            for line in self:
                if line.applied_promotion_id:
                    line.remove_promotion()
        
        result = super().write(vals)
        
        # Reaplicar promociones después del cambio
        if 'product_id' in vals or 'product_uom_qty' in vals:
            for line in self:
                line.apply_automatic_promotions()
        
        return result