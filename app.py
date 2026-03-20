import streamlit as st
import pandas as pd
from datetime import datetime, date
import calendar
from decimal import Decimal, ROUND_HALF_UP, getcontext
from io import BytesIO

getcontext().prec = 10

st.set_page_config(page_title="Simulador Revolving", layout="wide")
st.title("💳 Simulador Revolving")

# ---------------------------------------------------------
# SELECCIÓN DEL DÍA DEL RECIBO
# ---------------------------------------------------------
dia_recibo = st.selectbox(
    "Seleccione el día del recibo (1-12)",
    options=list(range(1, 13))
)
st.write(f"Día del recibo seleccionado: {dia_recibo}")

# ---------------------------------------------------------
# FUNCIONES DE FECHAS
# ---------------------------------------------------------
def primer_recibo(fecha_inicio, dia_recibo):
    year, month = fecha_inicio.year, fecha_inicio.month
    day = min(dia_recibo, calendar.monthrange(year, month)[1])
    fecha = fecha_inicio.replace(day=day)
    if fecha < fecha_inicio:
        if month == 12:
            month = 1
            year += 1
        else:
            month += 1
        day = min(dia_recibo, calendar.monthrange(year, month)[1])
        fecha = fecha.replace(year=year, month=month, day=day)
    return fecha

def siguiente_recibo(fecha_actual):
    year, month = fecha_actual.year, fecha_actual.month + 1
    if month > 12:
        month = 1
        year += 1
    day = min(fecha_actual.day, calendar.monthrange(year, month)[1])
    return fecha_actual.replace(year=year, month=month, day=day)

# ---------------------------------------------------------
# FUNCIONES AUXILIARES
# ---------------------------------------------------------

def dias_ano(fecha):
    if isinstance(fecha, pd.Timestamp):
        fecha = fecha.date()
    return 366 if calendar.isleap(fecha.year) else 365

def interes_preciso(capital, tin, fecha_inicio, fecha_fin):
    """
    Calcula los intereses exactos de un capital entre fecha_inicio y fecha_fin,
    desglosando diciembre y enero solo si hay cambio de base (bisiesto/no bisiesto).
    Ajuste: ya no suma +1 a los días de diciembre.
    """
    capital = Decimal(str(capital))
    tin = Decimal(str(tin)) / Decimal("100")
    fecha_inicio = pd.to_datetime(fecha_inicio).date()
    fecha_fin = pd.to_datetime(fecha_fin).date()

    interes_diciembre = Decimal("0")
    interes_enero = Decimal("0")

    # Detectar cruce de año
    if fecha_fin.year != fecha_inicio.year:
        # Solo dividir si los años tienen distinto número de días
        base_inicio = 366 if calendar.isleap(fecha_inicio.year) else 365
        base_fin = 366 if calendar.isleap(fecha_fin.year) else 365

        if base_inicio != base_fin:
            # Interés diciembre (año inicial)
            fin_dic = date(fecha_inicio.year, 12, 31)
            dias_dic = (fin_dic - fecha_inicio).days  # ⚡ Ajuste aquí, no +1
            interes_diciembre = (capital * tin * Decimal(dias_dic) / Decimal(base_inicio)).quantize(Decimal("0.00001"))

            # Interés enero (año siguiente)
            inicio_ene = date(fecha_fin.year, 1, 1)
            dias_ene = (fecha_fin - inicio_ene).days + 1  # enero sí mantiene +1
            interes_enero = (capital * tin * Decimal(dias_ene) / Decimal(base_fin)).quantize(Decimal("0.00001"))

            interes_total = (interes_diciembre + interes_enero).quantize(Decimal("0.00001"))
            return interes_total, interes_diciembre, interes_enero

    # Caso normal (mismo año o años con misma base)
    dias_tramo = (fecha_fin - fecha_inicio).days
    base = dias_ano(fecha_inicio)
    interes_total = (capital * tin * Decimal(dias_tramo) / Decimal(base)).quantize(Decimal("0.00001"))
    return interes_total, Decimal("0"), interes_total

# ---------------------------------------------------------
# SIMULADOR
# ---------------------------------------------------------
def simulador(capital, tin, tipo_calculo, valor, fecha_inicio, seguro_tasa=0, dia_recibo=2):
    capital = Decimal(str(capital))
    saldo = capital
    seguro_tasa = Decimal(str(seguro_tasa))
    fecha_pago = primer_recibo(fecha_inicio, dia_recibo)
    fecha_anterior = fecha_inicio
    datos = []
    mes = 1

    if tipo_calculo == "Vitesse":
        cuota = (capital * Decimal(str(valor)) / Decimal("100")).quantize(Decimal("0.01"), ROUND_HALF_UP)
    elif tipo_calculo == "Cuota":
        cuota = Decimal(str(valor)).quantize(Decimal("0.01"), ROUND_HALF_UP)

    while saldo > 0:
        interes_total, interes_dic, interes_ene = interes_preciso(saldo, tin, fecha_anterior, fecha_pago)
        interes_total = interes_total.quantize(Decimal("0.01"), ROUND_HALF_UP)
        seguro = ((saldo + interes_total) * seguro_tasa).quantize(Decimal("0.01"), ROUND_HALF_UP)

        if saldo + interes_total <= cuota:
            amort = saldo.quantize(Decimal("0.01"), ROUND_HALF_UP)
            saldo = Decimal("0")
            cuota_final = (amort + interes_total).quantize(Decimal("0.01"), ROUND_HALF_UP)
        else:
            amort = (cuota - interes_total).quantize(Decimal("0.01"), ROUND_HALF_UP)
            saldo = (saldo - amort).quantize(Decimal("0.01"), ROUND_HALF_UP)
            cuota_final = cuota

        datos.append({
            "Mes": mes,
            "Fecha recibo": fecha_pago,
            "Capital pendiente (€)": float(saldo + amort),
            "Cuota (€)": float(cuota_final),
            "Intereses diciembre (€)": float(interes_dic),
            "Intereses enero (€)": float(interes_ene),
            "Intereses total (€)": float(interes_total),
            "Amortización (€)": float(amort),
            "Saldo (€)": float(saldo),
            "Seguro (€)": float(seguro),
            "Recibo total (€)": float(cuota_final + seguro)
        })

        fecha_anterior = fecha_pago
        fecha_pago = siguiente_recibo(fecha_pago)
        mes += 1
        if mes > 600:  # seguridad
            break

    return pd.DataFrame(datos)

# ---------------------------------------------------------
# CALCULO TAE
# ---------------------------------------------------------

def calcular_tae(cuotas, fechas, capital, tin, duracion):
    """
    Calcula la TAE:
    - Si capital < 6000 €, se usa aproximación: TAE ≈ (1 + TIN/12)^duración - 1
    - Si capital >= 6000 €, se calcula mediante VAN iterativo con flujos y fechas
    """
    if capital < 6000:
        # TIN mensual
        r = Decimal(str(tin)) / Decimal("100") / Decimal("12")
        tae = ((1 + r) ** Decimal(str(duracion)) - 1) * 100
        return round(float(tae), 2)

    # Cálculo normal para capital >= 6000
    tiempos = [0.0]
    for i in range(1, len(fechas)):
        f0 = pd.to_datetime(fechas[i-1]).date()
        f1 = pd.to_datetime(fechas[i]).date()
        fraccion = (f1 - f0).days / dias_ano(f0)
        tiempos.append(tiempos[-1] + fraccion)

    def van(tasa):
        return sum(c / ((1 + tasa) ** t) for c, t in zip(cuotas, tiempos))

    minimo, maximo = -0.9999, 10
    for _ in range(1000):
        medio = (minimo + maximo) / 2
        valor = van(medio)
        if abs(valor) < 1e-10:
            return round(medio * 100, 2)
        if valor > 0:
            minimo = medio
        else:
            maximo = medio
    return round(medio * 100, 2)


# ------------------------------
from decimal import Decimal
from datetime import datetime, date
import pandas as pd

# ------------------------------
# Preparar flujos y fechas para TAE
# ------------------------------

if capital is None:
    st.error("Debes introducir un importe de financiación.")
    st.stop()

# Primer flujo: capital recibido (negativo)
flujos = [-float(Decimal(str(capital)))]

# Todas las cuotas de la tabla (sin seguro ni comisión), convertidas a float seguro
cuotas_lista = pd.to_numeric(tabla["Cuota (€)"], errors='coerce').fillna(0).astype(float).tolist()
flujos += cuotas_lista

# Fechas correspondientes a los flujos
fechas = [fecha_inicio] + list(tabla["Fecha"])

# Convertir todas las fechas a tipo date seguro
fechas_tae = []
for f in fechas:
    if isinstance(f, pd.Timestamp):
        fechas_tae.append(f.date())
    elif isinstance(f, datetime):
        fechas_tae.append(f.date())
    elif isinstance(f, date):
        fechas_tae.append(f)
    else:
        raise ValueError(f"Tipo de fecha no esperado: {type(f)}")

# Calcular TAE
tae = calcular_tae(flujos, fechas_tae, float(capital), float(tin), int(duracion))
st.write(f"📈 TAE calculada: {tae} %")
# ---------------------------------------------------------
# INPUTS
# ---------------------------------------------------------
vitesse_valores = [2.7,2.75,3,3.25,3.43,4.37,5.17,6.57,9.37]

capital = st.number_input("Importe de financiación (€)", 0.0, 1000000.0, 6000.0)
tin = st.number_input("TIN anual (%)", 0.0, 100.0, 21.79)
fecha_inicio = st.date_input("Fecha de financiación", datetime.today())
tipo_calculo = st.selectbox("Tipo de cálculo", ["Seleccionar", "Vitesse", "Cuota", "Duración"])
valor = None

if tipo_calculo == "Vitesse":
    valor = st.selectbox("Vitesse (%)", vitesse_valores)
elif tipo_calculo == "Cuota":
    opciones_cuota = [round(capital * v / 100, 2) for v in vitesse_valores]
    valor = st.selectbox("Cuota mensual (€)", opciones_cuota)
elif tipo_calculo == "Duración":
    opciones_duracion = []
    mapa_vitesse = {}
    for v in vitesse_valores:
        cuota_test = round(capital * v / 100, 2)
        tabla_test = simulador(capital, tin, "Cuota", cuota_test, fecha_inicio, 0, dia_recibo)
        meses = len(tabla_test)
        etiqueta = f"{meses} meses"
        opciones_duracion.append(etiqueta)
        mapa_vitesse[etiqueta] = v
    seleccion = st.selectbox("Duración del préstamo", opciones_duracion)
    valor = mapa_vitesse[seleccion]
    tipo_calculo = "Vitesse"

# ---------------------------------------------------------
# SEGURO
# ---------------------------------------------------------
opciones_seguro = {
    "No":0,
    "Un titular Light":0.0035,
    "Un titular Full/Senior":0.0061,
    "Dos titulares Full/Full":0.0104,
    "Dos titulares Senior/Senior":0.0104,
    "Dos titulares Light/Light":0.0059,
    "Dos titulares Full/Light":0.0082
}
seguro_str = st.selectbox("Seguro mensual", list(opciones_seguro.keys()))
seguro_tasa = opciones_seguro[seguro_str]

# ---------------------------------------------------------
# RESULTADOS
# ---------------------------------------------------------
if st.button("Calcular") and valor is not None:
    tabla = simulador(capital, tin, tipo_calculo, valor, fecha_inicio, seguro_tasa, dia_recibo)

    if seguro_tasa == 0 and "Seguro (€)" in tabla.columns:
        tabla = tabla.drop(columns=["Seguro (€)"])

    st.dataframe(tabla, use_container_width=True)

    total_intereses = round(tabla["Intereses total (€)"].sum(), 2)
    total_capital_intereses = round(tabla["Cuota (€)"].sum(), 2)
    total_seguro = round(tabla["Seguro (€)"].sum(), 2) if seguro_tasa > 0 else 0

    cuotas_tae = [-capital] + list(tabla["Cuota (€)"])
    fechas_tae = [fecha_inicio] + list(tabla["Fecha recibo"])
    tae = calcular_tae(flujos, fechas, float(capital), float(tin), int(duracion))

    # Resumen
    resumen_dict = {
        "Concepto": ["Duración (meses)", "Intereses (€)"] + (["Seguro (€) total"] if seguro_tasa > 0 else []) + ["Coste total (capital+intereses)"] + (["Coste total (capital+intereses+seguro)"] if seguro_tasa > 0 else []) + ["TAE (%)"],
        "Valor": [len(tabla), total_intereses] + ([total_seguro] if seguro_tasa > 0 else []) + [total_capital_intereses] + ([round(total_capital_intereses + total_seguro,2)] if seguro_tasa > 0 else []) + [tae]
    }
    df_resumen = pd.DataFrame(resumen_dict)
    st.subheader("Resumen")
    st.table(df_resumen)

    # Exportar a Excel
    output = BytesIO()
    with pd.ExcelWriter(output) as writer:
        tabla.to_excel(writer, sheet_name="Cuadro Amortización", index=False)
        df_resumen.to_excel(writer, sheet_name="Resumen", index=False)
    excel_data = output.getvalue()
    st.download_button(
        label="📥 Descargar cuadro de amortización en Excel",
        data=excel_data,
        file_name="simulacion_revolving.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
