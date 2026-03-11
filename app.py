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

# ---------- INTERESES EXACTOS POR TRAMOS ----------
def interes_preciso(capital, tin, fecha_inicio, fecha_fin):
    fecha_inicio = pd.to_datetime(fecha_inicio).date()
    fecha_fin = pd.to_datetime(fecha_fin).date()
    
    interes_diciembre = 0.0
    interes_enero = 0.0
    interes_total = 0.0

    # Cambio bisiesto ↔ no bisiesto
    if fecha_fin.month == 1 and fecha_inicio.year < fecha_fin.year:
        year_prev = fecha_fin.year - 1
        year_curr = fecha_fin.year
        bisiesto_prev = calendar.isleap(year_prev)
        bisiesto_curr = calendar.isleap(year_curr)
        if bisiesto_prev != bisiesto_curr:
            # Diciembre: del 2 al 31
            dias_dic = 29
            base_dic = 366 if bisiesto_prev else 365
            interes_diciembre = round(capital * (tin / 100) * dias_dic / base_dic, 5)

            # Enero: 1 hasta fecha_fin
            dias_ene = (fecha_fin - date(year_curr, 1, 1)).days + 1
            base_ene = 366 if bisiesto_curr else 365
            interes_enero = round(capital * (tin / 100) * dias_ene / base_ene, 5)

            # Suma total con 5 decimales internamente
            interes_total = round(interes_diciembre + interes_enero, 5)
            # Para tabla: redondeo a 2 decimales
            return round(interes_total, 2), interes_diciembre, interes_enero

    # Mes normal
    dias_tramo = (fecha_fin - fecha_inicio).days
    base = dias_ano(fecha_inicio)
    interes_total = round(capital * (tin / 100) * dias_tramo / base, 5)
    return round(interes_total, 2), 0.0, round(interes_total, 5)

# ---------- FRACCION DE AÑO DESDE FINANCIACION PARA TAE ----------
def fraccion_ano_desde_financiacion(fecha_inicio, fecha_pago):
    fecha_inicio = pd.to_datetime(fecha_inicio).date()
    fecha_pago = pd.to_datetime(fecha_pago).date()
    fraccion_total = 0.0

    fecha_actual = fecha_inicio
    while fecha_actual < fecha_pago:
        # Manejo cambio bisiesto ↔ no bisiesto
        if fecha_actual.month == 12 and fecha_actual.day == 2 and fecha_actual.year +1 == fecha_pago.year:
            year_prev = fecha_actual.year
            year_curr = fecha_pago.year
            bisiesto_prev = calendar.isleap(year_prev)
            bisiesto_curr = calendar.isleap(year_curr)
            if bisiesto_prev != bisiesto_curr:
                # Diciembre: 2-31
                base_dic = 366 if bisiesto_prev else 365
                dias_dic = 29
                fraccion_total += dias_dic / base_dic

                # Enero: 1 hasta fecha_pago
                base_ene = 366 if bisiesto_curr else 365
                dias_ene = (fecha_pago - date(year_curr, 1, 1)).days + 1
                fraccion_total += dias_ene / base_ene
                return fraccion_total

        # Mes normal
        base = dias_ano(fecha_actual)
        dias_mes = (fecha_pago - fecha_actual).days
        fraccion_total += dias_mes / base
        break

    return fraccion_total

# ---------- SIMULADOR ----------
def simulador(capital, tin, cuota_porcentaje, fecha_inicio, seguro_tasa=0):
    saldo = capital
    cuota = capital * (cuota_porcentaje / 100)
    fecha_inicio_dt = fecha_inicio if isinstance(fecha_inicio, date) else fecha_inicio.date()
    fecha_pago = primer_recibo(fecha_inicio_dt)
    fecha_anterior = fecha_inicio_dt
    datos = []
    mes = 1

    while saldo > 0:
        interes_total, interes_diciembre, interes_enero = interes_preciso(saldo, tin, fecha_anterior, fecha_pago)
        seguro = round((saldo + interes_total) * seguro_tasa, 5) if seguro_tasa > 0 else 0.0
        capital_pendiente = saldo

        if saldo + interes_total <= cuota:
            amort = saldo
            saldo = 0
            cuota_final = amort + interes_total
            recibo_total = cuota_final + seguro
            datos.append({
                "Mes": mes,
                "Fecha recibo": fecha_pago,
                "Capital pendiente (€)": round(capital_pendiente, 2),
                "Cuota (€)": round(cuota_final, 2),
                "Intereses diciembre (€)": interes_diciembre,
                "Intereses enero (€)": interes_enero,
                "Intereses total (€)": round(interes_total, 2),
                "Amortización (€)": round(amort, 2),
                "Saldo (€)": saldo,
                "Seguro (€)": round(seguro, 2),
                "Recibo total (€)": round(recibo_total, 2),
                "Recibo total exacto": recibo_total,
                "Fraccion año TAE": fraccion_ano_desde_financiacion(fecha_inicio_dt, fecha_pago)
            })
            break

        amort = cuota - interes_total
        saldo -= amort
        recibo_total = cuota + seguro

        datos.append({
            "Mes": mes,
            "Fecha recibo": fecha_pago,
            "Capital pendiente (€)": round(capital_pendiente, 2),
            "Cuota (€)": round(cuota, 2),
            "Intereses diciembre (€)": interes_diciembre,
            "Intereses enero (€)": interes_enero,
            "Intereses total (€)": round(interes_total, 2),
            "Amortización (€)": round(amort, 2),
            "Saldo (€)": round(saldo, 2),
            "Seguro (€)": round(seguro, 2),
            "Recibo total (€)": round(recibo_total, 2),
            "Recibo total exacto": recibo_total,
            "Fraccion año TAE": fraccion_ano_desde_financiacion(fecha_inicio_dt, fecha_pago)
        })

        fecha_anterior = fecha_pago
        fecha_pago = siguiente_recibo(fecha_pago)
        mes += 1
        if mes > 600:
            break

    return pd.DataFrame(datos)

# ---------- CALCULO TAE ----------
def calcular_tae(cuotas, tiempos, tolerancia=0.000001, max_iter=10000):
    tae = 0.2179
    for _ in range(max_iter):
        van = sum([c / ((1 + tae) ** t) for c, t in zip(cuotas, tiempos)])
        if abs(van) < tolerancia:
            return round(tae*100,2)
        tae += 0.00001 if van > 0 else -0.00001
    return round(tae*100,2)

# ---------- INPUTS ----------
capital = st.number_input("Capital inicial (€)", 0.0, 1000000.0, 6000.0)
tin = st.number_input("TIN anual (%)", 0.0, 100.0, 21.79)
fecha_inicio = st.date_input("Fecha de financiación", datetime.today())

opciones = [2.7, 3, 3.5, 4, 5, 6, 7, 8, 9]
cuota_porcentaje = st.selectbox("Velocidad de reembolso (% del capital inicial)", opciones)

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

# ---------- CALCULO ----------
if st.button("Calcular"):
    tabla = simulador(capital, tin, cuota_porcentaje, fecha_inicio, seguro_tasa)

    tabla_mostrar = tabla.copy()
    for col in ["Intereses diciembre (€)", "Intereses enero (€)", "Intereses total (€)", "Cuota (€)", "Recibo total (€)"]:
        tabla_mostrar[col] = tabla_mostrar[col].map("{:.2f}".format)
    st.dataframe(tabla_mostrar, use_container_width=True)

    total_intereses = round(tabla["Intereses total (€)"].sum(),2)
    total_intereses_diciembre = round(tabla["Intereses diciembre (€)"].sum(),2)
    total_intereses_enero = round(tabla["Intereses enero (€)"].sum(),2)
    total_seguro = round(tabla["Seguro (€)"].sum(),2) if seguro_tasa>0 else 0
    total_capital_intereses = round(tabla["Cuota (€)"].sum(),2)
    total_con_seguro = round(total_capital_intereses + total_seguro,2)

    cuotas_exactas = [-capital] + list(tabla["Recibo total exacto"].values)
    tiempos = [0] + list(tabla["Fraccion año TAE"].cumsum())
    tae = calcular_tae(cuotas_exactas, tiempos)

    resumen_dict = {"Concepto":["Duración (meses)","Intereses totales (€)","Intereses diciembre (€)","Intereses enero (€)","TAE aproximada (%)"]}
    resumen_valores = [len(tabla), total_intereses, total_intereses_diciembre, total_intereses_enero, tae]

    if seguro_tasa>0:
        resumen_dict["Concepto"].insert(4,"Seguro (€) total")
        resumen_valores.insert(4,total_seguro)
        resumen_dict["Concepto"].insert(5,"Coste total con seguro (capital + intereses + seguro)")
        resumen_valores.insert(5,total_con_seguro)

    resumen_dict["Concepto"].append("Coste total (capital + intereses)")
    resumen_valores.append(total_capital_intereses)

    df_resumen = pd.DataFrame({"Concepto":resumen_dict["Concepto"],"Valor":resumen_valores})
    st.subheader("📊 Resumen en tabla")
    st.table(df_resumen)

    # Exportar Excel
    output = BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        tabla.to_excel(writer,index=False,sheet_name="Amortización")
        df_resumen.to_excel(writer,index=False,sheet_name="Resumen")
    excel_data = output.getvalue()
    st.download_button(label="📥 Descargar Excel con resumen",data=excel_data,
                       file_name="amortizacion_revolving_seguro_tae.xlsx",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
