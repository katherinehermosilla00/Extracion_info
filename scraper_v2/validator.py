def _a_dict(valor):
    if valor is None:
        return {}

    if isinstance(valor, dict):
        return valor

    if hasattr(valor, "model_dump"):
        return valor.model_dump()

    return {}


def validar_tour(tour) -> dict:
    """
    Valida una actividad antes de permitir su guardado.

    No modifica los datos extraidos.
    No inventa informacion faltante.
    """

    if hasattr(tour, "model_dump"):
        datos = tour.model_dump()
    elif isinstance(tour, dict):
        datos = tour
    else:
        datos = {}

    errores = []
    advertencias = []

    # -----------------------------------------------------
    # NOMBRE
    # -----------------------------------------------------

    nombre = str(
        datos.get("nombre") or ""
    ).strip()

    if not nombre:
        errores.append({
            "campo": "nombre",
            "codigo": "nombre_faltante",
            "mensaje": (
                "La actividad no tiene nombre."
            ),
        })

    # -----------------------------------------------------
    # DESCRIPCION
    # -----------------------------------------------------

    descripcion = str(
        datos.get("descripcion_original")
        or datos.get("descripcion_corta")
        or ""
    ).strip()

    if not descripcion:
        errores.append({
            "campo": "descripcion",
            "codigo": "descripcion_faltante",
            "mensaje": (
                "La actividad no tiene descripcion."
            ),
        })

    # -----------------------------------------------------
    # IMAGENES
    # -----------------------------------------------------

    imagenes = datos.get("imagenes") or []

    imagenes_validas = [
        imagen
        for imagen in imagenes
        if isinstance(imagen, str)
        and imagen.strip()
    ]

    if len(imagenes_validas) < 4:
        errores.append({
            "campo": "imagenes",
            "codigo": "imagenes_insuficientes",
            "mensaje": (
                "Se requieren al menos 4 imagenes "
                "turisticas validas."
            ),
            "cantidad": len(imagenes_validas),
            "minimo": 4,
        })

    # -----------------------------------------------------
    # UBICACION
    # -----------------------------------------------------

    ubicacion = _a_dict(
        datos.get("ubicacion")
    )

    campos_ubicacion = (
        "pais",
        "region",
        "ciudad",
        "direccion",
    )

    valores_ubicacion = [
        str(
            ubicacion.get(campo) or ""
        ).strip()
        for campo in campos_ubicacion
    ]

    cantidad_ubicacion = sum(
        bool(valor)
        for valor in valores_ubicacion
    )

    if cantidad_ubicacion == 0:
        errores.append({
            "campo": "ubicacion",
            "codigo": "ubicacion_faltante",
            "mensaje": (
                "No se pudo determinar la ubicacion."
            ),
        })

    elif cantidad_ubicacion == 1:
        advertencias.append({
            "campo": "ubicacion",
            "codigo": "ubicacion_incompleta",
            "mensaje": (
                "La ubicacion tiene poca informacion."
            ),
        })

    # -----------------------------------------------------
    # CALENDARIO
    # -----------------------------------------------------

    calendario = _a_dict(
        datos.get("calendario")
    )

    tipo_calendario = str(
        calendario.get("tipo")
        or "desconocido"
    ).strip().lower()

    if tipo_calendario in (
        "",
        "desconocido",
        "none",
    ):
        advertencias.append({
            "campo": "calendario",
            "codigo": "calendario_no_resuelto",
            "mensaje": (
                "No se pudo resolver el calendario "
                "publicado por el operador."
            ),
        })

    dias = calendario.get("dias") or []
    horarios = calendario.get(
        "horarios"
    ) or []
    evidencia = calendario.get(
        "evidencia"
    ) or []

    if (
        tipo_calendario
        != "desconocido"
        and not dias
        and not horarios
        and not evidencia
    ):
        advertencias.append({
            "campo": "calendario",
            "codigo": "calendario_sin_detalle",
            "mensaje": (
                "Existe referencia de calendario, "
                "pero no contiene detalle verificable."
            ),
        })

    # -----------------------------------------------------
    # SOURCE URL
    # -----------------------------------------------------

    source_url = str(
        datos.get("source_url") or ""
    ).strip()

    if not source_url:
        errores.append({
            "campo": "source_url",
            "codigo": "fuente_faltante",
            "mensaje": (
                "La ficha no conserva la URL fuente."
            ),
        })

    # -----------------------------------------------------
    # RESULTADO
    # -----------------------------------------------------

    lista_para_guardar = (
        len(errores) == 0
    )

    return {
        "estado": (
            "lista_para_guardar"
            if lista_para_guardar
            else "requiere_revision"
        ),
        "lista_para_guardar": (
            lista_para_guardar
        ),
        "errores_bloqueantes": errores,
        "advertencias": advertencias,
        "resumen": {
            "nombre": bool(nombre),
            "descripcion": bool(
                descripcion
            ),
            "imagenes_validas": len(
                imagenes_validas
            ),
            "ubicacion_campos": (
                cantidad_ubicacion
            ),
            "calendario_tipo": (
                tipo_calendario
            ),
        },
    }
