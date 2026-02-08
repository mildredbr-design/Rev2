
import streamlit as st
import pandas as pd

st.set_page_config(page_title="Simulador Revolving", layout="wide")
st.title("💳 Simulador de Préstamo Revolving - Método Francés con Opciones de Cuota")

# ---------------- FUNCIONES ----------------
def cuota_francesa(capital, interes_anual, meses, cuota_opcional=None):
    """
    Si cuota_opcional está definida, se usa como cuota mensual.
    Si no, se calcula con el método francés.
    """
    i = interes_anual / 12 / 100
    if cuota_opcional is not None:
        return cuota_opcional
    return capital * (i * (1 + i) ** meses) / ((1 + i) ** meses - 1)


def simulador(capital, interes, meses, cuota_opcional=None):
    saldo = capital
    i = interes / 12 / 100
    cuota = cuota_francesa(capital, interes, meses, cuota_opcional)
    datos = []

    for mes in range(1, meses + 1):
        interes_mes = saldo * i
        amort = cuota - interes_mes
        saldo -= amort

        # Evitar saldo negativo
        if saldo < 0:
            amort += saldo
            saldo = 0

        datos.append({
            "Mes": mes,
            "Cuota": round(cuota, 2),
            "Intereses": round(interes_mes, 2),
            "Amortizacion": round(amort, 2),
            "Saldo": round(saldo, 2)
        })

        if saldo <= 0:
            break

    return pd.DataFrame(datos)

# ---------------- INPUTS ----------------
capital = st.number_input("Capital inicial (€)", 0.0, 1000000.0, 10000.0)
interes = st.number_input("Interés anual (%)", 0.0, 100.0, 18.0)
meses = st.number_input("Plazo (meses)", 1, 600, 60)

# Opciones de cuota en porcentaje del capital inicial
opciones_cuota = [2.7, 3, 3.5, 4, 5, 6, 7, 8, 9]
cuota_porcentaje = st.selectbox(
    "Selecciona la cuota mensual (% del capital inicial)",
    opciones_cuota
)

cuota_opcional = capital * (cuota_porcentaje / 100)

# ---------------- CALCULO ----------------
if st.button("Calcular"):
    tabla = simulador(capital, interes, meses, cuota_opcional)
    st.dataframe(tabla, use_container_width=True)

    st.download_button(
        "Descargar Excel",
        tabla.to_excel(index=False),
        "amortizacion_revolving.xlsx"
      )
  
