# NOMBRE DEL FICHERO: Intento3_V1_app.py

import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import time
import sys

# --- IMPORTAMOS MÓDULOS ---
from Intento3_V1_Obtener_Datos import obtener_datos_financieros
from Intento3_V1_GateKeeper import ejecutar_gatekeeper
from Intento3_V1_Gestor_IA import generar_analisis_gemini

# Configuración de página
st.set_page_config(page_title="Herramienta TFM", layout="wide")

# --- SIDEBAR: CONFIGURACIÓN ---
with st.sidebar:
    st.header("⚙️ Configuración")
    # Input seguro para la API Key
    gemini_api_key = st.text_input("Google Gemini API Key", type="password")
    if not gemini_api_key:
        st.warning("⚠️ Introduce tu API Key para activar la IA.")
    
    st.divider()

# --- TÍTULO PRINCIPAL ---
st.title("📊 Análisis Fundamental Automatizado (Quality Value)")

# 1. Cargar Excel
try:
    df_refs = pd.read_excel("Referencias.xlsx")
    lista_tickers = df_refs['Ticker'].tolist()
    
    # NUEVO: Creamos un diccionario para "traducir" el ticker a nombre completo
    # Ejemplo: {"MDLZ": "MDLZ (Mondelez International)", ...}
    mapa_nombres = dict(zip(
        df_refs['Ticker'], 
        df_refs['Ticker'] + " (" + df_refs['Nombre'].astype(str) + ")"
    ))

except:
    st.error("⚠️ No se encuentra el archivo 'Referencias.xlsx'. Asegúrate de que está en la carpeta.")
    st.stop()

# --- SELECTOR DE EMPRESAS CON BOTONES DE CONTROL ---

# 1. Inicializamos el estado si no existe
if "empresas_seleccionadas" not in st.session_state:
    # Por defecto seleccionamos la primera de la lista (como tenías antes)
    st.session_state["empresas_seleccionadas"] = lista_tickers[:1]

# 2. Funciones "Callback" para los botones
def seleccionar_todas():
    st.session_state["empresas_seleccionadas"] = lista_tickers

def limpiar_seleccion():
    st.session_state["empresas_seleccionadas"] = []

# 3. Botones de control (Puestos en dos columnas para que queden bonitos)
col1, col2 = st.sidebar.columns(2)
col1.button("✅ Todas", on_click=seleccionar_todas, use_container_width=True)
col2.button("❌ Ninguna", on_click=limpiar_seleccion, use_container_width=True)

# 4. El Multiselect vinculado al estado
seleccion = st.sidebar.multiselect(
    "Selecciona empresas:", 
    options=lista_tickers, 
    format_func=lambda x: mapa_nombres.get(x, x), # <--- ESTA ES LA CLAVE
    key="empresas_seleccionadas" 
)

if st.button("🚀 Ejecutar Análisis"):
    
    if not gemini_api_key:
        st.warning("⚠️ Por favor, introduce tu API Key de Gemini en la barra lateral para activar el análisis cualitativo.")

    # Preparativos
    barra = st.progress(0)
    i = 0
    lista_resultados = [] # <--- AQUÍ GUARDAREMOS LOS DATOS    

    for ticker in seleccion:
        st.markdown(f"---") # Separador visual
                
        col_logo, col_titulo = st.columns([1, 10])
        with col_titulo:
            # 1. Recuperamos los datos del Excel de forma segura antes de pintar
            try:
                # Filtramos el dataframe global para sacar la fila de este ticker
                datos_ref = df_refs[df_refs['Ticker'] == ticker].iloc[0]
                sector = datos_ref['Sector']
                subsector = datos_ref['Subsector']
            except:
                sector = "No definido"
                subsector = "No definido"

            # 2. Pintamos el Título Principal (Grande)
            st.subheader(f"Análisis de {mapa_nombres.get(ticker, ticker)}")
            
            # 3. Pintamos el Subtítulo (Más pequeño y gris)
            # Usamos HTML para ajustar el margen superior negativo (-15px) y pegarlo al título
            st.markdown(f"""
            <div style='margin-top: -15px; margin-bottom: 10px; font-size: 16px; color: #a0a0a0;'>
                <b>Sector:</b> {sector} <span style='margin: 0 10px;'>|</span> <b>Subsector:</b> {subsector}
            </div>
            """, unsafe_allow_html=True)
            
        with st.expander(f"Ver informe detallado de {ticker}", expanded=True):
            
            # A. Referencias Excel
            try:
                fila_ref = df_refs[df_refs['Ticker'] == ticker].iloc[0]
            except:
                st.error(f"El ticker {ticker} no está en el Excel de referencias.")
                continue
            
            # B. OBTENER DATOS (TTM)
            with st.spinner(f"📥 Descargando datos financieros y noticias..."):
                datos = obtener_datos_financieros(ticker)
                
            if datos:

                # Función auxiliar para formatear visualización
                def formatear_ratio_visual(valor):
                    if valor == sys.float_info.max or valor == 0:
                        return "N/A"
                    return f"{valor:.2f}x"               

            
                # --- HACK CSS PARA REDUCIR ESPACIOS VERTICALES EN VISUALIZACIÓN DE KPIs---
                st.markdown("""
                <style>
                    /* 1. Reducir el margen inferior de los títulos H4 (####) */
                    h4 {
                        margin-bottom: 0.1rem !important;
                        padding-bottom: 0rem !important;
                    }
                    
                    /* 2. Reducir el espacio de los divisores (st.divider) */
                    hr {
                        margin-top: 0.5rem !important;
                        margin-bottom: 0.5rem !important;
                    }
                    
                    /* 3. (Opcional) Ajustar el padding interno de los contenedores con borde */
                    div[data-testid="stVerticalBlockBorderWrapper"] > div {
                        gap: 0.5rem; /* Reduce el hueco entre elementos dentro de la caja */
                    }
                </style>
                """, unsafe_allow_html=True)
                
                                
                # --- VISUALIZACIÓN DE KPIs MEJORADA ---

                with st.expander(f"Análisis por Algoritmo de {ticker}", expanded=True):

                    st.markdown("### 📊 Tablero de Control Financiero")

                    # Creamos dos grandes columnas principales para dividir la pantalla
                    # Izquierda: Métricas Fundamentales | Derecha: Gráfico de Precio
                    col_izq, col_der = st.columns([1.2, 1.8], gap="medium")

                    # --- COLUMNA IZQUIERDA: MÉTRICAS FUNDAMENTALES ---
                    with col_izq:
                        # --- GRUPO 1: VALORACIÓN Y PRECIO ---
                        # Usamos st.container(border=True) para crear una "Caja" visual
                        with st.container(border=True):
                            st.markdown("#### 🏷️ Precio y Ratios de Valoración")
                            
                            st.divider() # Línea separadora interna
                            
                            # Sub-columnas dentro de la tarjeta
                            c1, c2 = st.columns(2)
                            
                            c1.metric(
                                "Precio Actual",
                                f"${datos['precio']:.2f}",
                                help="Precio de cierre más reciente"
                            )
                            

                            # Ratio de Solvencia
                            val_solvencia = datos['ratio_solvencia']
                            
                            # Verificamos si es un número (int o float) para poder restar
                            if isinstance(val_solvencia, (int, float)):
                                delta_solvencia = val_solvencia - fila_ref['Ref_Solvencia_Mediana']
                                delta_str = f"{delta_solvencia:.1f}x vs Ref"
                                val_str = formatear_ratio_visual(val_solvencia)
                            else:
                                # Si es "N/A", no calculamos delta
                                delta_str = "N/A"
                                val_str = "N/A"
                            c2.metric(
                                "Solvencia", 
                                val_str, 
                                delta=delta_str,
                                delta_color="inverse", # Menos deuda suele ser mejor
                                help="Deuda Neta / (EBITDA - Capex)"
                            )
                            
                            st.divider() # Línea separadora interna
                            
                            c3, c4 = st.columns(2)
                            
                            # PER Actual
                            if datos['per_ltm'] is not None and datos['per_ltm'] >= 0:
                                per_ltm_val = f"{datos['per_ltm']:.2f}x"
                                delta_per = f"{datos['per_ltm'] - fila_ref['Ref_PER_LTM_Mediana']:.1f}x vs Ref"
                            else:
                                delta_per = "N/A"
                                per_ltm_val = "N/A"
                            c3.metric(
                                "PER (LTM)",
                                per_ltm_val,
                                delta=delta_per,
                                delta_color="inverse",
                                help="PER últimos 12 meses"
                            )
                            
                            # PER Estimado
                            delta_est = datos['per_ntm'] - fila_ref['Ref_PER_NTM_Mediana']
                            c4.metric(
                                "PER (NTM)", 
                                formatear_ratio_visual(datos['per_ntm']), 
                                delta=f"{delta_est:.1f}x vs Ref",
                                delta_color="inverse",
                                help="PER estimado próximos 12 meses"
                            )

                        # --- GRUPO 2: RETORNO AL ACCIONISTA ---
                        with st.container(border=True):
                            st.markdown("#### 💰 Retorno y Flujos (Yields)")
                            
                            st.divider() # Línea separadora interna

                            # Fila 1 de Yields
                            y1, y2, y3 = st.columns(3)
                            
                            delta_div = datos['div_yield'] - (fila_ref['Ref_Div_Yield_Mediana']/100)
                            y1.metric(
                                "Dividend Yield", 
                                f"{datos['div_yield']:.2%}", 
                                delta=f"{delta_div:.2%} vs Ref",
                                help="Rendimiento por dividendos."
                            )
                            
                            delta_buy = datos['buyback_yield'] - (fila_ref['Ref_Buyback_Yield_Mediana']/100)
                            y2.metric(
                                "Buyback Yield", 
                                f"{datos['buyback_yield']:.2%}", 
                                delta=f"{delta_buy:.2%} vs Ref",
                                help="Rendimiento por recompras de acciones."
                            )

                            delta_total = datos['total_yield'] - (fila_ref['Ref_Total_Yield']/100)
                            y3.metric(
                                "Total Yield", 
                                f"{datos['total_yield']:.2%}", 
                                delta=f"{delta_total:.2%} vs Ref",
                                help="Rendimiento total al accionista: Dividendo + Recompras"
                            )
                            
                            st.divider() # Línea separadora interna
                            
                            # Fila 2 de Yields (FCF y Total)
                            y4, y5 = st.columns(2)
                            
                            delta_fcf_ev = datos['fcf_yield_ev'] - (fila_ref['Ref_FCF_Yield_Mediana']/100)
                            y4.metric(
                                "FCF Yield (EV)", 
                                f"{datos['fcf_yield_ev']:.2%}", 
                                delta=f"{delta_fcf_ev:.2%} vs Ref",
                                help="Free Cash Flow / Enterprise Value: indica la rentabilidad del flujo de caja libre respecto al valor total de la empresa."
                            )                      

                            delta_fcf_mc = datos['fcf_yield_mc'] - datos['total_yield']
                            y5.metric(
                                "FCF Yield (MC)",
                                f"{datos['fcf_yield_mc']:.2%}",
                                delta=f"{delta_fcf_mc:.2%} vs Total Yield",
                                help="Free Cash Flow / Market Capitalization: se compara con Total Yield para saber si el retorno está respaldado por caja."
                            )

                    # --- COLUMNA DERECHA: GRÁFICO PROFESIONAL CON PLOTLY ---
                    with col_der:
                        with st.container(border=True):
                            st.markdown("#### 📈 Evolución del Precio (5 años)")
                            
                            hist = datos['history']
                            
                            # Usamos Plotly en lugar de st.line_chart para que sea interactivo
                            fig = go.Figure()
                            
                            # Línea de precio
                            fig.add_trace(go.Scatter(
                                x=hist.index, 
                                y=hist['Close'],
                                mode='lines',
                                name='Precio',
                                line=dict(color='#00FF00' if hist['Close'].iloc[-1] >= hist['Close'].iloc[0] else '#FF0000', width=2),
                                hovertemplate = "$%{y:.2f}"
                            ))
                            
                            # Configuración del diseño "Dark Mode Friendly"
                            fig.update_layout(
                                height=450,
                                margin=dict(l=20, r=20, t=30, b=20),
                                paper_bgcolor='rgba(0,0,0,0)', # Fondo transparente
                                plot_bgcolor='rgba(0,0,0,0)',
                                xaxis=dict(showgrid=False),
                                yaxis=dict(showgrid=True, gridcolor='rgba(128,128,128,0.2)'),
                                hovermode="x unified"
                            )
                            
                            st.plotly_chart(fig, use_container_width=True)
                    # -------------------------------------------------------              

                # C. GATEKEEPER (Lógica Matemática)
                    informe = ejecutar_gatekeeper(datos, fila_ref)
                    
                    # Pintar Resultado Gatekeeper
                    color_map = {"COMPRAR": "green", "NEUTRAL/PRECAUCIÓN": "orange", "DESCARTAR": "red"}
                    color = color_map.get(informe['decision'], "gray")
                    
                    st.markdown(f"### 🤖 Decisión Algorítmica: :{color}[**{informe['decision']}**]")
                    st.info(f"**Lógica:** {informe['motivo_principal']}")
                    st.info(f"Puntos Fuertes y Alertas a continuación detalladas.")

                    # VISUALIZACIÓN DE PUNTOS FUERTES Y ALERTAS ---
                    st.markdown("---") # Separador horizontal
                    
                    # Creamos 2 columnas para ponerlos frente a frente
                    col_pros, col_cons = st.columns(2)

                    with col_pros:
                        st.subheader("✅ Puntos Fuertes")
                        if informe['puntos_fuertes']:
                            for punto in informe['puntos_fuertes']:
                                # Opción A: Cajas verdes (muy visual)
                                st.success(f"📍 {punto}")
                        else:
                            st.markdown("_No hay puntos fuertes destacados._")

                    with col_cons:
                        st.subheader("⚠️ Alertas Detectadas")
                        if informe['alertas']:
                            for alerta in informe['alertas']:
                                # Opción B: Cajas rojas (destaca el riesgo)
                                st.error(f"🚩 {alerta}")
                        else:
                            st.markdown("_No hay alertas moderadas._")
                        if informe['alertas_criticas']:
                            for alerta in informe['alertas_criticas']:
                                st.error(f"🚨 Alerta Crítica: {alerta}")
                        else:
                            st.markdown("_No hay alertas críticas._")
                    
                    st.markdown("---")
                    # -------------------------------------------------------     

                    barra.progress((i + 0.5) / len(seleccion)) # Mitad del progreso hasta aquí

                with st.expander(f"Análisis con IA de {ticker}", expanded=True):
                    # --- INICIALIZAMOS VARIABLES AQUÍ ---
                    # Esto asegura que existan siempre, pase lo que pase en los if/else de abajo
                    texto_justificacion_final = "" 
                    decision_ia = "N/A" 
                # D. ANÁLISIS IA (GEMINI)
                    if informe['decision'] != "DESCARTAR" and gemini_api_key:
                        st.divider()
                        st.markdown("### 🧠 Análisis Cualitativo (IA)")
                        
                        with st.spinner("Generando análisis con Gemini..."):
                            # 0. Desempaquetamos los valores
                            analisis_texto, prompt_debug, decision_ia, justificacion_ia = generar_analisis_gemini(gemini_api_key, ticker, datos, informe)
                            
                            # 1. Mostramos el análisis normal
                            st.markdown(analisis_texto)
                            color2 = color_map.get(decision_ia, "gray")
                            st.markdown(f"### 🤖 Decisión IA: :{color2}[**{decision_ia}**]")
                            
                            # 2. Mostramos el Prompt oculto en un desplegable (SOLO DEBUG)
                            if prompt_debug:
                                with st.expander("🛠️ Ver Prompt técnico enviado a Gemini (Debug)"):
                                    st.caption("Este es el texto exacto que se envió a la IA:")
                                    st.code(prompt_debug, language="markdown")
                            
                            # 3. Si Algoritmo O IA dicen COMPRAR, guardamos la justificación
                            condicion_compra = (informe['decision'] == "COMPRAR") or (decision_ia == "COMPRAR")
                            
                            if condicion_compra:
                                texto_justificacion_final = justificacion_ia
                            else:
                                texto_justificacion_final = "" # O un guion "-" si prefieres
                                    
                    elif informe['decision'] == "DESCARTAR":
                        st.warning("⛔ El análisis de IA se ha omitido...")
                        decision_ia = "DESCARTAR"

                # --- CAPTURA DE DATOS PARA LA TABLA RESUMEN ---
                lista_resultados.append({
                    "Ticker": ticker,
                    "Yield Total": f"{datos['total_yield']:.2%}", # Formateamos a porcentaje
                    "Decisión Algoritmo": informe['decision'],
                    "Decisión IA": decision_ia,
                    "Justificación": texto_justificacion_final
                })
                
            else:
                st.error(f"❌ Error al descargar datos de {ticker}.")

            i += 1
            barra.progress((i) / len(seleccion))
            time.sleep(1) # Respeto a la API

# --- VISUALIZACIÓN DE LA TABLA RESUMEN FINAL ---
    if lista_resultados:
        st.markdown("---")
        st.header("📋 Resumen Ejecutivo")
        
        # 1. Crear DataFrame Completo
        df_resumen = pd.DataFrame(lista_resultados)
        
        # 2. Definir función de estilo (colores)
        def estilo_decision(val):
            val_upper = str(val).upper()
            color = 'black'
            weight = 'normal'
            # Detectamos palabras clave para asignar colores
            if 'COMPRA' in val_upper: # Cubre "COMPRAR", "FUERTE COMPRA"
                color = '#2ecc71'; weight = 'bold' # Verde
            elif 'DESCARTAR' in val_upper or 'VENTA' in val_upper:
                color = '#e74c3c'; weight = 'bold' # Rojo
            elif 'PRECAUCIÓN' in val_upper or 'MANTENER' in val_upper or 'NEUTRAL' in val_upper:
                color = '#f39c12'; weight = 'bold' # Naranja
            return f'color: {color}; font-weight: {weight}'

        # 3. MODIFICACIÓN 1: MOSTRAR TABLA LIMPIA (Sin columna Justificación)
        # Seleccionamos solo las columnas que queremos ver arriba
        cols_visualizar = ["Ticker", "Yield Total", "Decisión Algoritmo", "Decisión IA"]
        
        st.dataframe(
            df_resumen[cols_visualizar].style.map(estilo_decision, subset=['Decisión Algoritmo', 'Decisión IA']),
            use_container_width=True,
            hide_index=True,
            column_config={
                "Ticker": st.column_config.TextColumn("Ticker", width="small"),
                "Yield Total": st.column_config.TextColumn("Yield Total", width="small"),
                "Decisión Algoritmo": st.column_config.TextColumn("Algoritmo", width="medium"),
                "Decisión IA": st.column_config.TextColumn("Analista IA", width="medium"),
            }
        )
        
        # 4. MODIFICACIÓN 2: VISOR DE DETALLES FILTRADO (Solo COMPRAS)
        
        # Filtramos el DF: Nos quedamos con filas donde Algo O IA contengan "COMPRA"
        # Usamos .apply para buscar en cada fila
        def es_oportunidad(row):
            # Convertimos a mayúsculas para asegurar la búsqueda
            algo = str(row['Decisión Algoritmo']).upper()
            ia = str(row['Decisión IA']).upper()
            return 'COMPRAR' in algo or 'COMPRA' in algo or 'COMPRAR' in ia or 'COMPRA' in ia

        df_compras = df_resumen[df_resumen.apply(es_oportunidad, axis=1)]
        
        # Renderizamos el expansor
        with st.expander("🔍 Leer Justificaciones (Solo Oportunidades de Compra)", expanded=True):
            
            if not df_compras.empty:
                st.markdown("A continuación se detallan los motivos de las empresas seleccionadas como **COMPRAR**:")
                
                # Creamos las pestañas solo con los Tickers filtrados
                tickers_compra = df_compras['Ticker'].tolist()
                tabs = st.tabs(tickers_compra)
                
                for i, tab in enumerate(tabs):
                    with tab:
                        # Extraemos los datos de la fila filtrada correspondiente
                        fila = df_compras.iloc[i]
                        
                        # Mostramos decisiones
                        c1, c2 = st.columns(2)
                        c1.info(f"**Algoritmo:** {fila['Decisión Algoritmo']}")
                        c2.info(f"**IA:** {fila['Decisión IA']}")
                        
                        # Mostramos el texto largo
                        st.markdown("### 📝 Justificación")
                        if fila['Justificación']:
                            st.write(fila['Justificación'])
                        else:
                            st.markdown("_No hay justificación detallada disponible (posiblemente la IA no dio motivo o no es compra)._")
            else:
                st.info("ℹ️ Ninguna de las empresas analizadas ha recibido una calificación de COMPRA, por lo que no hay detalles que mostrar.")

    else:
        st.info("No hay resultados para mostrar en el resumen.")