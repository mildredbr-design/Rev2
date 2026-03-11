import streamlit as st
import pandas as pd
from io import BytesIO
from datetime import datetime, date
import calendar

st.set_page_config(page_title="Simulador Revolving", layout="wide")
st.title("💳 Simulador de Préstamo Revolving")

# -------- DIAS DEL AÑO --------
def dias_ano(fecha):
    return 366 if calendar.isleap(fecha.year) else 365

# -------- PRIMER RECIBO --------
def primer_recibo(fecha_inicio):
    if fecha_inicio.day < 2:
        return fecha_inicio.replace(day=2)
    if fecha_inicio.month == 12:
        return date(fecha_inicio.year + 1, 1, 2)
    else:
        return date(fecha_inicio.year, fecha_inicio.month + 1, 2)

# -------- SIGUIENTE RECIBO --------
def siguiente_recibo(fecha):
    if fecha.month == 12:
        return date(fecha.year + 1, 1, 2)
    else:
        return date(fecha.year, fecha.month + 1, 2)

# -------- INTERES POR DIAS CON CAMBIO DE AÑO --------
def calcular_interes(capital, tin, fecha_inicio, fecha_fin):
    interes_total = 0
    fecha_actual = fecha_inicio
    while fecha_actual < fecha_fin:
        fin_ano = date(fecha_actual.year, 12, 31)
        if fecha_fin <= fin_ano:
            dias = (fecha_fin - fecha_actual).days
            base = dias_ano(fecha_actual)
            interes_total += capital * (tin/100) * dias / base
            break
        else:
            dias = (fin_ano - fecha_actual).days + 1
            base = dias_ano(fecha_actual)
            interes_total += capital * (tin/100) * dias / base
            fecha_actual = date(fecha_actual.year + 1, 1, 1)
    return round(interes_total, 2)  # Redondeo a 2 decimales

# -------- SIMULADOR --------
def simulador(capital, tin, cuota_porcentaje, fecha_inicio):

    saldo = capital
    cuota = round(capital * (cuota_porcentaje / 100), 2)

    fecha_pago = primer_recibo(fecha_inicio)
    fecha_anterior = fecha_inicio

    datos = []
    mes = 1

    while saldo > 0:

        # Interés del periodo
        interes = calcular_interes(saldo, tin, fecha_anterior, fecha_pago)
        dias = (fecha_pago - fecha_anterior).days

        # Último recibo
        if saldo + interes <= cuota:
            cuota_final = round(saldo + interes, 2)
            amort = saldo
            saldo = 0
            datos.append({
                "Mes": mes,
                "Fecha recibo": fecha_pago,
                "Días": dias,
                "Cuota (€)": cuota_final,
                "Intereses (€)": interes,
                "Amortización (€)": round(amort,2),
                "Saldo (€)": round(saldo,2)
            })
            break

        # Cuota fija mensual
        amort = round(cuota - interes, 2)
        saldo = round(saldo - amort, 2)

        datos.append({
            "Mes": mes,
            "Fecha recibo": fecha_pago,
            "Días": dias,
            "Cuota (€)": cuota,
            "Intereses (€)": interes,
            "Amortización (€)": amort,
            "Saldo (€)": saldo
        })

        fecha_anterior = fecha_pago
        fecha_pago = siguiente_recibo(fecha_pago)

        mes += 1

        if mes > 600:
            break

    return pd.DataFrame(datos)

# -------- INPUTS --------
capital = st.number_input("Capital inicial (€)", 0.0, 1000000.0, 1000.0)
tin = st.number_input("TIN anual (%)", 0.0, 100.0, 21.79)
fecha_inicio = st.date_input("Fecha de financiación", datetime.today())
opciones = [2.7, 3, 3.5, 4, 5, 6, 7, 8, 9]
cuota_porcentaje = st.selectbox("Velocidad de reembolso (% del capital inicial)", opciones)

# -------- CALCULO --------
if st.button("Calcular"):

    tabla = simulador(capital, tin, cuota_porcentaje, fecha_inicio)
    st.dataframe(tabla, use_container_width=True)

    st.subheader("📊 Resumen")
    total_pagado = tabla["Cuota (€)"].sum()
    total_intereses = tabla["Intereses (€)"].sum()
    col1, col2, col3 = st.columns(3)
    col1.metric("Meses totales", len(tabla))
    col2.metric("Total pagado (€)", round(total_pagado,2))
    col3.metric("Intereses totales (€)", round(total_intereses,2))

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
