# API de Gestión de Tarjas LH

API REST desarrollada en Flask para la gestión de tarjas de la empresa LH.

## Características

- API REST con Flask
- Soporte para CORS
- Configuración por variables de entorno
- Estructura modular con blueprints
- Documentación de endpoints

## Instalación

1. Clonar el repositorio
2. Crear entorno virtual:
   ```bash
   python -m venv venv
   ```

3. Activar el entorno virtual:
   - Windows:
     ```bash
     .\venv\Scripts\Activate.ps1
     ```
   - Linux/Mac:
     ```bash
     source venv/bin/activate
     ```

4. Instalar dependencias:
   ```bash
   pip install -r requirements.txt
   ```

## Configuración

Crear un archivo `.env` en la raíz del proyecto con las siguientes variables:

```env
SECRET_KEY=tu-clave-secreta-aqui
DEBUG=True
PORT=5000
```

## Ejecución

```bash
python app.py
```

La API estará disponible en `http://localhost:5000`

## Endpoints

- `GET /` - Información de la API
- `GET /api/health` - Estado de salud de la API

## Estructura del Proyecto

```
api_web_lh_tarja/
├── app.py              # Aplicación principal
├── config.py           # Configuración
├── requirements.txt    # Dependencias
├── README.md          # Documentación
├── venv/              # Entorno virtual
└── blueprints/        # Módulos de la API
    ├── __init__.py
    ├── auth.py
    ├── actividades.py
    ├── colaboradores.py
    ├── contratistas.py
    ├── opciones.py
    ├── permisos.py
    ├── rendimientopropio.py
    ├── rendimientos.py
    ├── trabajadores.py
    └── usuarios.py
```

## Desarrollo

Para agregar nuevos endpoints, crear blueprints en la carpeta `blueprints/` y registrarlos en `app.py`. 