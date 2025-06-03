# -*- coding: utf-8 -*-

from . import models

def _post_init_hook(cr, registry):
    """Hook ejecutado después de la instalación del módulo"""
    from odoo import api, SUPERUSER_ID
    
    env = api.Environment(cr, SUPERUSER_ID, {})
    
    # Asignar productos demo a promociones si existen
    try:
        # Buscar promociones demo
        summer_promo = env.ref('retail_promotions.promotion_demo_summer', raise_if_not_found=False)
        fixed_promo = env.ref('retail_promotions.promotion_demo_fixed', raise_if_not_found=False)
        
        # Buscar algunos productos para asignar
        products = env['product.product'].search([('sale_ok', '=', True)], limit=5)
        categories = env['product.category'].search([], limit=3)
        
        if summer_promo and products:
            summer_promo.write({
                'product_ids': [(6, 0, products[:3].ids)],
                'category_ids': [(6, 0, categories[:2].ids)] if categories else []
            })
        
        if fixed_promo and products:
            fixed_promo.write({
                'product_ids': [(6, 0, products[2:].ids)],
                'category_ids': [(6, 0, categories[1:].ids)] if categories else []
            })
            
        # Forzar recálculo de promociones en productos
        if products:
            products._compute_promotions()
            
    except Exception as e:
        # Si falla, no interrumpir la instalación
        import logging
        _logger = logging.getLogger(__name__)
        _logger.warning(f"Could not assign demo products to promotions: {e}")
        pass