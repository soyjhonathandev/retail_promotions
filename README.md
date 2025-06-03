# Preguntas y Respuestas de Prueba Técnica - Odoo Development

## ¿Cuáles son los componentes principales de un módulo en Odoo?

Los componentes principales de un módulo en Odoo son:

- **`__manifest__.py`** - Archivo de configuración y metadatos del módulo
- **`models/`** - Modelos de datos y lógica de negocio
- **`views/`** - Interfaces de usuario (XML)
- **`security/`** - Control de acceso y permisos
- **`data/`** - Datos iniciales y configuraciones
- **`static/`** - Archivos web (CSS, JS, imágenes)
- **`wizard/`** - Asistentes para procesos específicos
- **`reports/`** - Reportes y plantillas
- **`controllers/`** - Controladores web y APIs
- **`tests/`** - Tests unitarios

---

## Explica la diferencia entre fields.Char y fields.Text

| Aspecto | `fields.Char` | `fields.Text` |
|---------|---------------|---------------|
| **Longitud máxima** | 255 caracteres (personalizable) | Sin límite práctico |
| **Tipo de BD** | VARCHAR | TEXT/LONGTEXT |
| **Widget por defecto** | `<input type="text">` | `<textarea>` |
| **Indexación** | ✅ Recomendado | ❌ No recomendado |
| **Búsquedas** | ⚡ Muy rápido | 🐌 Más lento |
| **Uso típico** | Nombres, códigos, títulos | Descripciones, comentarios |

### Cuándo usar cada uno:

- **Char**: Nombres, códigos, emails, URLs, datos estructurados cortos
- **Text**: Descripciones largas, comentarios, contenido HTML, documentación

---

## ¿Para qué sirve el archivo __manifest__.py?

El archivo `__manifest__.py` es el core de cualquier módulo en Odoo. Sirve para:

- **Identificar el módulo** - Define nombre, versión, autor
- **Gestionar dependencias** - Lista módulos requeridos
- **Controlar instalación** - Especifica archivos a cargar
- **Configurar assets** - Define CSS, JS y recursos web
- **Establecer metadatos** - Categoría, descripción, licencia

---

## ¿Cómo manejarías el control de inventario en Odoo para una tienda retail?

Para manejar el control de inventario en retail implementaría:

### 1. Estructura Multi-ubicación:
- **Tienda principal** - Piso de venta
- **Trastienda** - Stock de reserva
- **Almacén central** - Distribución

### 2. Productos con Variantes:
- Atributos: talla, color, modelo
- SKUs automáticos
- Matriz de variantes completa

### 3. Reposición Automática:
- Reglas min/max inteligentes
- Órdenes de compra automáticas
- Análisis de demanda histórica

### 4. Integración POS:
- Stock en tiempo real
- Reservas automáticas

### 5. Control de Calidad:
- Trazabilidad por lotes/series
- Control de perdidas

### 6. Reportes Avanzados:
- Rotación de inventario
- Análisis ABC
- Productos de lento movimiento

---

## ¿Qué módulos de Odoo consideras esenciales para una tienda retail?

### MÓDULOS INDISPENSABLES (Instalación Obligatoria):
- **`point_of_sale`** - Sistema de caja y ventas
- **`stock`** - Control de inventario
- **`product`** - Gestión de productos
- **`sale`** - Órdenes de venta

### MÓDULOS MUY IMPORTANTES:
- **`purchase`** - Gestión de compras
- **`account`** - Contabilidad
- **`crm`** - Gestión de clientes
- **`barcodes`** - Códigos de barras

### MÓDULOS SEGÚN NECESIDAD:

#### Para E-commerce:
- `website` + `website_sale`
- `delivery` (envíos)
- `payment_*` (métodos de pago)

#### Para Fidelización:
- `loyalty` (programas de puntos)
- `marketing_automation`

#### Para Cadenas:
- `base_multi_company`
- `board` (dashboards)

---

## ¿Cómo defines grupos de usuarios y permisos en Odoo?

La seguridad en Odoo se define en múltiples niveles:

### 1. Crear Grupos (`security/security.xml`):

```xml
<record id="group_user" model="res.groups">
    <field name="name">Usuario</field>
    <field name="category_id" ref="module_category"/>
    <field name="comment">Acceso básico</field>
</record>

<record id="group_manager" model="res.groups">
    <field name="name">Manager</field>
    <field name="implied_ids" eval="[(4, ref('group_user'))]"/>
</record>
```

### 2. Permisos CRUD (`security/ir.model.access.csv`):

```csv
id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink
access_model_user,model.user,model_my_model,group_user,1,1,1,0
access_model_manager,model.manager,model_my_model,group_manager,1,1,1,1
```

### 3. Reglas de Registro (`security/security.xml`):

```xml
<record id="rule_own_records" model="ir.rule">
    <field name="name">Usuario ve solo sus registros</field>
    <field name="model_id" ref="model_my_model"/>
    <field name="domain_force">[('create_uid', '=', user.id)]</field>
    <field name="groups" eval="[(4, ref('group_user'))]"/>
</record>
```

### 4. Seguridad de Menús:

```xml
<menuitem id="menu_admin" 
          name="Administración"
          groups="group_manager"/>
```

---

## ¿Cuál es la diferencia entre una regla de registro (record rule) y una lista de control de acceso (ACL)?

### Diferencias Fundamentales:

| Aspecto | ACL (`ir.model.access`) | Record Rules (`ir.rule`) |
|---------|-------------------------|--------------------------|
| **Nivel** | Modelo completo | Registros individuales |
| **Control** | Binario (Sí/No) | Granular (Dominio) |
| **Pregunta que responde** | "¿Puede acceder al modelo?" | "¿Qué registros puede ver?" |
| **Velocidad** | ⚡ Muy rápida | 🐌 Más lenta |
| **Flexibilidad** | 🔒 Limitada | 🎯 Muy flexible |
| **Obligatoriedad** | ✅ Requerida | ❓ Opcional |
| **Momento de evaluación** | Primero | Después |
| **Archivo** | CSV | XML |
| **Sintaxis** | Columnas fijas | Dominios Python |

### Flujo de Evaluación:

```
Usuario intenta acceder a registros
    ↓
1️⃣ ACL: ¿Tiene permiso en el MODELO?
    ↓ NO → ❌ Acceso Denegado Total
    ↓ SÍ
2️⃣ Record Rules: ¿Qué REGISTROS puede ver?
    ↓ Filtro aplicado
    ↓
3️⃣ ✅ Acceso Permitido a registros filtrados
```

### Ejemplo:

**ACL**: "El usuario puede leer productos"
```csv
access_product_user,product.user,product.model_product,base.group_user,1,0,0,0
```

**Record Rule**: "El usuario ve solo productos de su departamento"
```xml
<record id="product_dept_rule" model="ir.rule">
    <field name="domain_force">[('department_id', '=', user.department_id.id)]</field>
</record>
```

### Casos de Uso:

- **Usa ACL cuando**: Control simple por rol (Admin vs User)
- **Usa Record Rules cuando**: Filtrado contextual (mis registros, mi empresa)