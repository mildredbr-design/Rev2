import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
import calendar
from decimal import Decimal, ROUND_HALF_UP, getcontext

getcontext().prec = 10

st.set_page_config(page_title="Simulador Revolving Completo", layout="wide")
st.title("💳 Simulador Revolving con Tipo de Cálculo Avanzado y TAE Exacta")

# -------------------------------
# FUNCIONES AUXILIARES
# -------------------------------
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

# -------------------------------
# CALCULO INTERESES CON BISESTO
# -------------------------------
def calcular_interes(capital, tin, inicio, fin):
    capital = Decimal(str(capital))
    tin_decimal = Decimal(str(tin)) / Decimal("100")
    inicio = pd.to_datetime(inicio).date()
    fin = pd.to_datetime(fin).date()

    # Ajuste diciembre/enero con cambio bisiesto
    if fin.month == 1 and inicio.year < fin.year:
        year_prev = inicio.year
        year_curr = fin.year
        bisiesto_prev = calendar.isleap(year_prev)
        bisiesto_curr = calendar.isleap(year_curr)
        if bisiesto_prev != bisiesto_curr:
            dias_dic = 29
            base_dic = 366 if bisiesto_prev else 365
            interes_dic = (capital * tin_decimal * Decimal(dias_dic) / Decimal(base_dic)).quantize(Decimal("0.00001"))
            dias_ene = (fin - date(year_curr, 1, 1)).days + 1
            base_ene = 366 if bisiesto_curr else 365
            interes_ene = (capital * tin_decimal * Decimal(dias_ene) / Decimal(base_ene)).quantize(Decimal("0.00001"))
            total = (interes_dic + interes_ene).quantize(Decimal("0.00001"))
            return total, interes_dic, interes_ene

    dias_tramo = (fin - inicio).days
    base = dias_ano(inicio)
    total = (capital * tin_decimal * Decimal(dias_tramo) / Decimal(base)).quantize(Decimal("0.00001"))
    return total, Decimal("0.0"), total

# -------------------------------
# SIMULADOR
# -------------------------------
def simulador(capital, tin, tipo_calculo, valor, fecha_inicio, seguro_tasa=0):
    capital = Decimal(str(capital))
    seguro_tasa = Decimal(str(seguro_tasa))
    saldo = capital
    fecha_pago = primer_recibo(fecha_inicio)
    fecha_anterior = fecha_inicio
    datos = []
    mes = 1

    vitesse_valores = [2.7, 2.75, 3, 3.25, 3.43, 4.37, 5.17, 6.57, 9.37]

    # Definir la cuota inicial según tipo de cálculo
    if tipo_calculo == "Vitesse":
        cuota = (capital * Decimal(str(valor)) / Decimal("100")).quantize(Decimal("0.01"), ROUND_HALF_UP)
    elif tipo_calculo == "Cuota":
        cuota = Decimal(str(valor)).quantize(Decimal("0.01"), ROUND_HALF_UP)
    else:  # Duración
        meses = int(valor)
        cuota = (capital / Decimal(meses)).quantize(Decimal("0.01"), ROUND_HALF_UP)

    while saldo > 0:
        interes_total, interes_dic, interes_ene = calcular_interes(saldo, tin, fecha_anterior, fecha_pago)
        interes_total_mostrar = interes_total.quantize(Decimal("0.01"), ROUND_HALF_UP)
        interes_dic_mostrar = interes_dic.quantize(Decimal("0.01"), ROUND_HALF_UP)
        interes_ene_mostrar = interes_ene.quantize(Decimal("0.01"), ROUND_HALF_UP)

        seguro = ((saldo + interes_total_mostrar) * seguro_tasa).quantize(Decimal("0.01"), ROUND_HALF_UP)

        if saldo + interes_total_mostrar <= cuota:
            amort = saldo.quantize(Decimal("0.01"), ROUND_HALF_UP)
            saldo = Decimal("0.00")
            cuota_final = (amort + interes_total_mostrar).quantize(Decimal("0.01"), ROUND_HALF_UP)
        else:
            amort = (cuota - interes_total_mostrar).quantize(Decimal("0.01"), ROUND_HALF_UP)
            saldo = (saldo - amort).quantize(Decimal("0.01"), ROUND_HALF_UP)
            cuota_final = cuota

        datos.append({
            "Mes": mes,
            "Fecha recibo": fecha_pago,
            "Capital pendiente (€)": float(saldo + amort),
            "Cuota (€)": float(cuota_final),
            "Intereses diciembre (€)": float(interes_dic_mostrar),
            "Intereses enero (€)": float(interes_ene_mostrar),
            "Intereses total (€)": float(interes_total_mostrar),
            "Amortización (€)": float(amort),
            "Saldo (€)": float(saldo),
            "Seguro (€)": float(seguro),
            "Recibo total (€)": float(cuota_final + seguro)
        })

        fecha_anterior = fecha_pago
        fecha_pago = siguiente_recibo(fecha_pago)
        mes += 1
        if mes > 600:
            break

    return pd.DataFrame(datos)

# -------------------------------
# CALCULO TAE EXACTA
# -------------------------------
def calcular_tae(cuotas, fechas):
    tiempos = [0.0]
    for i in range(1, len(fechas)):
        f0 = pd.to_datetime(fechas[i-1]).date()
        f1 = pd.to_datetime(fechas[i]).date()
        fraccion = 0
        actual = f0
        if i == 1:
            delta = (f1 - f0).days + 1
            fraccion = delta / dias_ano(f0)
        else:
            while actual < f1:
                dias_en_ano = 366 if calendar.isleap(actual.year) else 365
                fin_ano = date(actual.year, 12, 31)
                if f1 <= fin_ano:
                    dias_tramo = (f1 - actual).days
                    fraccion += dias_tramo / dias_en_ano
                    actual = f1
                else:
                    dias_tramo = (fin_ano - actual).days + 1
                    fraccion += dias_tramo / dias_en_ano
                    actual = fin_ano + timedelta(days=1)
        tiempos.append(tiempos[-1] + fraccion)

    def van(tasa):
        return sum(c / ((1 + tasa) ** t) for c, t in zip(cuotas, tiempos))

    minimo, maximo = -0.999999, 10.0
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

# -------------------------------
# INTERFAZ STREAMLIT
# -------------------------------
tipo_calculo = st.selectbox("Tipo de cálculo", ["Vitesse", "Cuota", "Duración"])

vitesse_valores = [2.7, 2.75, 3, 3.25, 3.43, 4.37, 5.17, 6.57, 9.37]

capital = st.number_input("Capital inicial (€)", 0.0, 1000000.0, 6000.0)
tin = st.number_input("TIN anual (%)", 0.0, 100.0, 21.79)
fecha_inicio = st.date_input("Fecha de financiación", datetime.today())

# Campo dinámico según tipo
if tipo_calculo == "Vitesse":
    valor = st.selectbox("Porcentaje de reembolso mensual (%)", vitesse_valores)
elif tipo_calculo == "Cuota":
    opciones_cuota = [round(capital * v / 100, 2) for v in vitesse_valores]
    valor = st.selectbox("Cuota mensual (€)", opciones_cuota)
else:
    valor = st.number_input("Duración en meses", 1, 600, 36)

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

if st.button("Calcular"):
    tabla = simulador(capital, tin, tipo_calculo, valor, fecha_inicio, seguro_tasa)
    st.dataframe(tabla, use_container_width=True)

    total_intereses = round(tabla["Intereses total (€)"].sum(),2)
    total_seguro = round(tabla["Seguro (€)"].sum(),2)
    total_capital_intereses = round(tabla["Cuota (€)"].sum(),2)
    total_con_seguro = round(total_capital_intereses + total_seguro,2)

    cuotas_tae = [-capital] + list(tabla["Cuota (€)"])
    fechas_tae = [fecha_inicio] + list(tabla["Fecha recibo"])
    tae = calcular_tae(cuotas_tae, fechas_tae)

    resumen_dict = {
        "Concepto": [
            "Duración (meses)",
            "Intereses (€)",
            "Seguro (€) total",
            "Coste total con seguro",
            "Coste total (capital + intereses)",
            "TAE exacta (%)"
        ],
        "Valor": [
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

    # Tabla detalle TAE
    tabla_tae = pd.DataFrame({
        "Fecha": fechas_tae,
        "Cuota (sin seguro) (€)": cuotas_tae,
        "Tiempo (años)": [round(t,5) for t in range(len(cuotas_tae))],  # aproximado simplificado
        "Valor descontado": [round(c / ((1 + tae/100) ** t),5) for c,t in zip(cuotas_tae, range(len(cuotas_tae)))]
    })
    st.subheader("📈 Detalle cálculo TAE mes a mes")
    st.dataframe(tabla_tae, use_container_width=True)
