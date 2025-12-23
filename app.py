
# IMPORTS
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import tempfile

from reportlab.platypus import SimpleDocTemplate, Paragraph, Image
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm

sns.set_style("whitegrid")


# CONFIG

st.set_page_config(page_title="Dashboard de Mantenimiento", layout="wide")


# SESSION STATE

for key in ["logged", "user", "role"]:
    if key not in st.session_state:
        st.session_state[key] = False if key == "logged" else None


# USERS
USERS = {
    "gerencia": {"password": "gerencia2024", "role": "Gerencia"},
    "operaciones": {"password": "operaciones2024", "role": "Operaciones"},
}

# LOGIN

def login():
    st.title("🔐 Acceso al Dashboard de Mantenimiento")
    user = st.text_input("Usuario")
    password = st.text_input("Contraseña", type="password")

    if st.button("Ingresar"):
        if user in USERS and USERS[user]["password"] == password:
            st.session_state.logged = True
            st.session_state.user = user
            st.session_state.role = USERS[user]["role"]
            st.rerun()
        else:
            st.error("Credenciales incorrectas")


# DATA

@st.cache_data
def load_data():
    xls = "analisis_mantenimiento_final.xlsx"
    return {
        "datos": pd.read_excel(xls, "datos_procesados"),
        "control": pd.read_excel(xls, "control_presupuesto"),
        "anual": pd.read_excel(xls, "comparacion_anual_presupuesto"),
        "fallas": pd.read_excel(xls, "fallas_recurrentes"),
        "drivers": pd.read_excel(xls, "drivers_ml"),
        "forecast": pd.read_excel(xls, "forecast_costos"),
    }


# SAVE FIG

def save_fig(fig):
    f = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
    fig.savefig(f.name, bbox_inches="tight")
    plt.close(fig)
    return f.name

# PDF

def generar_pdf(df, control):
    file = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    doc = SimpleDocTemplate(file.name, pagesize=A4)
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph("Reporte Ejecutivo de Mantenimiento", styles["Title"]))
    story.append(Paragraph("<br/>", styles["Normal"]))

    story.append(Paragraph(f"Gasto Total: ${df['costo'].sum():,.0f}", styles["Normal"]))
    story.append(Paragraph(f"Ahorro Potencial (12%): ${df['costo'].sum()*0.12:,.0f}", styles["Normal"]))
    story.append(Paragraph(
        f"% Correctivo: {(df['clase_mantencion']=='Correctivo').mean()*100:.1f}%",
        styles["Normal"]
    ))
    story.append(Paragraph("<br/>", styles["Normal"]))

    fig, ax = plt.subplots(figsize=(6,3))
    sns.lineplot(data=control, x=control.index, y="costo", ax=ax, label="Gasto")
    sns.lineplot(data=control, x=control.index, y="presupuesto_mantenimiento", ax=ax, label="Presupuesto")
    ax.legend()
    story.append(Image(save_fig(fig), width=16*cm, height=8*cm))

    doc.build(story)
    return file.name

 
# DASHBOARD

def dashboard():
    data = load_data()
    df = data["datos"]
    control = data["control"]
    anual = data["anual"]
    fallas = data["fallas"]
    drivers = data["drivers"]
    forecast = data["forecast"]

    #  SIDEBAR 
    st.sidebar.success(f"{st.session_state.user} ({st.session_state.role})")
    st.sidebar.subheader("Filtros")

    #  FILTROS CLAVE 
    años = sorted(df["año"].unique())
    año_sel = st.sidebar.multiselect("Año", años, default=años)

    clases = sorted(df["clase_mantencion"].unique())
    clase_sel = st.sidebar.multiselect("Clase de mantención", clases, default=clases)

    tipos = sorted(df["tipo_mantencion"].unique())
    tipo_sel = st.sidebar.multiselect("Tipo de mantención", tipos, default=tipos)

    activos = sorted(df["nombre_activo"].unique())
    activo_sel = st.sidebar.multiselect("Activo", activos, default=activos)

    proveedores = sorted(df["nombre_proveedor"].unique())
    proveedor_sel = st.sidebar.multiselect("Proveedor", proveedores, default=proveedores)

    #  APLICAcion de FILTROS 
    df = df[
        df["año"].isin(año_sel) &
        df["clase_mantencion"].isin(clase_sel) &
        df["tipo_mantencion"].isin(tipo_sel) &
        df["nombre_activo"].isin(activo_sel) &
        df["nombre_proveedor"].isin(proveedor_sel)
    ]

    control = control[control["año"].isin(año_sel)]
    anual = anual[anual["año"].isin(año_sel)]

    if st.sidebar.button("Cerrar sesión"):
        st.session_state.logged = False
        st.rerun()

    #  KPIs 
    st.title("📊 Dashboard Ejecutivo de Mantenimiento")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Gasto Total", f"${df['costo'].sum():,.0f}")
    c2.metric("Presupuesto Total", f"${control['presupuesto_mantenimiento'].sum():,.0f}")
    c3.metric("Ahorro Potencial (12%)", f"${df['costo'].sum()*0.12:,.0f}")
    c4.metric("% Correctivo", f"{(df['clase_mantencion']=='Correctivo').mean()*100:.1f}%")

    st.divider()

    #  OPERACIONES
    fig, ax = plt.subplots(figsize=(6,4))
    sns.barplot(data=df, x="clase_mantencion", y="costo", estimator=sum, ax=ax)
    ax.set_title("Costo Preventivo vs Correctivo")
    st.pyplot(fig)

    fig, ax = plt.subplots(figsize=(6,4))
    top_activos = df.groupby("nombre_activo")["costo"].sum().nlargest(5).reset_index()
    sns.barplot(data=top_activos, y="nombre_activo", x="costo", ax=ax)
    ax.set_title("Top 5 activos por costo")
    st.pyplot(fig)

    #  EFICIENCIA
    fig, ax = plt.subplots(figsize=(6,4))
    ranking = df.groupby("nombre_activo")["costo_hora"].mean().nlargest(5).reset_index()
    sns.barplot(data=ranking, y="nombre_activo", x="costo_hora", ax=ax)
    ax.set_title("Top 5 activos por costo/hora")
    st.pyplot(fig)

    fig, ax = plt.subplots(figsize=(6,4))
    sns.scatterplot(data=df, x="duracion_horas", y="costo", hue="clase_mantencion", ax=ax)
    ax.set_title("Costo vs duración")
    st.pyplot(fig)

    # PRESUPUESTO 
    fig, ax = plt.subplots(figsize=(8,4))
    sns.lineplot(data=control, x=control.index, y="costo", ax=ax, label="Gasto")
    sns.lineplot(data=control, x=control.index, y="presupuesto_mantenimiento", ax=ax, label="Presupuesto")
    ax.set_title("Gasto vs Presupuesto")
    st.pyplot(fig)

    fig, ax = plt.subplots(figsize=(8,4))
    sns.barplot(data=control, x=control.index, y="desviacion_$", ax=ax)
    ax.set_title("Desviación mensual")
    st.pyplot(fig)

    #  FALLAS
    fig, ax = plt.subplots(figsize=(6,4))
    sns.barplot(data=fallas.head(5), y="nombre_activo", x="frecuencia", ax=ax)
    ax.set_title("Top 5 fallas recurrentes")
    st.pyplot(fig)

    #  ML
    fig, ax = plt.subplots(figsize=(6,4))
    sns.barplot(data=drivers.head(10), y="variable", x="importancia", ax=ax)
    ax.set_title("Drivers del costo (ML)")
    st.pyplot(fig)

    #  FORECAST 
    fig, ax = plt.subplots(figsize=(8,4))
    ax.plot(forecast["fecha"], forecast["costo_forecast"], linestyle="--", color="red")
    ax.set_title("Forecast de costos")
    st.pyplot(fig)

    #  PDF 
    st.divider()
    if st.button("📄 Generar PDF Ejecutivo"):
        pdf = generar_pdf(df, control)
        with open(pdf, "rb") as f:
            st.download_button("Descargar PDF", f, "reporte_mantenimiento.pdf")


# MAIN

if not st.session_state.logged:
    login()
else:
    dashboard()
