# 📚 Documentación Completa de la API LH Gestión de Tarjas

## 🚀 Información General

**API REST** desarrollada en Flask para la gestión integral de tarjas, colaboradores, actividades y rendimientos de la empresa LH.

- **Base URL**: `http://localhost:5000`
- **Autenticación**: JWT (JSON Web Tokens)
- **Formato**: JSON
- **Versión**: 1.0.0

---

## 🔐 Autenticación

Todos los endpoints (excepto `/api/health`) requieren autenticación JWT.

### Headers Requeridos:
```http
Authorization: Bearer <jwt_token>
Content-Type: application/json
```

### Obtener Token:
```http
POST /api/auth/login
{
  "usuario": "nombre_usuario",
  "clave": "password"
}
```

---

## 📋 Endpoints por Módulo

## 🔑 Autenticación (`/api/auth`)

### POST `/api/auth/login`
**Descripción**: Iniciar sesión y obtener token JWT

**Request Body**:
```json
{
  "usuario": "string",
  "clave": "string"
}
```

**Response**:
```json
{
  "access_token": "jwt_token",
  "usuario": {
    "id": "uuid",
    "usuario": "nombre_usuario",
    "nombre": "Juan",
    "apellido_paterno": "Pérez",
    "id_sucursalactiva": 106
  }
}
```

---

## 👥 Usuarios (`/api/usuarios`)

> **⚠️ Requiere permiso Full (id=6) para todos los endpoints**

### GET `/api/usuarios/`
**Descripción**: Obtener todos los usuarios

**Response**:
```json
[
  {
    "id": "uuid",
    "usuario": "nombre_usuario",
    "correo": "email@ejemplo.com",
    "id_sucursalactiva": 106,
    "id_estado": 1,
    "id_rol": 3,
    "id_perfil": 1,
    "fecha_creacion": "2025-01-01",
    "nombre_sucursal": "OFICINA CENTRAL",
    "nombre_completo": "Juan Pérez González"
  }
]
```

### POST `/api/usuarios/`
**Descripción**: Crear nuevo usuario

**Request Body**:
```json
{
  "usuario": "string",
  "correo": "string",
  "clave": "string",
  "id_sucursalactiva": 106,
  "nombre": "string",
  "apellido_paterno": "string",
  "apellido_materno": "string",
  "permisos": ["6", "7", "8"]
}
```

**Response**:
```json
{
  "message": "Usuario creado correctamente",
  "id": "uuid",
  "usuario": "nombre_usuario",
  "correo": "email@ejemplo.com",
  "id_sucursalactiva": 106,
  "nombre": "Juan",
  "apellido_paterno": "Pérez",
  "apellido_materno": "González",
  "permisos_asignados": ["6", "7", "8"]
}
```

### PUT `/api/usuarios/{usuario_id}`
**Descripción**: Editar usuario existente

**Request Body**:
```json
{
  "usuario": "string",
  "correo": "string",
  "clave": "string",
  "id_sucursalactiva": 106,
  "nombre": "string",
  "apellido_paterno": "string",
  "apellido_materno": "string",
  "permisos": ["6", "7", "8"],
  "id_estado": 1
}
```

### DELETE `/api/usuarios/{usuario_id}`
**Descripción**: Eliminar usuario

### GET `/api/usuarios/permisos-disponibles`
**Descripción**: Obtener permisos disponibles para la app (id_app=3)

**Response**:
```json
{
  "permisos": [
    {
      "id": "6",
      "nombre": "Full",
      "id_app": 3,
      "id_estado": 1
    }
  ],
  "total": 1
}
```

### GET `/api/usuarios/{usuario_id}/permisos`
**Descripción**: Obtener permisos actuales de un usuario

**Response**:
```json
{
  "usuario_id": "uuid",
  "permisos": [
    {
      "id_permiso": "6",
      "nombre_permiso": "Full",
      "id_app": 3,
      "id_estado": 1
    }
  ],
  "total": 1
}
```

---

## 🏢 Sucursales (`/api/sucursal`)

### GET `/api/sucursal/ubicacion-activa`
**Descripción**: Obtener ubicación de la sucursal activa del usuario

**Response**:
```json
{
  "ubicacion": "-33.78367522929209, -70.73970944745895"
}
```

---

## 👷 Colaboradores (`/api/colaboradores`)

### GET `/api/colaboradores/`
**Descripción**: Listar colaboradores de la sucursal activa

**Query Parameters**:
- `buscar` (opcional): Término de búsqueda
- `id_estado` (opcional): Filtrar por estado

**Response**:
```json
[
  {
    "id": "uuid",
    "nombre": "Juan",
    "apellido_paterno": "Pérez",
    "apellido_materno": "González",
    "rut": "12345678-9",
    "id_sucursal": 106,
    "id_estado": 1,
    "sueldobase": 500000,
    "base_dia": 16667,
    "hora_dia": 1894,
    "fecha_sueldobase": "2025-01-01"
  }
]
```

### GET `/api/colaboradores/{colaborador_id}`
**Descripción**: Obtener colaborador por ID

### POST `/api/colaboradores/`
**Descripción**: Crear nuevo colaborador

### PUT `/api/colaboradores/{colaborador_id}`
**Descripción**: Editar colaborador

### DELETE `/api/colaboradores/{colaborador_id}`
**Descripción**: Eliminar colaborador

---

## 🏗️ Contratistas (`/api/contratistas`)

### GET `/api/contratistas/`
**Descripción**: Listar contratistas con cantidad de trabajadores activos

**Response**:
```json
[
  {
    "id": "uuid",
    "nombre": "Contratista ABC",
    "cantidad_trabajadores_activos": 15
  }
]
```

---

## 🎯 Actividades (`/api/actividades`)

### GET `/api/actividades/`
**Descripción**: Listar actividades ordenadas alfabéticamente por labor

**Query Parameters**:
- `fecha_desde` (opcional): Fecha de inicio
- `fecha_hasta` (opcional): Fecha de fin
- `id_labor` (opcional): Filtrar por labor
- `id_estadoactividad` (opcional): Filtrar por estado

### GET `/api/actividades/{actividad_id}`
**Descripción**: Obtener actividad por ID

### POST `/api/actividades/`
**Descripción**: Crear nueva actividad

### PUT `/api/actividades/{actividad_id}`
**Descripción**: Editar actividad

### PUT `/api/actividades/{actividad_id}/cambiar-estado`
**Descripción**: Cambiar estado de actividad

---

## 📊 Rendimientos (`/api/rendimientos`)

### GET `/api/rendimientos/individuales-propios`
**Descripción**: Obtener rendimientos individuales propios

**Query Parameters**:
- `fecha_desde`, `fecha_hasta`: Rango de fechas
- `id_colaborador`: Filtrar por colaborador
- `id_actividad`: Filtrar por actividad

### GET `/api/rendimientos/individuales-contratistas`
**Descripción**: Obtener rendimientos individuales de contratistas

**Query Parameters**:
- `id_actividad` (opcional): Filtrar por actividad

### GET `/api/rendimientos/grupales`
**Descripción**: Obtener rendimientos grupales

---

## ⏰ Horas Trabajadas (`/api/horas-trabajadas`)

### GET `/api/horas-trabajadas/resumen-diario-colaborador`
**Descripción**: Obtener resumen diario de horas trabajadas por colaborador

**Query Parameters**:
- `fecha_desde`, `fecha_hasta`: Rango de fechas
- `id_colaborador`: Filtrar por colaborador

**Response**:
```json
[
  {
    "id_colaborador": "uuid",
    "nombre_colaborador": "Juan Pérez",
    "fecha": "2025-01-01",
    "total_horas_trabajadas": "8:00:00",
    "total_rendimiento": 2.5,
    "actividades_detalle": [
      {
        "id_actividad": "123",
        "labor": "ABOCAR",
        "ceco": "AN2 B2B LH SM",
        "nombre_ceco": "Nombre Completo del CECO",
        "horas_trabajadas": "4:00:00",
        "rendimiento": 2.0
      }
    ]
  }
]
```

---

## ⚡ Horas Extras (`/api/horas-extras`)

### GET `/api/horas-extras/`
**Descripción**: Listar rendimientos propios con horas esperadas

**Response**:
```json
[
  {
    "id_colaborador": "uuid",
    "nombre_colaborador": "Juan Pérez",
    "fecha": "2025-01-01",
    "horas_esperadas": 8,
    "total_horas_trabajadas": 9.5,
    "diferencia_horas": 1.5,
    "estado_trabajo": "MÁS",
    "actividades_detalle": [
      {
        "id_actividad": "123",
        "labor": "ABOCAR",
        "ceco": "AN2 B2B LH SM",
        "nombre_ceco": "Nombre Completo del CECO",
        "horas_trabajadas": "4:00:00"
      }
    ]
  }
]
```

---

## 🏭 Horas Extras Otros CECOs (`/api/horas-extras-otroscecos`)

### GET `/api/horas-extras-otroscecos/`
**Descripción**: Listar horas extras en otros CECOs

### POST `/api/horas-extras-otroscecos/`
**Descripción**: Crear registro de horas extras en otro CECO

### GET `/api/horas-extras-otroscecos/tipos-ceco`
**Descripción**: Obtener tipos de CECO disponibles

### GET `/api/horas-extras-otroscecos/cecos-por-tipo/{id_tipo_ceco}`
**Descripción**: Obtener CECOs por tipo

---

## 💰 Sueldos (`/api/sueldos`)

### GET `/api/sueldos/sueldos-base`
**Descripción**: Listar sueldos base agrupados por colaborador

**Response**:
```json
[
  {
    "id_colaborador": "uuid",
    "nombre_colaborador": "Juan Pérez",
    "sueldos_base": [
      {
        "id": 1,
        "sueldobase": 500000,
        "fecha": "2025-01-01",
        "base_dia": 16667,
        "hora_dia": 1894
      }
    ]
  }
]
```

### GET `/api/sueldos/sueldos-base/{sueldo_id}`
**Descripción**: Obtener sueldo base por ID

### POST `/api/sueldos/sueldos-base`
**Descripción**: Crear nuevo sueldo base

### PUT `/api/sueldos/sueldos-base/{sueldo_id}`
**Descripción**: Editar sueldo base

### DELETE `/api/sueldos/sueldos-base/{sueldo_id}`
**Descripción**: Eliminar sueldo base

---

## 📋 Tarjas Propios (`/api/tarja-propio`)

### GET `/api/tarja-propio/`
**Descripción**: Obtener tarjas propios de la vista `v_tarja_tarjaweb_tarjaspropios`

**Query Parameters**:
- `fecha_desde`, `fecha_hasta`: Rango de fechas
- `id_colaborador`: Filtrar por colaborador
- `id_labor`: Filtrar por labor
- `id_ceco`: Filtrar por CECO
- `id_estadoactividad`: Filtrar por estado de actividad

**Response**:
```json
{
  "tarjas_propios": [
    {
      "id_sucursal": 106,
      "fecha": "2025-09-01",
      "id_usuario": "123",
      "usuario": "admin",
      "id_colaborador": "456",
      "colaborador": "DOMINGO VALENZUELA",
      "id_labor": 1,
      "labor": "RALEO",
      "id_tiporendimiento": 1,
      "tipo_renimiento": "Individual",
      "id_ceco": 101,
      "centro_de_costo": "CECO001",
      "detalle_ceco": "Detalle del CECO",
      "horas_trabajadas": "9:00:00",
      "id_unidad": 1,
      "unidad": "Hectárea",
      "rendimiento": 2.5,
      "tarifa": 15000,
      "liquido_trato_dia": 135000,
      "horas_extras": "1:30:00",
      "valor_he": 3000,
      "total_HE": 4500,
      "id_estadoactividad": 1,
      "estado": "Activa"
    }
  ],
  "total": 257
}
```

### GET `/api/tarja-propio/resumen`
**Descripción**: Obtener resumen de tarjas propios por colaborador

**Response**:
```json
{
  "resumen": [
    {
      "id_colaborador": "456",
      "colaborador": "DOMINGO VALENZUELA",
      "total_registros": 15,
      "total_horas_trabajadas": "135:00:00",
      "total_rendimiento": 37.5,
      "total_horas_extras": "15:30:00",
      "total_valor_he": 45000,
      "total_liquido_trato_dia": 2025000,
      "promedio_rendimiento": 2.5
    }
  ],
  "total_colaboradores": 25
}
```

---

## 🎯 Rendimientos Propios (`/api/rendimientopropio`)

### GET `/api/rendimientopropio/actividad/{id_actividad}`
**Descripción**: Obtener rendimientos propios por actividad con sueldo base actual

**Response**:
```json
[
  {
    "id": "uuid",
    "id_colaborador": "456",
    "nombre_colaborador": "Juan Pérez",
    "apellido_paterno": "Pérez",
    "apellido_materno": "González",
    "horas_trabajadas": "8:00:00",
    "rendimiento": 2.5,
    "horas_extras": "1:30:00",
    "id_bono": 1,
    "id_ceco": 101,
    "nombre_ceco": "CECO Administrativo",
    "sueldobase": 500000,
    "base_dia": 16667,
    "hora_dia": 1894
  }
]
```

---

## 🏥 Licencias (`/api/licencias`)

### GET `/api/licencias/`
**Descripción**: Listar licencias médicas

### POST `/api/licencias/`
**Descripción**: Crear nueva licencia médica

### PUT `/api/licencias/{licencia_id}`
**Descripción**: Editar licencia médica

### DELETE `/api/licencias/{licencia_id}`
**Descripción**: Eliminar licencia médica

---

## 🏖️ Vacaciones (`/api/vacaciones`)

### GET `/api/vacaciones/`
**Descripción**: Listar vacaciones

### POST `/api/vacaciones/`
**Descripción**: Crear nueva vacación

### PUT `/api/vacaciones/{vacacion_id}`
**Descripción**: Editar vacación

### DELETE `/api/vacaciones/{vacacion_id}`
**Descripción**: Eliminar vacación

---

## 📝 Permisos (`/api/permisos`)

### GET `/api/permisos/`
**Descripción**: Listar permisos de ausencia

### POST `/api/permisos/`
**Descripción**: Crear nuevo permiso

### PUT `/api/permisos/{permiso_id}`
**Descripción**: Editar permiso

### DELETE `/api/permisos/{permiso_id}`
**Descripción**: Eliminar permiso

---

## 🎁 Bono Especial (`/api/bono-especial`)

### GET `/api/bono-especial/`
**Descripción**: Listar bonos especiales

### POST `/api/bono-especial/`
**Descripción**: Crear nuevo bono especial

### PUT `/api/bono-especial/{bono_id}`
**Descripción**: Editar bono especial

### DELETE `/api/bono-especial/{bono_id}`
**Descripción**: Eliminar bono especial

---

## 🔧 Opciones (`/api/opciones`)

### GET `/api/opciones/`
**Descripción**: Obtener opciones del sistema

---

## 📊 Códigos de Estado HTTP

| Código | Descripción |
|--------|-------------|
| 200 | OK - Solicitud exitosa |
| 201 | Created - Recurso creado exitosamente |
| 400 | Bad Request - Datos de entrada inválidos |
| 401 | Unauthorized - Token JWT inválido o faltante |
| 403 | Forbidden - Sin permisos suficientes |
| 404 | Not Found - Recurso no encontrado |
| 500 | Internal Server Error - Error interno del servidor |

---

## 🚨 Manejo de Errores

### Formato de Error:
```json
{
  "error": "Descripción del error"
}
```

### Errores Comunes:

#### 401 Unauthorized
```json
{
  "error": "Token JWT inválido o faltante"
}
```

#### 403 Forbidden
```json
{
  "error": "No autorizado. Se requiere permiso Full para gestionar usuarios"
}
```

#### 404 Not Found
```json
{
  "error": "Usuario no encontrado"
}
```

#### 400 Bad Request
```json
{
  "error": "Faltan campos obligatorios: usuario, correo, clave, id_sucursalactiva, nombre, apellido_paterno"
}
```

---

## 🔒 Seguridad

### Autenticación JWT
- Todos los endpoints requieren token JWT válido
- Token se obtiene mediante `/api/auth/login`
- Token debe incluirse en header `Authorization: Bearer <token>`

### Permisos
- **Gestión de Usuarios**: Requiere permiso Full (id=6)
- **Otros endpoints**: Requieren autenticación JWT básica
- **Filtrado por Sucursal**: Los datos se filtran automáticamente por la sucursal activa del usuario

### Validaciones
- **Campos obligatorios**: Validación en todos los endpoints de creación/edición
- **Formato de datos**: Validación de tipos de datos y formatos
- **Existencia de recursos**: Verificación de existencia antes de operaciones

---

## 📈 Características Técnicas

### Base de Datos
- **MySQL** con conexión mediante `mysql-connector-python`
- **Transacciones atómicas** para operaciones complejas
- **Índices optimizados** para consultas frecuentes

### Serialización JSON
- **Campos de tiempo**: Convertidos automáticamente a string para compatibilidad JSON
- **Relaciones**: JOINs optimizados para obtener datos relacionados
- **Agregaciones**: Funciones SQL para cálculos complejos

### Estructura Modular
- **Blueprints**: Separación por funcionalidad
- **Utils**: Funciones auxiliares reutilizables
- **Config**: Configuración centralizada

---

## 🚀 Instalación y Configuración

### Requisitos
- Python 3.8+
- MySQL 8.0+
- pip

### Instalación
```bash
# Clonar repositorio
git clone <repository-url>
cd api_web_lh_tarja

# Crear entorno virtual
python -m venv venv

# Activar entorno virtual
# Windows:
.\venv\Scripts\Activate.ps1
# Linux/Mac:
source venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt
```

### Configuración
Crear archivo `.env`:
```env
SECRET_KEY=tu-clave-secreta-aqui
DEBUG=True
PORT=5000
DATABASE_URL=mysql+pymysql://user:password@localhost/database
```

### Ejecución
```bash
python app.py
```

---

## 📞 Soporte

Para soporte técnico o consultas sobre la API, contactar al equipo de desarrollo.

---

**Versión**: 1.0.0  
**Última actualización**: Enero 2025  
**Desarrollado por**: Equipo LH Gestión de Tarjas
