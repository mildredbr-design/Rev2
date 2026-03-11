import streamlit as st
import pandas as pd
from io import BytesIO
from datetime import datetime, date

st.set_page_config(page_title="Simulador Revolving", layout="wide")
st.title("💳 Simulador de Préstamo Revolving")

# -------- PRIMER RECIBO (día 2) --------
def primer_recibo(fecha_inicio):

    if fecha_inicio.day < 2:
        return fecha_inicio.replace(day=2)

    if fecha_inicio.month == 12:
        return date(fecha_inicio.year + 1, 1, 2)
    else:
        return date(fecha_inicio.year, fecha_inicio.month + 1, 2)

# -------- SIMULADOR --------
def simulador(capital, interes, cuota_porcentaje, fecha_inicio):

    saldo = capital
    i = interes / 12 / 100
    cuota = capital * (cuota_porcentaje / 100)

    fecha_pago = primer_recibo(fecha_inicio)

    datos = []
    mes = 1

    while saldo > 0:

        interes_mes = saldo * i

        # Si el saldo se puede liquidar en este mes
        if saldo + interes_mes <= cuota:

            cuota_final = saldo + interes_mes
            amort = saldo
            saldo = 0

            datos.append({
                "Mes": mes,
                "Fecha recibo": fecha_pago,
                "Cuota (€)": round(cuota_final, 2),
                "Intereses (€)": round(interes_mes, 2),
                "Amortización (€)": round(amort, 2),
                "Saldo (€)": round(saldo, 2)
            })

            break

        amort = cuota - interes_mes
        saldo -= amort

        datos.append({
            "Mes": mes,
            "Fecha recibo": fecha_pago,
            "Cuota (€)": round(cuota, 2),
            "Intereses (€)": round(interes_mes, 2),
            "Amortización (€)": round(amort, 2),
            "Saldo (€)": round(saldo, 2)
        })

        mes += 1

        # siguiente recibo (siempre día 2)
        if fecha_pago.month == 12:
            fecha_pago = date(fecha_pago.year + 1, 1, 2)
        else:
            fecha_pago = date(fecha_pago.year, fecha_pago.month + 1, 2)

        if mes > 600:
            break

    return pd.DataFrame(datos)

# -------- INPUTS --------
capital = st.number_input("Capital inicial (€)", 0.0, 1000000.0, 10000.0)
interes = st.number_input("Interés anual (%)", 0.0, 100.0, 18.0)

fecha_inicio = st.date_input(
    "Fecha de financiación",
    datetime.today()
)

opciones_cuota = [2.7, 3, 3.5, 4, 5, 6, 7, 8, 9]

cuota_porcentaje = st.selectbox(
    "Velocidad de reembolso (% del capital inicial)",
    opciones_cuota
)

# -------- CALCULO --------
if st.button("Calcular"):

    tabla = simulador(capital, interes, cuota_porcentaje, fecha_inicio)

    st.dataframe(tabla, use_container_width=True)

    st.subheader("📊 Resumen")

    total_pagado = tabla["Cuota (€)"].sum()
    total_intereses = tabla["Intereses (€)"].sum()
    meses_totales = len(tabla)

    col1, col2, col3 = st.columns(3)

    col1.metric("Meses totales", meses_totales)
    col2.metric("Total pagado (€)", round(total_pagado, 2))
    col3.metric("Intereses totales (€)", round(total_intereses, 2))

    # -------- EXPORTAR EXCEL --------
    output = BytesIO()

    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        tabla.to_excel(writer, index=False)

    excel_data = output.getvalue()

    st.download_button(
        label="📥 Descargar Excel",
        data=excel_data,
        file_name="amortizacion_revolving.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
