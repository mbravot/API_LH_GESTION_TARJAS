# 🚀 API de Gestión de Tarjas LH

API REST desarrollada en Flask para la gestión integral de tarjas, colaboradores, actividades y rendimientos de la empresa LH.

## 📚 Documentación Completa

**👉 [Ver Documentación Completa de la API](./API_DOCUMENTATION.md)**

La documentación completa incluye:
- Todos los endpoints disponibles
- Ejemplos de requests y responses
- Códigos de estado HTTP
- Manejo de errores
- Guías de autenticación y seguridad

## ⚡ Inicio Rápido

### 1. Instalación
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

### 2. Configuración
Crear archivo `.env`:
```env
SECRET_KEY=tu-clave-secreta-aqui
DEBUG=True
PORT=5000
DATABASE_URL=mysql+pymysql://user:password@localhost/database
```

### 3. Ejecución
```bash
python app.py
```

La API estará disponible en `http://localhost:5000`

## 🔑 Autenticación

```bash
# Obtener token
curl -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"usuario": "tu_usuario", "clave": "tu_password"}'

# Usar token en requests
curl -X GET http://localhost:5000/api/usuarios/ \
  -H "Authorization: Bearer <tu_token>"
```

## 📋 Módulos Principales

| Módulo | Endpoint | Descripción |
|--------|----------|-------------|
| 🔐 **Auth** | `/api/auth` | Autenticación y login |
| 👥 **Usuarios** | `/api/usuarios` | Gestión de usuarios y permisos |
| 🏢 **Sucursales** | `/api/sucursal` | Información de sucursales |
| 👷 **Colaboradores** | `/api/colaboradores` | Gestión de colaboradores |
| 🏗️ **Contratistas** | `/api/contratistas` | Gestión de contratistas |
| 🎯 **Actividades** | `/api/actividades` | Gestión de actividades |
| 📊 **Rendimientos** | `/api/rendimientos` | Reportes de rendimientos |
| ⏰ **Horas** | `/api/horas-*` | Gestión de horas trabajadas y extras |
| 💰 **Sueldos** | `/api/sueldos` | Gestión de sueldos base |
| 📋 **Tarjas** | `/api/tarja-propio` | Vista de tarjas propios |

## 🛠️ Tecnologías

- **Backend**: Flask (Python)
- **Base de Datos**: MySQL
- **Autenticación**: JWT
- **ORM**: mysql-connector-python
- **Validación**: bcrypt para passwords

## 🔒 Seguridad

- **Autenticación JWT** en todos los endpoints
- **Permisos granulares** por funcionalidad
- **Filtrado automático** por sucursal del usuario
- **Validación robusta** de datos de entrada

## 📊 Características

- ✅ **API REST** completa con 50+ endpoints
- ✅ **Autenticación JWT** segura
- ✅ **Gestión de permisos** granular
- ✅ **Filtrado automático** por sucursal
- ✅ **Validaciones robustas** de datos
- ✅ **Manejo de errores** consistente
- ✅ **Documentación completa** con ejemplos
- ✅ **Estructura modular** con blueprints

## 🚀 Endpoints Principales

### Autenticación
- `POST /api/auth/login` - Iniciar sesión

### Usuarios (Requiere permiso Full)
- `GET /api/usuarios/` - Listar usuarios
- `POST /api/usuarios/` - Crear usuario
- `PUT /api/usuarios/{id}` - Editar usuario
- `DELETE /api/usuarios/{id}` - Eliminar usuario

### Colaboradores
- `GET /api/colaboradores/` - Listar colaboradores
- `POST /api/colaboradores/` - Crear colaborador
- `PUT /api/colaboradores/{id}` - Editar colaborador

### Actividades
- `GET /api/actividades/` - Listar actividades
- `POST /api/actividades/` - Crear actividad
- `PUT /api/actividades/{id}/cambiar-estado` - Cambiar estado

### Reportes
- `GET /api/rendimientos/individuales-propios` - Rendimientos individuales
- `GET /api/horas-trabajadas/resumen-diario-colaborador` - Resumen de horas
- `GET /api/tarja-propio/` - Vista de tarjas propios

## 📁 Estructura del Proyecto

```
api_web_lh_tarja/
├── app.py                    # Aplicación principal
├── config.py                 # Configuración
├── requirements.txt          # Dependencias
├── README.md                # Este archivo
├── API_DOCUMENTATION.md     # Documentación completa
├── utils/                   # Utilidades
│   ├── db.py               # Conexión a BD
│   └── validar_rut.py      # Validación RUT
└── blueprints/             # Módulos de la API
    ├── auth.py             # Autenticación
    ├── usuarios.py         # Gestión de usuarios
    ├── colaboradores.py    # Gestión de colaboradores
    ├── actividades.py      # Gestión de actividades
    ├── rendimientos.py    # Reportes de rendimientos
    ├── horas_trabajadas.py # Gestión de horas
    ├── horas_extras.py     # Gestión de horas extras
    ├── sueldos.py          # Gestión de sueldos
    ├── tarja_propio.py     # Vista de tarjas
    └── ...                 # Otros módulos
```

## 🆘 Soporte

Para soporte técnico o consultas sobre la API:
- 📖 **Documentación completa**: [API_DOCUMENTATION.md](./API_DOCUMENTATION.md)
- 🐛 **Issues**: Reportar en el repositorio
- 💬 **Consultas**: Contactar al equipo de desarrollo

---

**Versión**: 1.0.0  
**Última actualización**: Enero 2025  
**Desarrollado por**: Equipo LH Gestión de Tarjas 