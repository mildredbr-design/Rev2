import streamlit as st
import pandas as pd
from datetime import datetime, date
import calendar
from decimal import Decimal, ROUND_HALF_UP, getcontext
from io import BytesIO

getcontext().prec = 10

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
    
''Calcular la fecha del primer vencimiento en base a la fecha de bloqueo posterior a la fecha de financiación'''
    proximas_db = FECHAS_BLOQUEO[FECHAS_BLOQUEO['Fecha_BLOQUEO'] >= fecha_financiacion]
    fecha_primer_vencimiento = proximas_db['Fecha_BLOQUEO'].iloc[0].replace(day=dia_pago) + pd.DateOffset(months=1)
def siguiente_recibo(fecha):
    if fecha.month == 12:
        return date(fecha.year + 1, 1, 2)
    return date(fecha.year, fecha.month + 1, 2)

# ---------------------------------------------------------
# CALCULO INTERESES
# ---------------------------------------------------------

def interes_preciso(capital, tin, fecha_inicio, fecha_fin):

    capital = Decimal(str(capital))
    tin = Decimal(str(tin)) / Decimal("100")

    fecha_inicio = pd.to_datetime(fecha_inicio).date()
    fecha_fin = pd.to_datetime(fecha_fin).date()

    interes_diciembre = Decimal("0")
    interes_enero = Decimal("0")

    if fecha_fin.month == 1 and fecha_inicio.year < fecha_fin.year:

        year_prev = fecha_inicio.year
        year_curr = fecha_fin.year

        bisiesto_prev = calendar.isleap(year_prev)
        bisiesto_curr = calendar.isleap(year_curr)

        if bisiesto_prev != bisiesto_curr:

            dias_dic = 29
            base_dic = 366 if bisiesto_prev else 365

            interes_diciembre = (
                capital * tin * Decimal(dias_dic) / Decimal(base_dic)
            ).quantize(Decimal("0.00001"))

            dias_ene = (fecha_fin - date(year_curr,1,1)).days + 1
            base_ene = 366 if bisiesto_curr else 365

            interes_enero = (
                capital * tin * Decimal(dias_ene) / Decimal(base_ene)
            ).quantize(Decimal("0.00001"))

            interes_total = (interes_diciembre + interes_enero).quantize(Decimal("0.00001"))

            return interes_total, interes_diciembre, interes_enero

    dias_tramo = (fecha_fin - fecha_inicio).days
    base = dias_ano(fecha_inicio)

    interes_total = (
        capital * tin * Decimal(dias_tramo) / Decimal(base)
    ).quantize(Decimal("0.00001"))

    return interes_total, Decimal("0"), interes_total

# ---------------------------------------------------------
# SIMULADOR
# ---------------------------------------------------------

def simulador(capital, tin, tipo_calculo, valor, fecha_inicio, seguro_tasa=0):

    capital = Decimal(str(capital))
    saldo = capital
    seguro_tasa = Decimal(str(seguro_tasa))

    fecha_pago = primer_recibo(fecha_inicio)
    fecha_anterior = fecha_inicio

    datos = []
    mes = 1

    if tipo_calculo == "Vitesse":
        cuota = (capital * Decimal(str(valor)) / Decimal("100")).quantize(Decimal("0.01"),ROUND_HALF_UP)

    elif tipo_calculo == "Cuota":
        cuota = Decimal(str(valor)).quantize(Decimal("0.01"),ROUND_HALF_UP)

    while saldo > 0:

        interes_total, interes_dic, interes_ene = interes_preciso(
            saldo, tin, fecha_anterior, fecha_pago
        )

        interes_total = interes_total.quantize(Decimal("0.01"),ROUND_HALF_UP)

        seguro = ((saldo + interes_total) * seguro_tasa).quantize(Decimal("0.01"),ROUND_HALF_UP)

        if saldo + interes_total <= cuota:

            amort = saldo.quantize(Decimal("0.01"),ROUND_HALF_UP)
            saldo = Decimal("0")

            cuota_final = (amort + interes_total).quantize(Decimal("0.01"),ROUND_HALF_UP)

        else:

            amort = (cuota - interes_total).quantize(Decimal("0.01"),ROUND_HALF_UP)
            saldo = (saldo - amort).quantize(Decimal("0.01"),ROUND_HALF_UP)

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

        if mes > 600:
            break

    return pd.DataFrame(datos)

# ---------------------------------------------------------
# CALCULO TAE
# ---------------------------------------------------------

def calcular_tae(cuotas, fechas):

    tiempos=[0.0]

    for i in range(1,len(fechas)):
        f0=pd.to_datetime(fechas[i-1]).date()
        f1=pd.to_datetime(fechas[i]).date()

        fraccion=(f1-f0).days/dias_ano(f0)
        tiempos.append(tiempos[-1]+fraccion)

    def van(tasa):
        return sum(c/((1+tasa)**t) for c,t in zip(cuotas,tiempos))

    minimo=-0.9999
    maximo=10

    for _ in range(1000):

        medio=(minimo+maximo)/2
        valor=van(medio)

        if abs(valor)<1e-10:
            return round(medio*100,2)

        if valor>0:
            minimo=medio
        else:
            maximo=medio

    return round(medio*100,2)

# ---------------------------------------------------------
# INPUTS
# ---------------------------------------------------------

vitesse_valores=[2.7,2.75,3,3.25,3.43,4.37,5.17,6.57,9.37]

capital = st.number_input("Importe de financiación (€)",0.0,1000000.0,6000.0)

tin = st.number_input("TIN anual (%)",0.0,100.0,21.79)

fecha_inicio = st.date_input("Fecha de financiación",datetime.today())

tipo_calculo = st.selectbox(
    "Tipo de cálculo",
    ["Seleccionar","Vitesse","Cuota","Duración"]
)

valor=None

if tipo_calculo=="Vitesse":

    valor=st.selectbox("Vitesse (%)",vitesse_valores)

elif tipo_calculo=="Cuota":

    opciones_cuota=[round(capital*v/100,2) for v in vitesse_valores]
    valor=st.selectbox("Cuota mensual (€)",opciones_cuota)

elif tipo_calculo=="Duración":

    opciones_duracion=[]
    mapa_vitesse={}

    for v in vitesse_valores:

        cuota_test=round(capital*v/100,2)

        tabla_test=simulador(capital,tin,"Cuota",cuota_test,fecha_inicio,0)

        meses=len(tabla_test)

        etiqueta=f"{meses} meses"
        opciones_duracion.append(etiqueta)

        mapa_vitesse[etiqueta]=v

    seleccion=st.selectbox("Duración del préstamo",opciones_duracion)

    valor=mapa_vitesse[seleccion]
    tipo_calculo="Vitesse"

# ---------------------------------------------------------
# SEGURO
# ---------------------------------------------------------

opciones_seguro={
"No":0,
"Un titular Light":0.0035,
"Un titular Full/Senior":0.0061,
"Dos titulares Full/Full":0.0104,
"Dos titulares Senior/Senior":0.0104,
"Dos titulares Light/Light":0.0059,
"Dos titulares Full/Light":0.0082
}

seguro_str=st.selectbox("Seguro mensual",list(opciones_seguro.keys()))
seguro_tasa=opciones_seguro[seguro_str]

# ---------------------------------------------------------
# RESULTADOS
# ---------------------------------------------------------
if st.button("Calcular") and valor is not None:

    tabla=simulador(capital,tin,tipo_calculo,valor,fecha_inicio,seguro_tasa)

    # Quitar columna seguro si no hay seguro
    if seguro_tasa==0 and "Seguro (€)" in tabla.columns:
        tabla=tabla.drop(columns=["Seguro (€)"])

    st.dataframe(tabla,use_container_width=True)

    total_intereses=round(tabla["Intereses total (€)"].sum(),2)
    total_capital_intereses=round(tabla["Cuota (€)"].sum(),2)

    if seguro_tasa>0:
        total_seguro=round(tabla["Seguro (€)"].sum(),2)

    cuotas_tae=[-capital]+list(tabla["Cuota (€)"])
    fechas_tae=[fecha_inicio]+list(tabla["Fecha recibo"])

    tae=calcular_tae(cuotas_tae,fechas_tae)

    # ---------------------------------------------------------
    # RESUMEN
    # ---------------------------------------------------------

    if seguro_tasa>0:

        resumen_dict={
        "Concepto":[
        "Duración (meses)",
        "Intereses (€)",
        "Seguro (€) total",
        "Coste total (capital+intereses)",
        "Coste total (capital+intereses+seguro)",
        "TAE (%)"
        ],
        "Valor":[
        len(tabla),
        total_intereses,
        total_seguro,
        total_capital_intereses,
        round(total_capital_intereses+total_seguro,2),
        tae
        ]
        }

    else:

        resumen_dict={
        "Concepto":[
        "Duración (meses)",
        "Intereses (€)",
        "Coste total (capital+intereses)",
        "TAE (%)"
        ],
        "Valor":[
        len(tabla),
        total_intereses,
        total_capital_intereses,
        tae
        ]
        }

    df_resumen=pd.DataFrame(resumen_dict)

    st.subheader("Resumen")
    st.table(df_resumen)

    # ---------------------------------------------------------
    # EXPORTAR A EXCEL
    # ---------------------------------------------------------

    output = BytesIO()

    # SOLUCIÓN 1 → sin engine para evitar error en Streamlit Cloud
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
