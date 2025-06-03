# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import datetime, date

class Promotion(models.Model):
    _name = 'retail.promotion'
    _description = 'Product Promotion'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'start_date desc, name'
    _rec_name = 'name'
    
    # ====================================
    # CAMPOS BÁSICOS
    # ====================================
    
    name = fields.Char(
        string='Promotion Name',
        required=True,
        tracking=True,
        help='Descriptive name of the promotion'
    )
    
    code = fields.Char(
        string='Code',
        required=True,
        copy=False,
        tracking=True,
        help='Unique promotion code'
    )
    
    active = fields.Boolean(
        string='Active',
        default=True,
        tracking=True,
        help='If checked, the promotion can be applied'
    )
    
    description = fields.Text(
        string='Description',
        help='Detailed description of the promotion'
    )
    
    # ====================================
    # CAMPOS DE DESCUENTO
    # ====================================
    
    discount_type = fields.Selection([
        ('percentage', 'Percentage'),
        ('fixed', 'Fixed Amount'),
    ], string='Discount Type', required=True, default='percentage', tracking=True)
    
    discount = fields.Float(
        string='Discount (%)',
        digits=(5, 2),
        tracking=True,
        help='Percentage discount to apply (0-100)'
    )
    
    fixed_discount = fields.Monetary(
        string='Fixed Discount',
        currency_field='currency_id',
        tracking=True,
        help='Fixed discount amount to apply'
    )
    
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id,
        required=True
    )
    
    # ====================================
    # CAMPOS DE VIGENCIA
    # ====================================
    
    start_date = fields.Date(
        string='Start Date',
        required=True,
        default=fields.Date.today,
        tracking=True,
        help='Promotion validity start date'
    )
    
    end_date = fields.Date(
        string='End Date',
        required=True,
        tracking=True,
        help='Promotion validity end date'
    )
    
    # ====================================
    # CAMPOS COMPUTADOS
    # ====================================
    
    is_valid = fields.Boolean(
        string='Valid',
        compute='_compute_is_valid',
        store=True,
        help='Indicates if the promotion is currently valid'
    )
    
    days_remaining = fields.Integer(
        string='Days Remaining',
        compute='_compute_days_remaining',
        store=True,
        help='Days remaining until promotion expires'
    )
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('expired', 'Expired'),
        ('cancelled', 'Cancelled'),
    ], string='State', compute='_compute_state', store=True, tracking=True)
    
    # ====================================
    # RELACIONES
    # ====================================
    
    product_ids = fields.Many2many(
        'product.product',
        'promotion_product_rel',
        'promotion_id',
        'product_id',
        string='Products in Promotion',
        help='Products to which this promotion applies'
    )
    
    category_ids = fields.Many2many(
        'product.category',
        'promotion_category_rel',
        'promotion_id',
        'category_id',
        string='Categories in Promotion',
        help='Product categories included in the promotion'
    )
    
    # ====================================
    # CAMPOS DE CONTROL
    # ====================================
    
    usage_limit = fields.Integer(
        string='Usage Limit',
        default=0,
        help='Maximum number of times the promotion can be used (0 = no limit)'
    )
    
    current_usage = fields.Integer(
        string='Current Usage',
        default=0,
        help='Number of times the promotion has been used'
    )
    
    customer_limit = fields.Integer(
        string='Customer Limit',
        default=0,
        help='Maximum number of times a customer can use the promotion (0 = no limit)'
    )
    
    minimum_amount = fields.Monetary(
        string='Minimum Purchase Amount',
        currency_field='currency_id',
        default=0.0,
        help='Minimum purchase amount to apply the promotion'
    )
    
    # ====================================
    # MÉTODOS COMPUTADOS
    # ====================================
    
    @api.depends('start_date', 'end_date', 'active')
    def _compute_is_valid(self):
        today = fields.Date.today()
        for promotion in self:
            promotion.is_valid = (
                promotion.active and
                promotion.start_date and
                promotion.end_date and
                promotion.start_date <= today <= promotion.end_date
            )
    
    @api.depends('end_date')
    def _compute_days_remaining(self):
        today = fields.Date.today()
        for promotion in self:
            if promotion.end_date:
                delta = promotion.end_date - today
                promotion.days_remaining = delta.days
            else:
                promotion.days_remaining = 0

    @api.depends('active', 'is_valid', 'end_date')
    def _compute_state(self):
        today = fields.Date.today()
        for promotion in self:
            if not promotion.active:
                promotion.state = 'cancelled'
            elif not promotion.end_date:
                # Si no hay fecha de fin, es draft
                promotion.state = 'draft'
            elif promotion.end_date < today:
                promotion.state = 'expired'
            elif promotion.is_valid:
                promotion.state = 'active'
            else:
                promotion.state = 'draft'
    
    # ====================================
    # VALIDACIONES
    # ====================================
    
    @api.constrains('start_date', 'end_date')
    def _check_dates(self):
        for promotion in self:
            if promotion.end_date < promotion.start_date:
                raise ValidationError(
                    "End date cannot be earlier than start date."
                )
    
    @api.constrains('discount')
    def _check_percentage_discount(self):
        for promotion in self:
            if promotion.discount_type == 'percentage':
                if not (0 <= promotion.discount <= 100):
                    raise ValidationError(
                        "Percentage discount must be between 0% and 100%."
                    )
    
    @api.constrains('fixed_discount')
    def _check_fixed_discount(self):
        for promotion in self:
            if promotion.discount_type == 'fixed':
                if promotion.fixed_discount < 0:
                    raise ValidationError(
                        "Fixed discount cannot be negative."
                    )
    
    @api.constrains('code')
    def _check_unique_code(self):
        for promotion in self:
            if promotion.code:
                existing = self.search([
                    ('code', '=', promotion.code),
                    ('id', '!=', promotion.id)
                ])
                if existing:
                    raise ValidationError(
                        f"A promotion with code '{promotion.code}' already exists"
                    )
    
    # ====================================
    # MÉTODOS DE NEGOCIO
    # ====================================
    
    def calculate_discount(self, unit_price, quantity=1):
        """Calcula el monto de descuento a aplicar"""
        self.ensure_one()
        
        if not self.is_valid:
            return 0.0
        
        subtotal = unit_price * quantity
        
        # Verificar monto mínimo
        if self.minimum_amount > 0 and subtotal < self.minimum_amount:
            return 0.0
        
        if self.discount_type == 'percentage':
            discount = subtotal * (self.discount / 100)
        else:  # fixed
            discount = min(self.fixed_discount, subtotal)  # No puede ser mayor al subtotal
        
        return discount
    
    def is_applicable_to_product(self, product):
        """Verifica si la promoción es aplicable a un producto específico"""
        self.ensure_one()
        
        if not self.is_valid:
            return False
        
        # Verificar si el producto está directamente incluido
        if product in self.product_ids:
            return True
        
        # Verificar si la categoría del producto está incluida
        if product.categ_id in self.category_ids:
            return True
        
        # Verificar categorías padre
        current_category = product.categ_id.parent_id
        while current_category:
            if current_category in self.category_ids:
                return True
            current_category = current_category.parent_id
        
        return False
    
    def increment_usage(self):
        """Incrementa el contador de usos de la promoción"""
        self.ensure_one()
        if self.usage_limit > 0 and self.current_usage >= self.usage_limit:
            raise UserError(
                f"Promotion '{self.name}' has reached its usage limit."
            )
        self.current_usage += 1
    
    def action_activate(self):
        """Activa la promoción"""
        self.write({'active': True})
        self.message_post(body="Promotion activated")
    
    def action_deactivate(self):
        """Desactiva la promoción"""
        self.write({'active': False})
        self.message_post(body="Promotion deactivated")
    
    def action_duplicate(self):
        """Duplica la promoción con un nuevo código"""
        self.ensure_one()
        
        # Generar nuevo código
        new_code = f"{self.code}-COPY-{len(self.search([('code', 'like', f'{self.code}-COPY%')]))}"
        
        new_record = self.copy({
            'name': f"{self.name} (Copy)",
            'code': new_code,
            'active': False,
            'current_usage': 0,
        })
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'retail.promotion',
            'res_id': new_record.id,
            'view_mode': 'form',
            'target': 'current',
        }
    
    # ====================================
    # MÉTODOS DE BÚSQUEDA
    # ====================================
    
    @api.model
    def search_valid_promotions(self, product=None, category=None):
        """Busca promociones vigentes para un producto o categoría"""
        domain = [
            ('active', '=', True),
            ('is_valid', '=', True),
        ]
        
        if product:
            domain.extend([
                '|',
                ('product_ids', 'in', [product.id]),
                ('category_ids', 'in', [product.categ_id.id])
            ])
        
        if category:
            domain.append(('category_ids', 'in', [category.id]))
        
        return self.search(domain)
    
    # ====================================
    # HOOKS DE CRUD
    # ====================================
    
    @api.model
    def create(self, vals):
        # Generar código automático si no se proporciona
        if not vals.get('code'):
            vals['code'] = self.env['ir.sequence'].next_by_code('retail.promotion') or 'PROMO-NEW'
        
        promotion = super().create(vals)
        promotion.message_post(body=f"Promotion '{promotion.name}' created")
        return promotion
    
    def write(self, vals):
        # Log de cambios importantes
        if 'active' in vals:
            for promotion in self:
                state = "activated" if vals['active'] else "deactivated"
                promotion.message_post(body=f"Promotion {state}")
        
        return super().write(vals)
    
    def unlink(self):
        # Verificar que no tenga usos registrados
        for promotion in self:
            if promotion.current_usage > 0:
                raise UserError(
                    f"Cannot delete promotion '{promotion.name}' "
                    f"because it already has {promotion.current_usage} recorded uses."
                )
        
        return super().unlink()
    
    # ====================================
    # MÉTODOS DE VISTA
    # ====================================
    
    def name_get(self):
        """Personaliza cómo se muestra el nombre en relaciones Many2one"""
        result = []
        for promotion in self:
            name = f"[{promotion.code}] {promotion.name}"
            if promotion.discount_type == 'percentage':
                name += f" ({promotion.discount}%)"
            else:
                name += f" ({promotion.fixed_discount} {promotion.currency_id.symbol})"
            result.append((promotion.id, name))
        return result