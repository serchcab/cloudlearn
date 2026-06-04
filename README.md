# CloudLearn

Aplicacion web base para una academia digital con Flask, HTML, CSS y base de datos SQL.

## Tecnologias recomendadas

- Python 3.11 o superior
- Flask para backend web
- SQLAlchemy para modelos y acceso a datos
- Flask-Login para sesiones de usuario
- PostgreSQL para desarrollo formal y produccion
- SQLite como respaldo local si aun no instalas PostgreSQL
- HTML + CSS sin framework pesado para empezar simple

## Estructura del proyecto

```text
cloudlearn/
  app/
    __init__.py
    auth.py
    config.py
    models.py
    routes.py
    static/
      css/
        styles.css
    templates/
      base.html
      dashboard.html
      index.html
      login.html
      courses/
        detail.html
        list.html
  instance/
  .env.example
  .gitignore
  requirements.txt
  run.py
```

## Instalacion en Windows

Abre PowerShell dentro de la carpeta `cloudlearn` y ejecuta:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
copy .env.example .env
```

Si PowerShell no permite activar el entorno virtual, ejecuta una vez:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

## Configurar PostgreSQL

1. Instala PostgreSQL desde https://www.postgresql.org/download/windows/
2. Abre pgAdmin o SQL Shell.
3. Crea una base de datos llamada `cloudlearn`.
4. En el archivo `.env`, cambia `DATABASE_URL` con tu usuario y contrasena:

```env
DATABASE_URL=postgresql+psycopg://postgres:tu_password@localhost:5432/cloudlearn
```

Si aun no quieres instalar PostgreSQL, deja la variable vacia o comentada y Flask usara SQLite local.

## Crear tablas y datos iniciales

Con el entorno virtual activado:

```powershell
flask --app run.py init-db
```

Este comando crea las tablas y agrega usuarios de prueba:

| Rol | Correo | Contrasena |
| --- | --- | --- |
| Administrador | admin@cloudlearn.local | Admin123! |
| Docente | docente@cloudlearn.local | Docente123! |
| Estudiante | estudiante@cloudlearn.local | Estudiante123! |

## Ejecutar la aplicacion

```powershell
flask --app run.py --debug run
```

Despues abre:

```text
http://127.0.0.1:5000
```

## Modulos incluidos

La base actual ya incluye:

- Inicio de sesion por rol
- Administracion de usuarios
- Edicion de usuarios, cambio de rol, cambio de contrasena y activacion/desactivacion
- Creacion, edicion y eliminacion de cursos
- Inscripcion de estudiantes
- Materiales por enlace o archivo local
- Tareas por curso
- Entrega de tareas por estudiantes
- Calificacion y retroalimentacion de entregas
- Avance y calificacion por estudiante
- Dashboard con tareas pendientes, entregas recientes y resumen academico
- Reportes de cursos, estudiantes, materiales, tareas, entregas y promedios

## Rutas principales

| Modulo | Ruta |
| --- | --- |
| Panel | `/dashboard` |
| Usuarios | `/admin/users` |
| Editar usuario | `/admin/users/<id>/edit` |
| Cursos | `/courses` |
| Crear curso | `/courses/new` |
| Gestionar curso | `/courses/<id>/manage` |
| Reportes | `/reports` |

## Nota al cambiar modelos

Si se agregan nuevas tablas o campos, reinicia la base local:

```powershell
flask --app run.py init-db
```

Este comando borra y vuelve a crear los datos de prueba.

## Siguiente etapa recomendada

- Agregar busqueda y filtros
- Agregar edicion completa de usuarios
- Reemplazar archivos locales por Azure Blob Storage
- Preparar despliegue a Azure App Service
- Conectar autenticacion con Microsoft Entra ID
