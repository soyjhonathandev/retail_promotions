# -*- coding: utf-8 -*-
{
    'name': 'Retail Promotions',
    'version': '17.0.1.0.0',
    'summary': 'Sistema de gestión de descuentos promocionales para retail',
    'description': """
        Sistema de Promociones para Retail
        ==================================
        
        Características principales:
        * Gestión completa de promociones con vigencia
        * Descuentos automáticos en órdenes de venta
        * Asociación flexible de productos a promociones
        * Validación automática de fechas de vigencia
        * Reportes de promociones activas
        * Integración completa con módulo de ventas
        
        Funcionalidades:
        * Creación y gestión de promociones
        * Aplicación automática de descuentos
        * Control de vigencia de promociones
        * Reportes y análisis de promociones
        * Seguridad por roles de usuario
    """,
    
    'author': 'Jhonathan Saldarriaga',
    'category': 'Sales/Sales',
    'license': 'LGPL-3',
    
    'depends': [
        'base',
        'sale',
        'product',
        'stock',
        'web',
    ],
    
    'data': [
        # Seguridad
        'security/promotions_security.xml',
        'security/ir.model.access.csv',
        
        # Datos base
        'data/ir_sequence_data.xml',
        
        # Vistas principales
        'views/promotion_views.xml',
        'views/product_template_views.xml',
        'views/sale_order_views.xml',
        'views/menu_views.xml',
        
        # Datos demo
        'demo/promotion_demo.xml',
    ],
    
    'demo': [
        'demo/promotion_demo.xml',
    ],
    
    'assets': {
        'web.assets_backend': [
            'retail_promotions/static/src/css/promotions.css',
            'retail_promotions/static/src/js/promotion_widget.js',
        ],
    },
    
    'installable': True,
    'application': False,
    'auto_install': False,
}