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
    
    has_promotions = fields.Boolean(
        string='Has Promotions',
        compute='_compute_has_promotions',
        store=True,
        help='Indicates if this order has applied promotions'
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
    
    @api.depends('applied_promotions')
    def _compute_has_promotions(self):
        for order in self:
            order.has_promotions = bool(order.applied_promotions)
    
    # ====================================
    # MÉTODOS DE NEGOCIO
    # ====================================
    
    def apply_automatic_promotions(self):
        """Aplica automáticamente las promociones vigentes a las líneas de la orden"""
        promotion_applied = False
        for line in self.order_line:
            if line.apply_automatic_promotions():
                promotion_applied = True
        
        # Actualizar promociones aplicadas a nivel de orden
        applied_promotions = self.order_line.mapped('applied_promotion_id').filtered(lambda p: p)
        self.applied_promotions = [(6, 0, applied_promotions.ids)]
        
        if applied_promotions:
            self.message_post(
                body=f"Automatically applied promotions: {', '.join(applied_promotions.mapped('name'))}"
            )
        
        return promotion_applied
    
    def remove_promotions(self):
        """Quita todas las promociones aplicadas a la orden"""
        for line in self.order_line:
            line.remove_promotion()
        self.applied_promotions = [(5, 0, 0)]
        self.message_post(body="All promotions have been removed")
    
    def action_apply_promotions(self):
        """Acción manual para aplicar promociones"""
        self.apply_automatic_promotions()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Promotions Applied',
                'message': 'Promotions have been applied to this order.',
                'type': 'success',
                'sticky': False,
            }
        }
    
    # ====================================
    # HOOKS DE CRUD
    # ====================================
    
    @api.model
    def create(self, vals_list):
        # Si vals_list no es una lista, convertirlo
        if not isinstance(vals_list, list):
            vals_list = [vals_list]
            
        # Llamar al create original
        if len(vals_list) == 1:
            order = super().create(vals_list[0])
            # Aplicar promociones automáticamente después de crear
            if order.order_line:
                order.apply_automatic_promotions()
            return order
        else:
            orders = super().create(vals_list)
            for order in orders:
                if order.order_line:
                    order.apply_automatic_promotions()
            return orders


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
    
    has_promotion = fields.Boolean(
        string='Has Promotion',
        compute='_compute_has_promotion',
        help='Indicates if this line has a promotion applied'
    )
    
    # ====================================
    # MÉTODOS COMPUTADOS
    # ====================================
    
    @api.depends('applied_promotion_id')
    def _compute_has_promotion(self):
        for line in self:
            line.has_promotion = bool(line.applied_promotion_id)
    
    # ====================================
    # MÉTODOS DE NEGOCIO
    # ====================================
    
    def apply_automatic_promotions(self):
        """Busca y aplica automáticamente promociones vigentes para el producto"""
        promotion_applied = False
        
        for line in self:
            if not line.product_id or line.applied_promotion_id:
                continue
            
            # Buscar promociones vigentes para el producto
            promotions = self.env['retail.promotion'].search_valid_promotions(
                product=line.product_id
            )
            
            if promotions:
                # Aplicar la mejor promoción (mayor descuento)
                best_promotion = None
                best_discount = 0
                
                for promotion in promotions:
                    if promotion.is_applicable_to_product(line.product_id):
                        discount = promotion.calculate_discount(line.price_unit, line.product_uom_qty)
                        if discount > best_discount:
                            best_promotion = promotion
                            best_discount = discount
                
                if best_promotion and best_discount > 0:
                    line._apply_promotion_internal(best_promotion)
                    promotion_applied = True
        
        return promotion_applied
    
    def _apply_promotion_internal(self, promotion):
        """Método interno para aplicar promoción sin validaciones adicionales"""
        self.ensure_one()
        
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
            self.price_unit = max(discounted_price, 0)
            
            # Incrementar contador de uso de la promoción
            promotion.increment_usage()
    
    def apply_promotion(self, promotion):
        """Aplica una promoción específica a la línea (método público)"""
        self.ensure_one()
        
        # Verificar que la promoción sea aplicable
        if not promotion.is_applicable_to_product(self.product_id):
            raise UserError(
                f"Promotion '{promotion.name}' is not applicable to product '{self.product_id.name}'"
            )
        
        # Quitar promoción anterior si existe
        if self.applied_promotion_id:
            self.remove_promotion()
        
        # Aplicar nueva promoción
        self._apply_promotion_internal(promotion)
        
        # Log del cambio
        self.order_id.message_post(
            body=f"Promotion '{promotion.name}' applied to {self.product_id.name}. "
                 f"Discount: {self.promotion_discount_amount} {self.currency_id.symbol}"
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
    
    @api.onchange('product_id')
    def _onchange_product_promotions(self):
        """Aplica automáticamente promociones cuando cambia el producto"""
        if self.product_id and self.price_unit > 0:
            # Quitar promoción anterior si existe
            if self.applied_promotion_id:
                self.applied_promotion_id = False
                self.promotion_discount_amount = 0
                self.original_price = 0
            
            # Buscar promociones para el producto
            promotions = self.env['retail.promotion'].search_valid_promotions(
                product=self.product_id
            )
            
            if promotions:
                best_promotion = None
                best_discount = 0
                
                for promotion in promotions:
                    if promotion.is_applicable_to_product(self.product_id):
                        discount = promotion.calculate_discount(self.price_unit, self.product_uom_qty or 1)
                        if discount > best_discount:
                            best_promotion = promotion
                            best_discount = discount
                
                if best_promotion and best_discount > 0:
                    # Preparar campos para mostrar la promoción (sin incrementar uso)
                    self.applied_promotion_id = best_promotion.id
                    self.original_price = self.price_unit
                    self.promotion_discount_amount = best_discount
                    
                    # Calcular nuevo precio
                    discounted_price = self.price_unit - (best_discount / (self.product_uom_qty or 1))
                    self.price_unit = max(discounted_price, 0)
    
    @api.onchange('product_uom_qty')
    def _onchange_quantity_promotions(self):
        """Recalcula promociones cuando cambia la cantidad"""
        if self.applied_promotion_id and self.original_price and self.product_uom_qty > 0:
            promotion = self.applied_promotion_id
            
            # Recalcular descuento
            new_discount = promotion.calculate_discount(self.original_price, self.product_uom_qty)
            self.promotion_discount_amount = new_discount
            
            # Recalcular precio
            if new_discount > 0:
                discounted_price = self.original_price - (new_discount / self.product_uom_qty)
                self.price_unit = max(discounted_price, 0)
            else:
                # Si ya no aplica la promoción, removerla
                self.price_unit = self.original_price
                self.applied_promotion_id = False
                self.promotion_discount_amount = 0
                self.original_price = 0
    
    @api.model
    def create(self, vals_list):
        # Si vals_list no es una lista, convertirlo
        if not isinstance(vals_list, list):
            vals_list = [vals_list]
            
        # Llamar al create original
        if len(vals_list) == 1:
            line = super(SaleOrderLine, self).create(vals_list[0])
            # Solo aplicar promociones si no se está creando desde onchange
            if line.product_id and not self.env.context.get('skip_promotion_auto_apply'):
                line.with_context(skip_promotion_auto_apply=True).apply_automatic_promotions()
            return line
        else:
            lines = super(SaleOrderLine, self).create(vals_list)
            for line in lines:
                if line.product_id and not self.env.context.get('skip_promotion_auto_apply'):
                    line.with_context(skip_promotion_auto_apply=True).apply_automatic_promotions()
            return lines
    
    def write(self, vals):
        result = super().write(vals)
        
        # Si se cambia producto o cantidad, reaplicar promociones
        if ('product_id' in vals or 'product_uom_qty' in vals) and not self.env.context.get('skip_promotion_auto_apply'):
            for line in self:
                if line.product_id:
                    # Quitar promoción actual
                    if line.applied_promotion_id:
                        line.with_context(skip_promotion_auto_apply=True).remove_promotion()
                    # Aplicar nueva promoción
                    line.with_context(skip_promotion_auto_apply=True).apply_automatic_promotions()
        
        return result