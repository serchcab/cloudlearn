# Despliegue de CloudLearn

Esta guia cubre dos destinos:

- GitHub para guardar el codigo.
- Azure App Service para publicar la aplicacion Flask.

## 1. Preparar Windows

Instala:

- Git for Windows: https://git-scm.com/download/win
- Azure CLI: https://learn.microsoft.com/cli/azure/install-azure-cli-windows

Cierra y vuelve a abrir PowerShell despues de instalar.

Verifica:

```powershell
git --version
az --version
```

## 2. Subir a GitHub

Desde la carpeta `cloudlearn`:

```powershell
git init
git add .
git commit -m "Initial CloudLearn Flask platform"
git branch -M main
git remote add origin https://github.com/TU_USUARIO/cloudlearn.git
git push -u origin main
```

Antes debes crear el repositorio vacio en GitHub.

## 3. Variables de entorno para Azure

En Azure App Service configura:

```text
FLASK_SECRET_KEY=una_clave_segura
DATABASE_URL=postgresql+psycopg://usuario:password@servidor:5432/cloudlearn
```

No subas el archivo `.env` a GitHub.

## 4. Crear App Service con Azure CLI

Ejemplo basico:

```powershell
az login
az group create --name CloudLearn-RG --location eastus
az appservice plan create --name cloudlearn-plan --resource-group CloudLearn-RG --sku B1 --is-linux
az webapp create --resource-group CloudLearn-RG --plan cloudlearn-plan --name cloudlearn-app-sergio --runtime "PYTHON:3.11"
az webapp config set --resource-group CloudLearn-RG --name cloudlearn-app-sergio --startup-file "gunicorn --bind=0.0.0.0 --timeout 600 wsgi:app"
```

## 5. Desplegar desde GitHub

En Azure Portal:

1. Entra a tu App Service.
2. Abre Deployment Center.
3. Selecciona GitHub.
4. Elige organizacion, repositorio y rama `main`.
5. Guarda la configuracion.

Azure creara el workflow automaticamente.

## 6. Inicializar base de datos

Para desarrollo local:

```powershell
flask --app run.py init-db
```

Para produccion conviene usar migraciones o ejecutar un comando controlado desde consola/Kudu. No uses `init-db` en produccion si ya tienes datos reales porque borra y recrea tablas.
