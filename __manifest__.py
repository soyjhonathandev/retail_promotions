# -*- coding: utf-8 -*-
{
    'name': 'Retail Promotions',
    'version': '17.0.1.1.0',
    'summary': 'Sistema completo de gestión de descuentos promocionales para retail',
    'description': """
        Sistema de Promociones para Retail
        ==================================
        
        Características principales:
        * Gestión completa de promociones con vigencia automática
        * Descuentos automáticos en órdenes de venta
        * Asociación flexible de productos y categorías a promociones
        * Validación automática de fechas de vigencia
        * Vista Kanban visual para gestión de promociones
        * Reportes de promociones activas y estadísticas
        * Integración completa con módulo de ventas
        * Aplicación automática de mejores promociones
        
        Funcionalidades avanzadas:
        * Creación y gestión visual de promociones
        * Aplicación automática de descuentos en ventas
        * Control inteligente de vigencia de promociones
        * Vista Kanban con estados visuales
        * Reportes y análisis de promociones
        * Seguridad por roles de usuario
        * Validación de límites de uso
        * Duplicación de promociones
        * Activación/desactivación rápida
        
    """,
    
    'author': 'Jhonathan Saldarriaga',
    'website': 'https://github.com/soyjhonathandev',
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
    
    # Información adicional
    'images': ['static/description/icon.png'],
    'maintainers': ['Jhonathan Saldarriaga'],
    'contributors': ['Jhonathan Saldarriaga'],
    
    # Configuración de actualización
    'pre_init_hook': False,
    'post_init_hook': '_post_init_hook',
    'uninstall_hook': False,
}
