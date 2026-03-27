# AGENTS.md

## Objetivo del proyecto
Crear una aplicación web en **Django 5.2** para gestionar y visualizar cronologías de trabajo a medio y largo plazo.

La aplicación debe permitir:
- Registrar **proyectos** desde el panel de administración.
- Registrar **partes/fases/tareas** dentro de cada proyecto.
- Asignar a cada parte una **estimación de tiempo**.
- Llevar un **diario de trabajo** donde se pueda anotar qué se ha hecho cada día y cuánto tiempo se ha dedicado.
- Recalcular automáticamente la cronología cuando el tiempo real invertido o las tareas externas modifiquen la planificación prevista.
- Mostrar una **línea de tiempo cronológica** en una vista sencilla (`index.html`) alimentada por los datos almacenados.
- Permitir desde esa misma interfaz añadir o editar lo realizado en el día actual o en días anteriores, actualizando inmediatamente la línea de tiempo.

---

## Descripción funcional
La aplicación está orientada a planificación y seguimiento real del trabajo.

### Entidades principales
1. **Proyecto**
   - Nombre
   - Descripción
   - Fecha de inicio prevista
   - Estado
   - Prioridad
   - Observaciones opcionales

2. **Parte de proyecto / fase / tarea planificada**
   - Relacionada con un proyecto
   - Nombre
   - Descripción
   - Orden dentro del proyecto
   - Tiempo estimado
   - Fecha prevista opcional de inicio
   - Fecha prevista opcional de fin
   - Estado

3. **Entrada diaria / registro de actividad**
   - Fecha
   - Proyecto relacionado (opcional si fue una tarea no planificada o externa)
   - Parte del proyecto relacionada (opcional)
   - Descripción de lo realizado
   - Tiempo real invertido
   - Tipo de trabajo:
     - trabajo de proyecto
     - tarea externa
     - interrupción
     - mantenimiento
     - otros
   - Observaciones

### Comportamiento esperado
- El administrador puede crear y editar proyectos y partes del proyecto desde Django Admin.
- El sistema debe usar las estimaciones de cada parte para construir una planificación temporal.
- Cuando se añaden registros diarios:
  - si el tiempo se dedica a una parte del proyecto, debe reflejarse como avance real;
  - si el tiempo se dedica a otras tareas no previstas, la cronología futura debe desplazarse/postergarse automáticamente;
  - la línea de tiempo debe reflejar siempre una combinación de:
    - planificación estimada,
    - progreso real,
    - retrasos acumulados.

---

## Objetivo de la interfaz pública
La página principal (`index.html`) debe ser sencilla, clara y funcional.

Debe mostrar:
- Los proyectos en orden cronológico.
- Sus partes/fases.
- El estado de avance.
- La duración estimada.
- El tiempo real registrado.
- Los retrasos o desplazamientos acumulados.
- Una representación simple de línea de tiempo, sin necesidad de una UI compleja al inicio.

También debe permitir:
- Añadir una entrada de trabajo del día actual.
- Editar entradas anteriores.
- Actualizar la cronología inmediatamente tras guardar cambios.

---

## Requisitos técnicos
- Usar **Django 5.2**.
- Priorizar una arquitectura simple, mantenible y clara.
- Usar Django Admin para la gestión inicial de datos.
- Evitar dependencias innecesarias en la primera versión.
- La primera implementación puede usar plantillas de Django renderizadas en servidor.
- La actualización de la línea de tiempo puede resolverse inicialmente con recarga de página tras guardar.
- La lógica de planificación debe estar desacoplada de las vistas para facilitar pruebas.

---

## Alcance de la primera versión
La V1 debe incluir como mínimo:
- Modelos de datos para proyectos, partes y registros diarios.
- Configuración completa de Django Admin.
- Vista `index.html` con cronología básica.
- Formulario para añadir/editar registros diarios.
- Recalculo automático de la cronología en base a:
  - estimaciones iniciales,
  - tiempo realmente trabajado,
  - tareas externas que consumen tiempo disponible.

No es prioritario en V1:
- autenticación compleja
- API REST
- frontend SPA
- drag & drop
- gráficos avanzados
- calendario complejo
- multiusuario avanzado

---

## Reglas de implementación
- No refactorizar grandes áreas del proyecto sin necesidad.
- Implementar por fases pequeñas y verificables.
- Antes de tocar código, proponer subtareas si la tarea es amplia.
- Mantener los cambios enfocados en el alcance solicitado.
- No añadir librerías JS o Python sin justificarlo.
- No complicar la UI en la primera fase.

---

## Orden recomendado de desarrollo
1. Crear estructura base del proyecto Django.
2. Definir modelos.
3. Registrar y mejorar Django Admin.
4. Implementar lógica de cálculo de cronología.
5. Crear vista `index.html`.
6. Añadir formulario de registro diario.
7. Permitir edición de registros anteriores.
8. Conectar guardado de registros con recálculo de la línea de tiempo.
9. Añadir pruebas básicas de modelos y lógica de planificación.

---

## Lógica de planificación esperada
La línea de tiempo no debe ser estática.

El sistema debe:
- partir de una estimación inicial por partes del proyecto;
- descontar el trabajo real realizado;
- detectar tiempo invertido en tareas ajenas al proyecto;
- desplazar automáticamente el trabajo pendiente hacia adelante en el tiempo;
- recalcular la proyección futura de finalización.

La prioridad es que la cronología sea **coherente, entendible y útil**, aunque la fórmula inicial sea simple.

---

## Criterios de aceptación generales
Una tarea se considera terminada solo si:
1. El código funciona dentro del alcance pedido.
2. No rompe funcionalidades existentes.
3. La cronología se recalcula de forma coherente.
4. Los formularios y vistas básicas funcionan.
5. Los cambios quedan explicados de forma breve.
6. Se ejecutan las validaciones relevantes antes de dar la tarea por cerrada.

---

## Validación obligatoria
Antes de cerrar cualquier subtarea:
1. Ejecutar migraciones si aplica.
2. Verificar que Django arranca correctamente.
3. Ejecutar tests afectados.
4. Revisar errores de plantilla, modelos, admin y formularios.
5. Resumir archivos modificados y motivo.

---

## Estilo de trabajo esperado para Codex
- Si una petición es grande, dividirla en microtareas antes de implementarla.
- Trabajar una microtarea cada vez.
- Explicar supuestos cuando falte contexto.
- Priorizar claridad sobre sofisticación.
- Mantener el proyecto listo para seguir iterando.