# -*- coding: utf-8 -*-

from odoo import models, fields, api

class ProductTemplate(models.Model):
    _inherit = 'product.template'
    
    # ====================================
    # CAMPOS RELACIONADOS CON PROMOCIONES
    # ====================================
    
    promotion_ids = fields.Many2many(
        'retail.promotion',
        'promotion_product_rel',
        'product_id',
        'promotion_id',
        string='Active Promotions',
        compute='_compute_promotions',
        help='Active promotions that include this product'
    )
    
    has_valid_promotion = fields.Boolean(
        string='Has Valid Promotion',
        compute='_compute_promotions',
        help='Indicates if the product has valid promotions'
    )
    
    best_discount = fields.Float(
        string='Best Discount (%)',
        compute='_compute_best_discount',
        help='The best percentage discount available for this product'
    )
    
    promotional_price = fields.Float(
        string='Promotional Price',
        compute='_compute_promotional_price',
        help='Product price applying the best available promotion'
    )
    
    # ====================================
    # MÉTODOS COMPUTADOS
    # ====================================
    
    @api.depends('product_variant_ids')
    def _compute_promotions(self):
        """Calcula las promociones activas para el producto"""
        for template in self:
            promotions = self.env['retail.promotion']
            
            # Buscar promociones por productos específicos
            if template.product_variant_ids:
                for variant in template.product_variant_ids:
                    variant_promotions = self.env['retail.promotion'].search([
                        ('product_ids', 'in', [variant.id]),
                        ('is_valid', '=', True)
                    ])
                    promotions |= variant_promotions
            
            # Buscar promociones por categoría
            if template.categ_id:
                category_promotions = self.env['retail.promotion'].search([
                    ('category_ids', 'in', [template.categ_id.id]),
                    ('is_valid', '=', True)
                ])
                promotions |= category_promotions
                
                # Buscar en categorías padre
                current_category = template.categ_id.parent_id
                while current_category:
                    parent_promotions = self.env['retail.promotion'].search([
                        ('category_ids', 'in', [current_category.id]),
                        ('is_valid', '=', True)
                    ])
                    promotions |= parent_promotions
                    current_category = current_category.parent_id
            
            template.promotion_ids = promotions
            template.has_valid_promotion = bool(promotions)
    
    @api.depends('promotion_ids', 'list_price')
    def _compute_best_discount(self):
        """Calcula el mejor descuento porcentual disponible"""
        for template in self:
            best_discount = 0.0
            
            if template.promotion_ids and template.list_price > 0:
                for promotion in template.promotion_ids:
                    if promotion.discount_type == 'percentage':
                        if promotion.discount > best_discount:
                            best_discount = promotion.discount
                    else:  # descuento fijo
                        discount_percentage = (promotion.fixed_discount / template.list_price) * 100
                        if discount_percentage > best_discount:
                            best_discount = discount_percentage
            
            template.best_discount = best_discount
    
    @api.depends('promotion_ids', 'list_price')
    def _compute_promotional_price(self):
        """Calcula el precio con la mejor promoción aplicada"""
        for template in self:
            promotional_price = template.list_price
            best_discount_amount = 0.0
            
            if template.promotion_ids and template.list_price > 0:
                for promotion in template.promotion_ids:
                    discount = promotion.calculate_discount(template.list_price, 1)
                    if discount > best_discount_amount:
                        best_discount_amount = discount
                
                promotional_price = template.list_price - best_discount_amount
            
            template.promotional_price = max(promotional_price, 0)
    
    # ====================================
    # MÉTODOS DE NEGOCIO
    # ====================================
    
    def get_applicable_promotions(self):
        """Obtiene promociones aplicables al producto"""
        self.ensure_one()
        promotions = self.env['retail.promotion']
        
        # Buscar por variantes específicas
        for variant in self.product_variant_ids:
            promotions |= self.env['retail.promotion'].search_valid_promotions(
                product=variant
            )
        
        return promotions.filtered('is_valid')
    
    def get_best_promotion(self):
        """Obtiene la mejor promoción disponible para el producto"""
        self.ensure_one()
        promotions = self.get_applicable_promotions()
        
        if not promotions:
            return self.env['retail.promotion']
        
        best_promotion = promotions[0]
        best_discount = 0
        
        for promotion in promotions:
            discount = promotion.calculate_discount(self.list_price, 1)
            if discount > best_discount:
                best_promotion = promotion
                best_discount = discount
        
        return best_promotion
    
    def action_view_promotions(self):
        """Acción para ver todas las promociones del producto"""
        self.ensure_one()
        promotions = self.get_applicable_promotions()
        
        return {
            'type': 'ir.actions.act_window',
            'name': f'Promotions for {self.name}',
            'res_model': 'retail.promotion',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', promotions.ids)],
            'context': {'default_product_ids': [(6, 0, self.product_variant_ids.ids)]},
        }


class ProductProduct(models.Model):
    _inherit = 'product.product'
    
    # ====================================
    # CAMPOS ESPECÍFICOS DE VARIANTE
    # ====================================
    
    direct_promotions = fields.Many2many(
        'retail.promotion',
        'promotion_product_rel',
        'product_id',
        'promotion_id',
        string='Direct Promotions',
        help='Promotions that specifically include this variant'
    )
    
    # ====================================
    # MÉTODOS DE VISTA
    # ====================================
    
    def name_get(self):
        """Personaliza el nombre para mostrar si tiene promoción"""
        result = []
        for product in self:
            name = super(ProductProduct, product).name_get()[0][1]
            
            # Verificar si tiene promociones vigentes
            promotions = self.env['retail.promotion'].search_valid_promotions(
                product=product
            )
            
            if promotions:
                best_promotion = promotions[0]
                best_discount = 0
                
                for promotion in promotions:
                    discount = promotion.calculate_discount(product.list_price, 1)
                    if discount > best_discount:
                        best_promotion = promotion
                        best_discount = discount
                
                if best_discount > 0:
                    if best_promotion.discount_type == 'percentage':
                        name += f" (🏷️ -{best_promotion.discount}%)"
                    else:
                        name += f" (🏷️ -{best_promotion.currency_id.symbol}{best_promotion.fixed_discount})"
            
            result.append((product.id, name))
        
        return result


class ProductCategory(models.Model):
    _inherit = 'product.category'
    
    def _get_parent_categories(self):
        """Obtiene todas las categorías padre"""
        categories = self
        current = self.parent_id
        while current:
            categories |= current
            current = current.parent_id
        return categories