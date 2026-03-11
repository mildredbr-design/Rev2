import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
import calendar
from decimal import Decimal, getcontext, ROUND_HALF_UP

# ---------------------------------------------------------
# CONFIGURACIÓN DECIMAL
# ---------------------------------------------------------
getcontext().prec = 12

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
# CALCULO INTERESES CON DECIMAL
# ---------------------------------------------------------
def interes_preciso(capital, tin, fecha_inicio, fecha_fin):
    fecha_inicio = pd.to_datetime(fecha_inicio).date()
    fecha_fin = pd.to_datetime(fecha_fin).date()
    capital = Decimal(capital)
    tin = Decimal(tin)
    interes_diciembre = Decimal('0.0')
    interes_enero = Decimal('0.0')

    if fecha_fin.month == 1 and fecha_inicio.year < fecha_fin.year:
        year_prev = fecha_fin.year - 1
        year_curr = fecha_fin.year
        bisiesto_prev = calendar.isleap(year_prev)
        bisiesto_curr = calendar.isleap(year_curr)
        if bisiesto_prev != bisiesto_curr:
            dias_dic = 29
            base_dic = Decimal(366 if bisiesto_prev else 365)
            interes_diciembre = capital * tin / Decimal('100') * Decimal(dias_dic) / base_dic
            dias_ene = (fecha_fin - date(year_curr, 1, 1)).days + 1
            base_ene = Decimal(366 if bisiesto_curr else 365)
            interes_enero = capital * tin / Decimal('100') * Decimal(dias_ene) / base_ene
            interes_total = interes_diciembre + interes_enero
            return interes_total, interes_diciembre, interes_enero

    dias_tramo = (fecha_fin - fecha_inicio).days
    base = Decimal(dias_ano(fecha_inicio))
    interes_total = capital * tin / Decimal('100') * Decimal(dias_tramo) / base
    return interes_total, Decimal('0.0'), interes_total

# ---------------------------------------------------------
# SIMULADOR
# ---------------------------------------------------------
def simulador(capital, tin, cuota_porcentaje, fecha_inicio, seguro_tasa=0):
    saldo = Decimal(capital)
    cuota_precisa = (Decimal(capital) * Decimal(cuota_porcentaje)/Decimal('100'))
    tin = Decimal(tin)
    fecha_pago = primer_recibo(fecha_inicio)
    fecha_anterior = fecha_inicio
    datos = []
    mes = 1

    while saldo > 0:
        interes_total_preciso, interes_dic, interes_ene = interes_preciso(
            saldo, tin, fecha_anterior, fecha_pago
        )
        seguro = (saldo + interes_total_preciso) * Decimal(seguro_tasa)
        capital_pendiente = saldo

        if saldo + interes_total_preciso <= cuota_precisa:
            amort = saldo
            saldo = Decimal('0.0')
            cuota_final = amort + interes_total_preciso
        else:
            amort = cuota_precisa - interes_total_preciso
            saldo -= amort
            cuota_final = cuota_precisa

        # Convertimos a str con quantize para mostrar exactamente 2 decimales
        datos.append({
            "Mes": mes,
            "Fecha recibo": fecha_pago,
            "Capital pendiente (€)": str(capital_pendiente.quantize(Decimal('0.01'), ROUND_HALF_UP)),
            "Cuota (€)": str(cuota_final.quantize(Decimal('0.01'), ROUND_HALF_UP)),
            "Intereses diciembre (€)": str(interes_dic.quantize(Decimal('0.01'), ROUND_HALF_UP)),
            "Intereses enero (€)": str(interes_ene.quantize(Decimal('0.01'), ROUND_HALF_UP)),
            "Intereses total (€)": str(interes_total_preciso.quantize(Decimal('0.01'), ROUND_HALF_UP)),
            "Amortización (€)": str(amort.quantize(Decimal('0.01'), ROUND_HALF_UP)),
            "Saldo (€)": str(saldo.quantize(Decimal('0.01'), ROUND_HALF_UP)),
            "Seguro (€)": str(seguro.quantize(Decimal('0.01'), ROUND_HALF_UP)),
            "Recibo total (€)": str((cuota_final + seguro).quantize(Decimal('0.01'), ROUND_HALF_UP))
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
    fecha_inicio = pd.to_datetime(fecha_inicio).date()
    tiempos = [Decimal('0.0')]

    for i in range(1, len(fechas)):
        f0 = pd.to_datetime(fechas[i-1]).date()
        f1 = pd.to_datetime(fechas[i]).date()
        fraccion = Decimal('0.0')
        actual = f0

        while actual < f1:
            dias_en_ano = Decimal(366 if calendar.isleap(actual.year) else 365)
            fin_ano = date(actual.year, 12, 31)
            if f1 <= fin_ano:
                dias_tramo = Decimal((f1 - actual).days)
                fraccion += dias_tramo / dias_en_ano
                actual = f1
            else:
                dias_tramo = Decimal((fin_ano - actual).days + 1)
                fraccion += dias_tramo / dias_en_ano
                actual = fin_ano + timedelta(days=1)

        tiempos.append(tiempos[-1] + fraccion)

    def van(tasa):
        return sum(Decimal(c) / (Decimal('1.0') + Decimal(tasa)) ** Decimal(t) for c,t in zip(cuotas, tiempos))

    minimo = Decimal('-0.999999')
    maximo = Decimal('10.0')
    for _ in range(1000):
        medio = (minimo + maximo)/Decimal('2.0')
        valor = van(medio)
        if abs(valor) < Decimal('1e-12'):
            return float((medio*Decimal('100')).quantize(Decimal('0.01'), ROUND_HALF_UP)), tiempos
        if valor > 0:
            minimo = medio
        else:
            maximo = medio
    return float((medio*Decimal('100')).quantize(Decimal('0.01'), ROUND_HALF_UP)), tiempos

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

    total_intereses = sum(Decimal(v) for v in tabla["Intereses total (€)"])
    total_seguro = sum(Decimal(v) for v in tabla["Seguro (€)"])
    total_capital_intereses = sum(Decimal(v) for v in tabla["Cuota (€)"])
    total_con_seguro = total_capital_intereses + total_seguro

    cuotas_tae = [-Decimal(capital)] + [Decimal(a)+Decimal(i) for a,i in zip(tabla["Amortización (€)"], tabla["Intereses total (€)"])]
    fechas_tae = [fecha_inicio] + list(tabla["Fecha recibo"])
    tae, tiempos_exactos = calcular_tae_exacta(cuotas_tae, fechas_tae, fecha_inicio)

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
            str(total_intereses.quantize(Decimal('0.01'), ROUND_HALF_UP)),
            str(total_seguro.quantize(Decimal('0.01'), ROUND_HALF_UP)),
            str(total_con_seguro.quantize(Decimal('0.01'), ROUND_HALF_UP)),
            str(total_capital_intereses.quantize(Decimal('0.01'), ROUND_HALF_UP)),
            tae
        ]
    }

    df_resumen = pd.DataFrame(resumen_dict)
    st.subheader("📊 Resumen en tabla")
    st.table(df_resumen)
