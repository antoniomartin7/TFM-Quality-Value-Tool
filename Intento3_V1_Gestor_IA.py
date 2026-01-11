# NOMBRE DEL FICHERO: Intento3_V1_Gestor_IA.py

import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold

# --- 1. CONFIGURACIÓN DE PERSONALIDAD Y FORMATO (CONSTANTE) ---
INSTRUCCIONES_DEL_SISTEMA = """
Eres un Analista de Inversiones Senior experto en la estrategia 'Quality Value' y gestión de riesgos.

TU TAREA:
Recibirás datos fundamentales y noticias de una empresa recabados por un algoritmo. Debes cruzar esta información para validar si la valoración devuelta por el algoritmo (COMPRAR / NEUTRAL/PRECAUCIÓN / DESCARTAR) es razonable.

TU FILOSOFÍA DE INVERSIÓN:
1. Buscas identificar empresas de alta calidad a precios razonables, exiges un Margen de Seguridad claro en el precio (PER NTM menor que su Referencia).
2. Priorizas la seguridad del dividendo, recompras y el flujo de caja libre (FCF), es decir, devolver valor al accionista.
3. No eres escéptico, aunque buscas evitar "Trampas de Valor" (empresas baratas con problemas estructurales de su negocio).
4. ANÁLISIS DE LA TENDENCIA DE BENEFICIOS (CRÍTICO): Analiza la relación entre PER LTM y PER NTM:
    4.1.CASO CRECIMIENTO (PER NTM < PER LTM): Interpreta esto como una expectativa de mejora operativa o crecimiento de beneficios. No menciones "no deterioro" o similares en este caso; habla de "expansión de beneficios" o "mejora de eficiencia".
    4.2.CASO CONTRACCIÓN (PER NTM > PER LTM): Aquí sí debes activar tu alerta de riesgo y confirmar si realmente es un riesgo. Distingue si la caída de beneficio futuro es por (1) deterioro real, (2) normalización tras un año extraordinario (one-off) o (3) problema temporal. **NO asumas automáticamente un deterioro real**, antes debes **INVESTIGAR A FONDO LA CAÍDA DEL BENEFICIO EN FUENTES FIABLES** para incluir el motivo en la JUSTIFICACIÓN.

FORMATO DE RESPUESTA OBLIGATORIO (IMPORTANTE: USA MARKDOWN):
- Usa títulos grandes (###) para las secciones principales.
- Usa listas con viñetas (-) para los puntos.
- Usa **negritas** para resaltar los conceptos clave al inicio de cada punto.
- Sé conciso. No escribas párrafos largos.
- IMPORTANTE: La decision final debe ser exactamente como se indica en el apartado 3: COMPRAR ó NEUTRAL/PRECAUCIÓN ó DESCARTAR.

ESTRUCTURA DE RESPUESTA OBLIGATORIA (Sigue este esquema visual):

### ✅ 1. PUNTOS FUERTES
- **Calidad del Beneficio y Generación de FCF:** <Tu análisis aquí>
- **Dividendos y Recompras:** <Tu análisis aquí>
- **Deuda:** <Tu análisis aquí>
- **Otros (Noticias/Contexto):** <Tu análisis aquí>

### ⚠️ 2. PUNTOS DÉBILES
- **Calidad del Beneficio y Generación de FCF:** <Tu análisis aquí: tener en cuenta especialmente indicaciones del punto "4.2 de la sección "TU FILOSOFÍA DE INVERSIÓN">
- **Dividendos y Recompras:** <Tu análisis aquí>
- **Deuda:** <Tu análisis aquí>
- **Otros (Noticias/Contexto):** <Tu análisis aquí>

### 🏁 3. CONCLUSIÓN FINAL
- **DECISIÓN:** [COMPRAR] / [NEUTRAL/PRECAUCIÓN] / [DESCARTAR]. A la hora de tomar la decisión, considera:
        - La información cuantitativa enviada por el algoritmo.
        - La ponderación entre Puntos Fuertes y Débiles enviados por el algoritmo.
        - Si está cara o barata por valoración (especialmente por PER NTM respecto al PER NTM de Referencia).
        - TEMPORALIDAD: Si el retorno al accionista es alto, para empresas de alta calidad los buenos momentos de compra se dan cuando se producen problemas temporales. Si estamos ante un problema temporal en una empresa de calidad la decisión debe tender a COMPRAR.
        - VALORACIÓN ALTA: Si la empresa está cara, no se debe recomendar COMPRAR aunque sea de alta calidad.
        - La causa del descuento (Oportunidad vs Trampa de Valor).
- **JUSTIFICACIÓN:**
      <Escribe aquí un párrafo de máximo 100 palabras que sintetice la decisión. Sé conciso y directo. Ve al grano. Debe permitir al inversor entender rápidamente las razones de tu veredicto.
            Sigue esta lógica mental para redactarlo:
            - DINÁMICA DE BENEFICIOS (LTM vs NTM): tener en cuenta especialmente indicaciones del punto "4" de la sección "TU FILOSOFÍA DE INVERSIÓN"
            - PONDERACIÓN: ¿Los "Puntos Fuertes" (ej. Dividendos/Recompras) son suficientes para compensar los "Puntos Débiles" (ej. Riesgos en noticias)?
            - CAUSA DEL DESCUENTO: ¿Por qué está barata la acción? ¿Es un miedo temporal injustificado (Oportunidad) o el negocio se está deteriorando (Trampa de Valor)?
            - COHERENCIA: Si hay una Alerta Contable (P/FCF alto, por ejemplo), la justificación debe señalar los motivos. Si la alerta incluye "Requiere investigación más profunda", investiga el motivo de dicha alerta, NO debes indicarle al usuario que invstigue, ya que esa es tu labor.>
            - TEMPORALIDAD: Para empresas de alta calidad los buenos momentos de compra se dan cuando se producen problemas temporales. Si estamos ante un problema temporal en una empresa de calidad la decisión debe tender a COMPRAR.
"""

# --- 2. CONFIGURACIÓN DE SEGURIDAD ---
# Permite que la IA hable de temas financieros "sensibles" sin bloquearse
CONFIGURACION_SEGURIDAD = {
    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
}

def generar_analisis_gemini(api_key, ticker, datos_financieros, informe_gatekeeper):
    """
    Construye el prompt avanzado y solicita el análisis a Gemini.
    """
    if not api_key:
        return "⚠️ Error: No se ha proporcionado una API Key de Google Gemini."

    try:
        # A. Autenticación
        genai.configure(api_key=api_key)
        
        # B. Inicialización del Modelo con Instrucciones del Sistema
        # Usamos 'gemini-3-flash-preview' ó gemini-2.5-flash' o 'gemini-2.5-flash-lite'
        model = genai.GenerativeModel(
            model_name='gemini-3-flash-preview',
            system_instruction=INSTRUCCIONES_DEL_SISTEMA
        )

        # C. Preparación de Datos para el Prompt
        
        # 1. Noticias
        lista_noticias = datos_financieros.get('noticias', [])
        texto_noticias = "\n- " + "\n- ".join(lista_noticias) if lista_noticias else "No hay noticias recientes relevantes."

        # 2. Factores Técnicos (Alertas y Puntos Fuertes del Gatekeeper)
        factores_gatekeeper = ""
        if informe_gatekeeper['puntos_fuertes']:
            factores_gatekeeper += "\nPUNTOS A FAVOR DETECTADOS:\n- " + "\n- ".join(informe_gatekeeper['puntos_fuertes']) + "\n"
        if informe_gatekeeper['alertas']:
            factores_gatekeeper += "\nALERTAS AUTOMÁTICAS MODERADAS:\n- " + "\n- ".join(informe_gatekeeper['alertas'])
        if informe_gatekeeper['alertas_criticas']:
            factores_gatekeeper += "\nALERTAS AUTOMÁTICAS CRÍTICAS:\n- " + "\n- ".join(informe_gatekeeper['alertas_criticas'])
     
        # --- CORRECCIÓN DE FORMATOS (Sanitización de "N/A") ---
        # Antes de crear el f-string, preparamos las variables para que no den error si son texto ("N/A")
        def safe_fmt(valor, formato=".2f", sufijo=""):
            if isinstance(valor, (int, float)):
                return f"{valor:{formato}}{sufijo}"
            return str(valor) # Si es "N/A", devuelve "N/A" sin intentar formatear decimales

        str_precio = safe_fmt(datos_financieros['precio'], ".2f")
        # Formateos específicos para PER LTM (puede ser negativo)
        if datos_financieros['per_ltm'] == -1.0:
            str_per_ltm = "Negativo"
        else:
            str_per_ltm = safe_fmt(datos_financieros['per_ltm'], ".1f", "x")
        
        str_per_ntm = safe_fmt(datos_financieros['per_ntm'], ".1f", "x")
        str_div = safe_fmt(datos_financieros['div_yield'], ".2%")
        str_buyback = safe_fmt(datos_financieros['buyback_yield'], ".2%")
        str_fcf_mc = safe_fmt(datos_financieros['fcf_yield_mc'], ".2%")
        str_payout = safe_fmt(datos_financieros['payout_ratio'], ".2%")
        str_fcf_ev = safe_fmt(datos_financieros['fcf_yield_ev'], ".2%")
        str_solvencia = safe_fmt(datos_financieros['ratio_solvencia'], ".2f", "x")
             
        # --- D. CONSTRUCCIÓN DEL PROMPT DE USUARIO (EL CASO ESPECÍFICO) ---
        prompt_usuario = f"""
        OBJETIVO: Validar oportunidad de inversión en **{ticker}**.
        
        1. DATOS FUNDAMENTALES (Hard Data - TTM):\n
        - ESTADO SEGÚN ALGORITMO: ({informe_gatekeeper['decision']})
        - Precio Actual: ${str_precio}
        - PER LTM : {str_per_ltm}
        - PER NTM: {str_per_ntm}
        - Dividend Yield: {str_div}
        - Buyback Yield: {str_buyback}
        - Payout Ratio (Dividendo / FCF): {str_payout}
        - FCF Yield LTM (sobre MC): {str_fcf_mc}
        - FCF Yield LTM (sobre EV): {str_fcf_ev}
        - Solvencia (Deuda Neta / EBITDA-Capex): {str_solvencia}
        
        2. FACTORES TÉCNICOS Y ALERTAS PREVIAS (Gatekeeper):
        {factores_gatekeeper}
        
        3. NOTICIAS RECIENTES (Contexto):
        {texto_noticias}
        
                
        DAME TU VEREDICTO FINAL SIGUIENDO LA ESTRUCTURA OBLIGATORIA.
        """

        # E. Generación

        generation_conf = genai.types.GenerationConfig(
            temperature=0.0, 
            candidate_count=1
        )

        response = model.generate_content(
            prompt_usuario,
            safety_settings=CONFIGURACION_SEGURIDAD,
            generation_config=generation_conf
        )
        
        texto_respuesta = response.text
        
        # --- EXTRACTOR DE DECISIÓN Y JUSTIFICACIÓN IA ---
        decision_ia = "NO DETECTADA" # Valor por defecto por si falla el parseo
        justificacion_ia = "No disponible" # Valor por defecto por si falla el parseo
        
        try:
            # 1. Extraer DECISIÓN: Recorremos el texto línea a línea buscando el patrón
            for linea in texto_respuesta.split('\n'):
                # Buscamos "DECISIÓN:" (o DECISION:) ignorando mayúsculas/tildes parciales
                if "DECISI" in linea.upper() and "N:" in linea.upper():
                    # Ejemplo típico de línea: "- **DECISIÓN:** [COMPRAR]"
                    
                    # 1. Separamos por los dos puntos y cogemos la parte derecha
                    parte_derecha = linea.split(':')[-1]
                    
                    # 2. Limpiamos "ruido": asteriscos, corchetes, guiones y espacios
                    limpia = parte_derecha.replace('*', '').replace('[', '').replace(']', '').replace('-', '').strip()
                    
                    # 3. Guardamos el resultado (ej: "COMPRAR")
                    if limpia:
                        decision_ia = limpia.upper()
                        break
            # 2. Extraer JUSTIFICACIÓN: Buscamos la etiqueta "JUSTIFICACIÓN:"
            if "JUSTIFICACIÓN:**" in texto_respuesta:
                # Partimos el texto en dos usando la etiqueta como separador
                partes = texto_respuesta.split("JUSTIFICACIÓN:**")
                if len(partes) > 1:
                    # Cogemos la segunda parte y limpiamos espacios extra
                    justificacion_ia = partes[1].strip()
            elif "JUSTIFICACIÓN:" in texto_respuesta:
                 partes = texto_respuesta.split("JUSTIFICACIÓN:")
                 if len(partes) > 1:
                    justificacion_ia = partes[1].strip()
            elif "**JUSTIFICACIÓN**" in texto_respuesta: # Por si la IA pone negritas diferente
                 partes = texto_respuesta.split("**JUSTIFICACIÓN**")
                 if len(partes) > 1:
                    justificacion_ia = partes[1].strip().lstrip(":").strip()
        
        except Exception as e:
            # Si falla algo en el parseo, no rompemos el programa
            print(f"Warning extrayendo datos IA: {e}")

        # RETORNO MODIFICADO: Añadimos decision_ia al final
        return texto_respuesta, prompt_usuario, decision_ia, justificacion_ia

    except Exception as e:
        # En caso de error de conexión, devolvemos 3 valores para no romper el unpacking en app.py
        return f"❌ Error al conectar con Gemini: {str(e)}", None, "ERROR", ""
    



    