import streamlit as st
import pandas as pd
from datetime import datetime, date
import calendar

st.set_page_config(page_title="Simulador Revolving", layout="wide")
st.title("💳 Simulador Revolving con Seguro Opcional y TAE Exacta")

# ---------------------------------------------------------
# FUNCIONES AUXILIARES
# ---------------------------------------------------------

def dias_ano(fecha):
    return 366 if calendar.isleap(fecha.year) else 365

def primer_recibo(fecha_inicio):
    if fecha_inicio.day < 2:
        return fecha_inicio.replace(day=2)
    if fecha_inicio.month == 12:
        return date(fecha_inicio.year + 1, 1, 2)
    return date(fecha_inicio.year, fecha_inicio.month + 1, 2)

def siguiente_recibo(fecha):
    if fecha.month == 12:
        return date(fecha.year + 1, 1, 2)
    return date(fecha.year, fecha.month + 1, 2)

# ---------------------------------------------------------
# CALCULO INTERESES
# ---------------------------------------------------------

def interes_preciso(capital, tin, fecha_inicio, fecha_fin):
    fecha_inicio = pd.to_datetime(fecha_inicio).date()
    fecha_fin = pd.to_datetime(fecha_fin).date()
    interes_diciembre = 0.0
    interes_enero = 0.0

    if fecha_fin.month == 1 and fecha_inicio.year < fecha_fin.year:
        year_prev = fecha_fin.year - 1
        year_curr = fecha_fin.year
        bisiesto_prev = calendar.isleap(year_prev)
        bisiesto_curr = calendar.isleap(year_curr)
        if bisiesto_prev != bisiesto_curr:
            dias_dic = 29
            base_dic = 366 if bisiesto_prev else 365
            interes_diciembre = round(capital * (tin / 100) * dias_dic / base_dic, 5)
            dias_ene = (fecha_fin - date(year_curr, 1, 1)).days + 1
            base_ene = 366 if bisiesto_curr else 365
            interes_enero = round(capital * (tin / 100) * dias_ene / base_ene, 5)
            interes_total = round(interes_diciembre + interes_enero, 5)
            return round(interes_total, 2), interes_diciembre, interes_enero

    dias_tramo = (fecha_fin - fecha_inicio).days
    base = dias_ano(fecha_inicio)
    interes_total = round(capital * (tin / 100) * dias_tramo / base, 5)
    return round(interes_total, 2), 0.0, interes_total

# ---------------------------------------------------------
# SIMULADOR
# ---------------------------------------------------------

def simulador(capital, tin, cuota_porcentaje, fecha_inicio, seguro_tasa=0):
    saldo = capital
    cuota = capital * (cuota_porcentaje / 100)
    fecha_pago = primer_recibo(fecha_inicio)
    fecha_anterior = fecha_inicio
    datos = []
    mes = 1

    while saldo > 0:
        interes_total, interes_diciembre, interes_enero = interes_preciso(
            saldo, tin, fecha_anterior, fecha_pago
        )
        seguro = round((saldo + interes_total) * seguro_tasa, 5)
        capital_pendiente = saldo

        if saldo + interes_total <= cuota:
            amort = saldo
            saldo = 0
            cuota_final = amort + interes_total
            recibo_total = cuota_final + seguro
            datos.append({
                "Mes": mes,
                "Fecha recibo": fecha_pago,
                "Capital pendiente (€)": round(capital_pendiente,2),
                "Cuota (€)": round(cuota_final,2),
                "Intereses diciembre (€)": interes_diciembre,
                "Intereses enero (€)": interes_enero,
                "Intereses total (€)": round(interes_total,2),
                "Amortización (€)": round(amort,2),
                "Saldo (€)": saldo,
                "Seguro (€)": round(seguro,2),
                "Recibo total (€)": round(recibo_total,2)
            })
            break

        amort = cuota - interes_total
        saldo -= amort
        recibo_total = cuota + seguro
        datos.append({
            "Mes": mes,
            "Fecha recibo": fecha_pago,
            "Capital pendiente (€)": round(capital_pendiente,2),
            "Cuota (€)": round(cuota,2),
            "Intereses diciembre (€)": interes_diciembre,
            "Intereses enero (€)": interes_enero,
            "Intereses total (€)": round(interes_total,2),
            "Amortización (€)": round(amort,2),
            "Saldo (€)": round(saldo,2),
            "Seguro (€)": round(seguro,2),
            "Recibo total (€)": round(recibo_total,2)
        })

        fecha_anterior = fecha_pago
        fecha_pago = siguiente_recibo(fecha_pago)
        mes += 1
        if mes > 600:
            break

    return pd.DataFrame(datos)

# ---------------------------------------------------------
# CALCULO TAE EXACTA
# ---------------------------------------------------------

def calcular_tae_exacta(cuotas, fechas, fecha_inicio):
    tiempos = [0.0]
    fecha_inicio = pd.to_datetime(fecha_inicio).date()
    for i in range(1, len(fechas)):
        f0 = pd.to_datetime(fechas[i-1]).date()
        f1 = pd.to_datetime(fechas[i]).date()
        fraccion = 0
        actual = f0
        while actual < f1:
            dias_en_ano = 366 if calendar.isleap(actual.year) else 365
            fin_ano = date(actual.year,12,31)
            if f1 <= fin_ano:
                dias_tramo = (f1 - actual).days
                fraccion += dias_tramo / dias_en_ano
                actual = f1
            else:
                dias_tramo = (fin_ano - actual).days + 1
                fraccion += dias_tramo / dias_en_ano
                actual = fin_ano + pd.Timedelta(days=1)
        tiempos.append(fraccion)

    def van(tasa):
        return sum(c / ((1 + tasa) ** t) for c,t in zip(cuotas, tiempos))

    minimo = -0.999999
    maximo = 10.0
    for _ in range(1000):
        medio = (minimo + maximo)/2
        valor = van(medio)
        if abs(valor) < 1e-12:
            return round(medio*100,2)
        if valor > 0:
            minimo = medio
        else:
            maximo = medio
    return round(medio*100,2)

# ---------------------------------------------------------
# INPUTS
# ---------------------------------------------------------

capital = st.number_input("Capital inicial (€)",0.0,1000000.0,6000.0)
tin = st.number_input("TIN anual (%)",0.0,100.0,21.79)
fecha_inicio = st.date_input("Fecha de financiación",datetime.today())
opciones=[2.7,3,3.5,4,5,6,7,8,9]
cuota_porcentaje=st.selectbox("Velocidad de reembolso (% del capital inicial)",opciones)

opciones_seguro = {
    "No": 0,
    "Un titular Light": 0.0035,
    "Un titular Full/Senior": 0.0061,
    "Dos titulares Full/Full": 0.0104,
    "Dos titulares Senior/Senior": 0.0104,
    "Dos titulares Light/Light": 0.0059,
    "Dos titulares Full/Light": 0.0082
}

seguro_str = st.selectbox("Seguro mensual sobre saldo pendiente + interés", list(opciones_seguro.keys()))
seguro_tasa = opciones_seguro[seguro_str]

# ---------------------------------------------------------
# CALCULO Y RESULTADOS
# ---------------------------------------------------------

if st.button("Calcular"):
    tabla = simulador(capital, tin, cuota_porcentaje, fecha_inicio, seguro_tasa)
    st.dataframe(tabla, use_container_width=True)

    total_intereses = round(tabla["Intereses total (€)"].sum(),2)
    total_seguro = round(tabla["Seguro (€)"].sum(),2)
    total_capital_intereses = round(tabla["Cuota (€)"].sum(),2)
    total_con_seguro = round(total_capital_intereses + total_seguro,2)

    cuotas_tae = [-capital] + list(tabla["Cuota (€)"])
    fechas_tae = [fecha_inicio] + list(tabla["Fecha recibo"])
    tae = calcular_tae_exacta(cuotas_tae, fechas_tae, fecha_inicio)

    resumen_dict = {
        "Concepto":[
            "Duración (meses)",
            "Intereses (€)",
            "Seguro (€) total",
            "Coste total con seguro",
            "Coste total (capital + intereses)",
            "TAE aproximada (%)"
        ],
        "Valor":[
            len(tabla),
            total_intereses,
            total_seguro,
            total_con_seguro,
            total_capital_intereses,
            tae
        ]
    }

    df_resumen = pd.DataFrame(resumen_dict)
    st.subheader("📊 Resumen en tabla")
    st.table(df_resumen)

    # ---------------------------------------------------------
    # TABLA DETALLE TAE
    # ---------------------------------------------------------

    tiempos_tae = [0.0]
    for i in range(1, len(fechas_tae)):
        f0 = pd.to_datetime(fechas_tae[i-1]).date()
        f1 = pd.to_datetime(fechas_tae[i]).date()
        fraccion = 0
        actual = f0
        while actual < f1:
            dias_en_ano = 366 if calendar.isleap(actual.year) else 365
            fin_ano = date(actual.year,12,31)
            if f1 <= fin_ano:
                dias_tramo = (f1 - actual).days
                fraccion += dias_tramo / dias_en_ano
                actual = f1
            else:
                dias_tramo = (fin_ano - actual).days + 1
                fraccion += dias_tramo / dias_en_ano
                actual = fin_ano + pd.Timedelta(days=1)
        tiempos_tae.append(round(fraccion,5))

    tabla_tae = pd.DataFrame({
        "Fecha": fechas_tae,
        "Cuota (sin seguro) (€)": cuotas_tae,
        "Tiempo (años)": tiempos_tae,
        "Valor descontado": [round(c / ((1 + tae/100) ** t),5) for c,t in zip(cuotas_tae, tiempos_tae)]
    })

    st.subheader("📈 Detalle cálculo TAE mes a mes")
    st.dataframe(tabla_tae, use_container_width=True)
