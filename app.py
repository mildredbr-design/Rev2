import streamlit as st
import pandas as pd
from io import BytesIO
from datetime import datetime, date
import calendar
import numpy as np

st.set_page_config(page_title="Simulador Revolving", layout="wide")
st.title("💳 Simulador de Préstamo Revolving con Seguro Opcional y TAE")

# ---------- FUNCIONES ----------
def dias_ano(fecha):
    return 366 if calendar.isleap(fecha.year) else 365

def primer_recibo(fecha_inicio):
    if fecha_inicio.day < 2:
        return fecha_inicio.replace(day=2)
    if fecha_inicio.month == 12:
        return date(fecha_inicio.year + 1, 1, 2)
    else:
        return date(fecha_inicio.year, fecha_inicio.month + 1, 2)

def siguiente_recibo(fecha):
    if fecha.month == 12:
        return date(fecha.year + 1, 1, 2)
    else:
        return date(fecha.year, fecha.month + 1, 2)

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
    return round(interes_total, 2)

def simulador(capital, tin, cuota_porcentaje, fecha_inicio, seguro_tasa=0):

    saldo = capital
    cuota = capital * (cuota_porcentaje / 100)  # usar sin redondeo para TAE
    fecha_pago = primer_recibo(fecha_inicio)
    fecha_anterior = fecha_inicio

    datos = []
    mes = 1

    while saldo > 0:
        interes = calcular_interes(saldo, tin, fecha_anterior, fecha_pago)
        dias = (fecha_pago - fecha_anterior).days
        seguro = (saldo + interes) * seguro_tasa if seguro_tasa > 0 else 0.0

        # Último recibo
        if saldo + interes <= cuota:
            cuota_final = saldo + interes
            amort = saldo
            saldo = 0
            if seguro_tasa > 0:
                seguro = (amort + interes) * seguro_tasa
            recibo_total = cuota_final + seguro
            datos.append({
                "Mes": mes,
                "Fecha recibo": fecha_pago,
                "Días": dias,
                "Cuota (€)": round(cuota_final,2),
                "Intereses (€)": round(interes,2),
                "Amortización (€)": round(amort,2),
                "Saldo (€)": round(saldo,2),
                "Seguro (€)": round(seguro,2),
                "Recibo total (€)": round(recibo_total,2),
                "Recibo total exacto": recibo_total
            })
            break

        amort = cuota - interes
        saldo = saldo - amort
        recibo_total = cuota + seguro

        datos.append({
            "Mes": mes,
            "Fecha recibo": fecha_pago,
            "Días": dias,
            "Cuota (€)": round(cuota,2),
            "Intereses (€)": round(interes,2),
            "Amortización (€)": round(amort,2),
            "Saldo (€)": round(saldo,2),
            "Seguro (€)": round(seguro,2),
            "Recibo total (€)": round(recibo_total,2),
            "Recibo total exacto": recibo_total
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

seguro_str = st.selectbox(
    "Seguro mensual sobre saldo pendiente + interés",
    ["No", "Un titular", "Dos titulares"]
)

if seguro_str == "No":
    seguro_tasa = 0
elif seguro_str == "Un titular":
    seguro_tasa = 0.0061
else:
    seguro_tasa = 0.0104

# -------- CALCULO --------
if st.button("Calcular"):

    tabla = simulador(capital, tin, cuota_porcentaje, fecha_inicio, seguro_tasa)
    st.dataframe(tabla.drop(columns=["Recibo total exacto"]), use_container_width=True)

    st.subheader("📊 Resumen")
    total_cuota = tabla["Cuota (€)"].sum()
    total_intereses = tabla["Intereses (€)"].sum()

    col1, col2, col3 = st.columns(3)
    col1.metric("Meses totales", len(tabla))
    col2.metric("Total pagado (€)", round(total_cuota,2))
    col3.metric("Intereses (€)", round(total_intereses,2))

    st.write(f"**Coste total (capital + intereses):** {round(total_cuota,2)} €")
    if seguro_tasa == 0:
        st.write("**Seguro no contratado**")
    else:
        total_seguro = tabla["Seguro (€)"].sum()
        st.write(f"**Coste total con seguro (capital + intereses + seguro):** {round(total_cuota + total_seguro,2)} €")

    # -------- CALCULO TAE USANDO FLUJOS EXACTOS --------
    flujos = [-capital] + list(tabla["Recibo total exacto"].values)
    try:
        tasa_mensual = np.irr(flujos)
        tae = (1 + tasa_mensual)**12 - 1
        st.write(f"**TAE aproximada:** {round(tae*100,2)} %")
    except:
        st.write("No se pudo calcular la TAE")

    # -------- EXPORTAR EXCEL CON RESUMEN --------
    output = BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        tabla.drop(columns=["Recibo total exacto"]).to_excel(writer, index=False, sheet_name="Amortización")
        resumen = {
            "Concepto": ["Coste total (capital + intereses)"],
            "Importe (€)": [round(total_cuota,2)]
        }
        if seguro_tasa == 0:
            resumen["Concepto"].append("Seguro no contratado")
            resumen["Importe (€)"].append(0)
        else:
            resumen["Concepto"].append("Coste total con seguro (capital + intereses + seguro)")
            resumen["Importe (€)"].append(round(total_cuota + total_seguro,2))
        try:
            resumen["Concepto"].append("TAE aproximada (%)")
            resumen["Importe (€)"].append(round(tae*100,2))
        except:
            pass
        df_resumen = pd.DataFrame(resumen)
        df_resumen.to_excel(writer, index=False, sheet_name="Resumen")

    excel_data = output.getvalue()
    st.download_button(
        label="📥 Descargar Excel con resumen",
        data=excel_data,
        file_name="amortizacion_revolving_seguro_tae.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
