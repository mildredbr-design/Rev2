import streamlit as st
import pandas as pd
from io import BytesIO

st.set_page_config(page_title="Simulador Revolving", layout="wide")
st.title("💳 Simulador de Préstamo Revolving - Velocidad de Reembolso")

# ---------------- FUNCION SIMULADOR ----------------
def simulador(capital, interes, cuota_porcentaje):

    saldo = capital
    i = interes / 12 / 100
    cuota = capital * (cuota_porcentaje / 100)

    datos = []
    mes = 1

    while saldo > 0:

        interes_mes = saldo * i
        amort = cuota - interes_mes

        # Si la cuota no cubre intereses
        if amort <= 0:
            st.error("⚠️ La cuota es demasiado baja y no cubre los intereses. La deuda aumentaría.")
            break

        saldo -= amort

        # Ajuste última cuota
        if saldo < 0:
            amort += saldo
            cuota = interes_mes + amort
            saldo = 0

        datos.append({
            "Mes": mes,
            "Cuota (€)": round(cuota, 2),
            "Intereses (€)": round(interes_mes, 2),
            "Amortización (€)": round(amort, 2),
            "Saldo (€)": round(saldo, 2)
        })

        mes += 1

        # seguridad para evitar bucle infinito
        if mes > 600:
            break

    return pd.DataFrame(datos)

# ---------------- INPUTS ----------------
capital = st.number_input("Capital inicial (€)", 0.0, 1000000.0, 10000.0)
interes = st.number_input("Interés anual (%)", 0.0, 100.0, 18.0)

opciones_cuota = [2.7, 3, 3.5, 4, 5, 6, 7, 8, 9]

cuota_porcentaje = st.selectbox(
    "Velocidad de reembolso (% del capital inicial)",
    opciones_cuota
)

# ---------------- CALCULO ----------------
if st.button("Calcular"):

    tabla = simulador(capital, interes, cuota_porcentaje)

    st.dataframe(tabla, use_container_width=True)

    # ----------- RESUMEN -----------
    st.subheader("📊 Resumen")

    total_pagado = tabla["Cuota (€)"].sum()
    total_intereses = tabla["Intereses (€)"].sum()
    meses_totales = len(tabla)

    col1, col2, col3 = st.columns(3)

    col1.metric("Meses totales", meses_totales)
    col2.metric("Total pagado (€)", round(total_pagado, 2))
    col3.metric("Intereses totales (€)", round(total_intereses, 2))

    # ----------- EXPORTAR EXCEL -----------
    output = BytesIO()

    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        tabla.to_excel(writer, index=False)

    excel_data = output.getvalue()

    st.download_button(
        label="📥 Descargar Excel",
        data=excel_data,
        file_name="amortizacion_revolving.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
