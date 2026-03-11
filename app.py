import streamlit as st
import pandas as pd
from io import BytesIO
from datetime import datetime, date, timedelta
import calendar

st.set_page_config(page_title="Simulador Revolving", layout="wide")
st.title("💳 Simulador de Préstamo Revolving con Seguro Opcional y TAE Exacta")

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

def interes_diario_exacto(capital, tin, fecha_inicio, fecha_fin):
    """Calcula interés sumando cada día del periodo con base correcta del año"""
    interes_total = 0.0
    fecha_actual = fecha_inicio
    while fecha_actual < fecha_fin:
        base = dias_ano(fecha_actual)
        interes_total += capital * (tin/100) / base
        fecha_actual += timedelta(days=1)
    return interes_total

def simulador(capital, tin, cuota_porcentaje, fecha_inicio, seguro_tasa=0):
    saldo = capital
    cuota = capital * (cuota_porcentaje / 100)
    fecha_pago = primer_recibo(fecha_inicio)
    fecha_anterior = fecha_inicio
    datos = []
    mes = 1

    while saldo > 0:
        interes = round(interes_diario_exacto(saldo, tin, fecha_anterior, fecha_pago),5)
        seguro = round((saldo + interes) * seguro_tasa,2) if seguro_tasa>0 else 0.0
        capital_pendiente = saldo  # Guardamos capital pendiente al inicio del mes

        # Ajustar último recibo
        if saldo + interes <= cuota:
            cuota_final = round(saldo + interes,2)
            amort = round(saldo,2)
            saldo = 0
            if seguro_tasa>0:
                seguro = round((amort + interes) * seguro_tasa,2)
            recibo_total = round(cuota_final + seguro,2)
            datos.append({
                "Mes": mes,
                "Fecha recibo": fecha_pago,
                "Capital pendiente (€)": round(capital_pendiente,2),
                "Cuota (€)": cuota_final,
                "Intereses (€)": round(interes,2),
                "Amortización (€)": amort,
                "Saldo (€)": saldo,
                "Seguro (€)": seguro,
                "Recibo total (€)": recibo_total,
                "Recibo total exacto": cuota_final
            })
            break

        amort = round(cuota - interes,2)
        saldo = round(saldo - amort,2)
        recibo_total = round(cuota + seguro,2)

        datos.append({
            "Mes": mes,
            "Fecha recibo": fecha_pago,
            "Capital pendiente (€)": round(capital_pendiente,2),
            "Cuota (€)": round(cuota,2),
            "Intereses (€)": round(interes,2),
            "Amortización (€)": amort,
            "Saldo (€)": saldo,
            "Seguro (€)": seguro,
            "Recibo total (€)": recibo_total,
            "Recibo total exacto": round(cuota,2)
        })

        fecha_anterior = fecha_pago
        fecha_pago = siguiente_recibo(fecha_pago)
        mes += 1
        if mes > 600:
            break

    return pd.DataFrame(datos)

# ---------- FUNCIONES TAE ----------
def redondear_decimal(valor, decimales=6):
    return round(valor, decimales)

def calcular_fraccion_entre_financiacion_y_vencimiento(fecha_inicio, fecha_fin):
    fecha_inicio = pd.to_datetime(fecha_inicio)
    fecha_fin = pd.to_datetime(fecha_fin)
    fraccion_total = 0.0
    fecha_actual = fecha_inicio
    while fecha_actual < fecha_fin:
        base = dias_ano(fecha_actual)
        fraccion_total += 1/base
        fecha_actual += timedelta(days=1)
    return fraccion_total

def calcular_tae(cuotas, tiempos, tolerancia=0.000001, max_iter=10000):
    tae = 0.2179
    van_lista = []
    for _ in range(max_iter):
        van_lista.clear()
        for i in range(len(cuotas)):
            van_lista.append(cuotas[i]/((1+tae)**tiempos[i]))
        if abs(sum(van_lista))<tolerancia:
            return redondear_decimal(tae*100,2)
        if sum(van_lista)<0:
            tae-=0.00001
        else:
            tae+=0.00001
    return redondear_decimal(tae*100,2)

# ---------- INPUTS ----------
capital = st.number_input("Capital inicial (€)", 0.0, 1000000.0, 6000.0)
tin = st.number_input("TIN anual (%)", 0.0, 100.0, 21.79)
fecha_inicio = st.date_input("Fecha de financiación", datetime.today())
opciones = [2.7,3,3.5,4,5,6,7,8,9]
cuota_porcentaje = st.selectbox("Velocidad de reembolso (% del capital inicial)", opciones)

# ---------- SEGURO ----------
opciones_seguro = {
    "No":0,
    "Un titular Light":0.0035,
    "Un titular Full/Senior":0.0061,
    "Dos titulares Full/Full":0.0104,
    "Dos titulares Senior/Senior":0.0104,
    "Dos titulares Light/Light":0.0059,
    "Dos titulares Full/Light":0.0082
}
seguro_str = st.selectbox("Seguro mensual sobre saldo pendiente + interés", list(opciones_seguro.keys()))
seguro_tasa = opciones_seguro[seguro_str]

# ---------- CALCULO ----------
if st.button("Calcular"):
    tabla = simulador(capital, tin, cuota_porcentaje, fecha_inicio, seguro_tasa)
    st.dataframe(tabla.drop(columns=["Recibo total exacto"]), use_container_width=True)

    # Valores resumen
    duracion_meses = len(tabla)
    total_intereses = round(tabla["Intereses (€)"].sum(),2)
    total_seguro = round(tabla["Seguro (€)"].sum(),2) if seguro_tasa>0 else 0.0
    total_capital_intereses = round(tabla["Cuota (€)"].sum(),2)
    total_con_seguro = round(total_capital_intereses + total_seguro,2)

    # Calculo TAE (sin seguro)
    cuotas_exactas = [-capital]+list(tabla["Recibo total exacto"].values)
    tiempos = [0]+[calcular_fraccion_entre_financiacion_y_vencimiento(fecha_inicio,f) for f in tabla["Fecha recibo"]]
    try:
        tae = calcular_tae(cuotas_exactas, tiempos)
    except:
        tae="Error"

    # Tabla resumen
    resumen_dict = {"Concepto":["Duración (meses)","Intereses (€)"]}
    resumen_valores = [int(duracion_meses),total_intereses]

    if seguro_tasa>0:
        resumen_dict["Concepto"].append("Seguro (€) total")
        resumen_valores.append(total_seguro)
        resumen_dict["Concepto"].append("Coste total con seguro (capital + intereses + seguro)")
        resumen_valores.append(total_con_seguro)

    resumen_dict["Concepto"].append("Coste total (capital + intereses)")
    resumen_valores.append(total_capital_intereses)
    resumen_dict["Concepto"].append("TAE aproximada (%)")
    resumen_valores.append(round(tae,2) if isinstance(tae,float) else tae)

    df_resumen = pd.DataFrame({"Concepto":resumen_dict["Concepto"],"Valor":resumen_valores})
    st.subheader("📊 Resumen en tabla")
    st.table(df_resumen)

    # ---------- EXPORTAR EXCEL ----------
    output = BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        tabla.drop(columns=["Recibo total exacto"]).to_excel(writer,index=False,sheet_name="Amortización")
        df_resumen.to_excel(writer,index=False,sheet_name="Resumen")
    excel_data = output.getvalue()
    st.download_button(
        label="📥 Descargar Excel con resumen",
        data=excel_data,
        file_name="amortizacion_revolving_seguro_tae.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
