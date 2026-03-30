# MPC Plan

Aplicación web en Django para planificar proyectos, registrar trabajo diario y visualizar cronologías en vistas de día, mes y año.

## Qué es este proyecto

Este repositorio contiene una aplicación Django 5.2 orientada a:

- planificar proyectos con horas estimadas;
- registrar trabajo diario real;
- recalcular fechas estimadas según el tiempo realmente invertido;
- reflejar interrupciones y trabajo fuera de proyecto;
- asignar responsables y solicitantes usando usuarios nativos de Django;
- mostrar todo en una interfaz web única, simple y editable.

La vista principal está en [`planner/templates/planner/index.html`](./planner/templates/planner/index.html) y actúa como panel de planificación, calendario y edición rápida.

## Estado actual

La aplicación ya incluye:

- gestión de proyectos desde Django Admin y desde la portada;
- calendario interactivo con vistas `día`, `mes` y `año`;
- formulario modal para añadir y editar registros diarios;
- visibilidad persistente por proyecto y para trabajo fuera de proyecto;
- asignación de uno o varios usuarios solicitantes;
- asignación de uno o varios usuarios ejecutores;
- cálculo de porcentaje de avance;
- fecha de entrega y fecha estimada recalculada;
- pruebas automáticas de lógica y flujos principales.

## Tecnologías usadas

- Python 3.12
- Django 5.2
- SQLite en desarrollo
- Plantillas Django renderizadas en servidor
- Django Admin
- FullCalendar 6.1.20 cargado por CDN en la interfaz pública
- CSS y JavaScript vanilla en una sola plantilla principal

Dependencias actuales de Python:

- Django
- asgiref
- sqlparse

Referencia del entorno en [`requirements.txt`](./requirements.txt).

## Estructura del proyecto

```text
.
├── AGENTS.md
├── README.md
├── manage.py
├── requirements.txt
├── config/
│   ├── settings.py
│   ├── urls.py
│   ├── asgi.py
│   └── wsgi.py
├── planner/
│   ├── admin.py
│   ├── forms.py
│   ├── models.py
│   ├── services.py
│   ├── tests.py
│   ├── urls.py
│   ├── views.py
│   ├── migrations/
│   └── templates/planner/index.html
└── static/
    └── images/
```

## Cómo se montó el proyecto

### 1. Base Django

Se creó un proyecto Django con configuración clásica:

- proyecto global en `config/`;
- app principal en `planner/`;
- enrutado raíz hacia `planner.urls`;
- uso de plantillas de app con `APP_DIRS=True`.

### 2. Modelo de dominio

La evolución del proyecto simplificó el diseño inicial y dejó el flujo principal en torno a dos entidades activas:

- `Project`
- `WorkLog`

Se mantuvo `ProjectTask` por compatibilidad histórica, pero el flujo principal actual gira sobre proyectos y registros diarios.

### 3. Lógica separada de la vista

La lógica de planificación vive en [`planner/services.py`](./planner/services.py).  
Esto permite:

- recalcular fechas sin meter reglas en la plantilla;
- probar la lógica con tests;
- reutilizar el contexto calculado desde la vista principal.

### 4. Interfaz pública

La portada se fue ampliando por iteraciones pequeñas:

- primero cronología simple;
- después calendario interactivo;
- luego modales de edición;
- más tarde filtros de visibilidad;
- y finalmente información de usuarios, progreso y mejoras visuales.

### 5. Administración

El panel Django Admin sigue siendo una parte importante del proyecto para:

- crear usuarios;
- revisar proyectos;
- revisar registros diarios;
- tocar configuraciones rápidas sin depender de la portada.

## Modelos actuales

### Project

Archivo: [`planner/models.py`](./planner/models.py)

Representa un proyecto planificado.

Campos principales:

- `name`: nombre del proyecto
- `description`: descripción funcional
- `planned_start_date`: fecha de inicio prevista
- `delivery_date`: fecha compromiso / entrega
- `requested_by`: usuarios que solicitan el proyecto
- `assigned_users`: usuarios que lo ejecutan
- `color`: color visual en calendario y tarjetas
- `is_visible`: visibilidad en calendario
- `estimated_hours`: horas estimadas
- `status`: estado general
- `notes`: observaciones

### WorkLog

Archivo: [`planner/models.py`](./planner/models.py)

Representa una entrada diaria de trabajo.

Campos principales:

- `date`: fecha del trabajo
- `requested_by`: usuarios que solicitan esa tarea o intervención
- `assigned_users`: usuarios que la realizan
- `project`: proyecto relacionado, opcional
- `task`: parte histórica del proyecto, opcional
- `description`: detalle de lo realizado
- `actual_hours`: horas invertidas
- `work_type`: tipo de trabajo
- `notes`: observaciones

Tipos actuales de trabajo:

- `project_work`
- `other_work`

### PlannerSettings

Archivo: [`planner/models.py`](./planner/models.py)

Modelo singleton simple para preferencias globales del panel.

Actualmente guarda:

- `show_other_work`: si el trabajo fuera de proyecto debe verse o no en calendario

### ProjectTask

Permanece en el esquema como compatibilidad histórica, pero no es el núcleo del flujo actual.  
Sirve como base para futuras ampliaciones si se quiere volver a un nivel más fino por fases o subtareas planificadas.

## Funcionamiento general

### Flujo de proyectos

1. Se crea un proyecto.
2. Se le asigna:
   - fecha de inicio,
   - fecha de entrega,
   - horas estimadas,
   - usuarios solicitantes,
   - usuarios asignados.
3. El sistema calcula una fecha base y una fecha estimada de fin.
4. A medida que se registran horas reales, el porcentaje de avance y la proyección cambian.

### Flujo de trabajo diario

1. Se abre el modal de registro diario.
2. Se elige fecha.
3. Se indica si el trabajo pertenece a un proyecto o no.
4. Se asignan solicitantes y ejecutores.
5. Se guardan horas reales.
6. El calendario y las tarjetas se recalculan al recargar la página.

### Cómo se calcula la planificación

La regla actual es simple y deliberadamente entendible:

- capacidad diaria por proyecto: `7.00 h`;
- las horas registradas sobre un proyecto descuentan horas pendientes;
- las horas dedicadas a otros proyectos o a trabajo no asociado consumen capacidad y desplazan fechas estimadas;
- la fecha estimada se recalcula según horas pendientes y bloqueos;
- si existe `delivery_date`, se muestra margen o retraso respecto a esa fecha.

### Visibilidad

La leyenda superior permite:

- ocultar o mostrar proyectos;
- ocultar o mostrar trabajo fuera de proyecto.

Estas preferencias se guardan en base de datos.

## Vista principal

Archivo: [`planner/templates/planner/index.html`](./planner/templates/planner/index.html)

La portada reúne:

- cabecera con logo;
- panel de información;
- leyenda de proyectos con porcentaje y visibilidad;
- calendario interactivo;
- tarjetas resumen de proyectos;
- tabla de registros recientes;
- modales de edición rápida.

### Vistas de calendario

- `Día`: agenda simple
- `Mes`: bloques de proyecto y mini barras de trabajo diario
- `Año`: vista compacta por color y progreso diario

### Interacciones relevantes

- click en proyecto para editarlo;
- click en registro diario para editarlo;
- click en día vacío para crear registro;
- click en chips de leyenda para ocultar o mostrar elementos;
- formularios protegidos contra doble envío.

## Formularios

Archivo: [`planner/forms.py`](./planner/forms.py)

Hay dos formularios principales:

- `ProjectForm`
- `WorkLogForm`

Características:

- campos fecha con `input[type="date"]`;
- selección múltiple de usuarios con checkboxes;
- validación para evitar duplicar proyectos con mismo nombre y fecha de inicio.

## Administración

Archivo: [`planner/admin.py`](./planner/admin.py)

Se registran:

- `Project`
- `WorkLog`
- `PlannerSettings`

El admin se usa especialmente para:

- crear usuarios de Django;
- revisar proyectos y registros;
- gestionar configuraciones globales.

## Lógica de servicios

Archivo: [`planner/services.py`](./planner/services.py)

`build_timeline_context()` es la pieza central.

Se encarga de:

- cargar proyectos y registros;
- agrupar horas por proyecto;
- calcular horas pendientes;
- obtener fecha base y fecha estimada;
- incorporar retrasos por trabajo ajeno;
- construir eventos del calendario;
- preparar leyenda y tarjetas resumen.

## Tests

Archivo: [`planner/tests.py`](./planner/tests.py)

Actualmente cubren:

- validaciones de `WorkLog`;
- cálculo de fechas y horas pendientes;
- retrasos por trabajo externo;
- retrasos por trabajo en otros proyectos;
- visibilidad;
- creación y edición desde la portada;
- prevención de duplicados.

## Cómo ejecutar en local

### Requisitos

- Python 3.12
- entorno con dependencias instaladas

### Pasos

```bash
python manage.py migrate
python manage.py runserver
```

### Comprobaciones útiles

```bash
python manage.py check
python manage.py test
```

## Cómo usarlo

### Crear usuarios

Desde Django Admin:

```bash
python manage.py createsuperuser
```

Luego entra en `/admin/` y crea los usuarios necesarios.

### Crear un proyecto

Desde la portada:

1. pulsa `Añadir proyecto`;
2. rellena fechas, horas y color;
3. selecciona usuarios solicitantes;
4. selecciona usuarios asignados;
5. guarda.

### Crear un registro diario

Desde la portada:

1. pulsa un día del calendario o `Añadir registro diario`;
2. indica si es trabajo de proyecto o trabajo no asociado;
3. selecciona proyecto si aplica;
4. marca solicitantes y usuarios ejecutores;
5. introduce horas reales;
6. guarda.

## Despliegue recomendado en Render

He consultado la documentación oficial de Render para Django y el despliegue recomendado hoy pasa por:

- servicio web para Django;
- PostgreSQL gestionado por Render;
- `build.sh` como comando de build;
- `gunicorn` para el arranque;
- WhiteNoise para servir estáticos;
- variables de entorno para configuración sensible.

Fuentes oficiales usadas:

- https://render.com/docs/deploy-django
- https://render.com/docs/deploys/

### Situación actual del proyecto respecto a producción

El proyecto actual está preparado para desarrollo, pero para producción en Render haría estos ajustes antes de publicarlo:

1. Cambiar SQLite por PostgreSQL.
2. Mover `SECRET_KEY` a variable de entorno.
3. Desactivar `DEBUG` en producción.
4. Configurar `ALLOWED_HOSTS` dinámicamente.
5. Añadir WhiteNoise para estáticos.
6. Añadir Gunicorn.
7. Preparar `build.sh`.

### Dependencias recomendadas para Render

Añadiría:

- `gunicorn`
- `whitenoise`
- `psycopg[binary]` o `psycopg2-binary`
- opcionalmente `dj-database-url`

### Ajustes de configuración que haría

En [`config/settings.py`](./config/settings.py):

- `SECRET_KEY` desde variable de entorno;
- `DEBUG` condicionado por entorno;
- `ALLOWED_HOSTS` incluyendo `RENDER_EXTERNAL_HOSTNAME`;
- `DATABASES` leyendo `DATABASE_URL`;
- `WhiteNoiseMiddleware` justo después de `SecurityMiddleware`;
- `STATIC_ROOT = BASE_DIR / "staticfiles"`.

### build.sh recomendado

Ejemplo:

```bash
#!/usr/bin/env bash
set -o errexit

pip install -r requirements.txt
python manage.py collectstatic --no-input
python manage.py migrate
```

### Start command recomendado

Para este proyecto:

```bash
gunicorn config.wsgi:application
```

Si quisieras una capa ASGI más adelante:

```bash
python -m gunicorn config.asgi:application -k uvicorn.workers.UvicornWorker
```

### Variables de entorno mínimas en Render

- `SECRET_KEY`
- `DEBUG=False`
- `DATABASE_URL`
- `WEB_CONCURRENCY=4`

### Despliegue manual en Render

1. Subir el repositorio a GitHub/GitLab.
2. Crear una base de datos PostgreSQL en Render.
3. Crear un Web Service apuntando al repositorio.
4. Configurar:
   - Build Command: `./build.sh`
   - Start Command: `gunicorn config.wsgi:application`
5. Añadir variables de entorno.
6. Lanzar deploy.
7. Crear superusuario desde Render Shell.

### Alternativa con render.yaml

También es una buena opción declarar el servicio con `render.yaml`, sobre todo si quieres:

- despliegue reproducible;
- entorno versionado;
- menor configuración manual.

En este repositorio todavía no lo he generado, pero sería una siguiente mejora razonable.

## Mejoras futuras recomendadas

- filtro por usuario en calendario;
- autenticación y permisos por rol;
- dashboard por persona;
- exportación de informes;
- separación más clara entre proyecto, tarea no programada y solicitud;
- `render.yaml` listo para despliegue;
- paso a PostgreSQL en local y producción;
- WhiteNoise y estáticos de producción;
- eliminación o reutilización formal de `ProjectTask`.

## Validación actual del proyecto

Para dar cambios por buenos durante el desarrollo se está usando:

```bash
python manage.py migrate
python manage.py test
python manage.py check
```

## Notas

- El calendario usa FullCalendar por CDN, por lo que el navegador necesita acceso a internet para cargarlo tal como está ahora.
- Los logos están en [`static/images`](./static/images).
- La interfaz está pensada como base iterativa: simple de mantener y fácil de seguir ampliando.
