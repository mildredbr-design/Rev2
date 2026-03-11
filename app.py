def interes_preciso(capital, tin, fecha_financiacion, fecha_vencimiento):
    """
    Calcula intereses exactos de un periodo, usando la misma lógica de fracción de año
    que la función de TAE, respetando cambios bisiesto/no bisiesto.
    """
    fecha_financiacion = pd.to_datetime(fecha_financiacion)
    fecha_vencimiento = pd.to_datetime(fecha_vencimiento)

    # Días del año del vencimiento
    w_dia_año = 366 if calendar.isleap(fecha_vencimiento.year) else 365
    w_dia_año_anterior = 366 if calendar.isleap(fecha_vencimiento.year - 1) else 365

    if fecha_vencimiento.year == fecha_financiacion.year:
        w_dia_año_anterior = w_dia_año

    # Delta años
    delta_años = max(fecha_vencimiento.year - fecha_financiacion.year + 1, 0)
    w_aniversario_fecha_financiacion = fecha_financiacion + pd.DateOffset(years=delta_años)

    # Cálculo fracción de año exacta (igual que TAE)
    if w_dia_año != w_dia_año_anterior and fecha_vencimiento < w_aniversario_fecha_financiacion:
        delta_años = delta_años - 2 if delta_años > 1 else 0
        w_aniversario_fecha_financiacion += pd.DateOffset(years=-1)
        fraccion_año = (
            delta_años +
            ((w_dia_año_anterior - w_aniversario_fecha_financiacion.dayofyear) / w_dia_año_anterior) +
            (fecha_vencimiento.dayofyear / w_dia_año)
        )
    elif fecha_vencimiento > w_aniversario_fecha_financiacion:
        fraccion_año = (
            (0 if delta_años < 1 else delta_años) +
            ((fecha_vencimiento.dayofyear - w_aniversario_fecha_financiacion.dayofyear) / w_dia_año)
        )
    else:
        delta_años = delta_años - 1 if delta_años > 1 else 0
        w_aniversario_fecha_financiacion += pd.DateOffset(years=-1)
        fraccion_año = (
            delta_años +
            ((fecha_vencimiento.dayofyear - w_aniversario_fecha_financiacion.dayofyear) / w_dia_año)
        )

    # Interés exacto
    interes = capital * (tin / 100) * fraccion_año
    return round(interes, 2)
