# NOMBRE DEL FICHERO: Intento3_V1_GateKeeper.py

def ejecutar_gatekeeper(datos_reales, referencias_historicas):
    """
    Recibe los datos de Yahoo y las referencias del Excel.
    Aplica lógica 'Quality Value' avanzada con detección de trampas de valor.
    Devuelve la decisión final y los motivos detallados.
    """
    resultados = {
        "decision": "",
        "color_logico": "", 
        "puntos_fuertes": [],
        "alertas": [],           # Alertas leves/moderadas
        "alertas_criticas": [],  # Motivos de descarte inmediato
        "motivo_principal": ""
    }

    # --- FASE 0: INTEGRIDAD DE DATOS (SANITY CHECK) ---
    # Antes de valorar, miramos si el negocio gana dinero.
    
    # Chequeo 1: de Solvencia por flujo de caja negativo)
    if datos_reales['fcf_yield_ev'] <= 0:
        resultados['alertas_criticas'].append("⛔ FLUJO DE CAJA NEGATIVO O MUY MERMADO: La empresa no genera caja operativa para cubrir gastos.")
    
    # Chequeo 2: de Beneficios Negativos
    # Solo es CRÍTICO si pierde dinero hoy (LTM) Y se espera que siga perdiendo (NTM)
    if datos_reales['per_ltm'] <= 0 and datos_reales['per_ntm'] <= 0:
        resultados['alertas_criticas'].append("⛔ PÉRDIDAS ESTRUCTURALES: EPS negativo actual y previsión de pérdidas futuras.")
        
    # Si pierde dinero hoy pero se espera que gane mañana, posible problema temporal o partida puntual en beneficios (Riesgo, pero no Descarte)
    elif datos_reales['per_ltm'] <= 0 and datos_reales['per_ntm'] > 0:
        resultados['alertas'].append(f"⚠️ Situación anómala: Pérdidas actuales, pero se estiman beneficios futuros (PER NTM {datos_reales['per_ntm']:.1f}x). Requiere investigación más profunda.")

    # Si hay alertas críticas, paramos AQUÍ. No importa si está barata.
    if resultados['alertas_criticas']:
        resultados['decision'] = "DESCARTAR"
        resultados['color_logico'] = "red"
        resultados['motivo_principal'] = "Problemas estructurales graves (Pérdidas o Flujo Negativo)."
        # Añadimos las críticas a la lista general para que la IA las vea
        return resultados

    # --- FASE 1: FILTRO DE SOLVENCIA (SEGURIDAD) ---
    ref_solvencia = referencias_historicas.get('Ref_Solvencia_Mediana', "N/A")
    
    if datos_reales['debug_ebitda_ttm'] - datos_reales['debug_capex_ttm'] > 0:
    
        # A. Comparación Histórica (¿Está más endeudada de lo habitual?)
        if datos_reales['ratio_solvencia'] > (ref_solvencia * 1.3) and datos_reales['ratio_solvencia'] > 2.5:
            resultados['alertas'].append(f"⚠️ Deuda Creciente: Net Debt / (EBITDA - Capex) (LTM): {datos_reales['ratio_solvencia']:.1f}x (Histórico: {ref_solvencia:.1f}x)")
        
        # B. Límite Absoluto (¿Es demasiada deuda para cualquiera?)
        if datos_reales['ratio_solvencia'] > 5.0:
            resultados['alertas'].append(f"⚠️ Deuda Absoluta Muy Alta: Net Debt / (EBITDA - Capex) (LTM): {datos_reales['ratio_solvencia']:.1f}x (>5x es arriesgado).")
        elif datos_reales['ratio_solvencia'] < 1.5:
            resultados['puntos_fuertes'].append(f"✅ Balance Fuerte: posee un ratio de endeudamiento Net Debt / (EBITDA - Capex) (LTM) reducido ({datos_reales['ratio_solvencia']:.1f}x).")

    # Si EBITDA - Capex es cero o negativo, no podemos calcular ratio de solvencia fiable
    elif datos_reales['debug_ebitda_ttm'] > 0 and datos_reales['debug_ebitda_ttm'] - datos_reales['debug_capex_ttm'] <= 0:
        resultados['alertas'].append("⚠️ Deuda No Evaluable: EBITDA - Capex es cero o negativo, no se puede calcular ratio de solvencia fiable. Requiere investigación más profunda.")

    # Si EBITDA es negativo, no podemos calcular ratio de solvencia fiable
    elif datos_reales['debug_ebitda_ttm'] < 0:
        resultados['alertas'].append("⚠️ Deuda No Evaluable: EBITDA es cero negativo, no se puede calcular ratio de solvencia fiable. Requiere investigación más profunda.")
    
    # --- FASE 2: FILTRO DE CALIDAD DEL BENEFICIO (ACCRUALS) ---
    # Comparamos PER de Ref (Beneficio Contable) con P/FCF actual (Caja Real)
    # Cargamos referencias históricas
    ref_per_ltm = referencias_historicas.get('Ref_PER_LTM_Mediana', "N/A")
    ref_per_ntm = referencias_historicas.get('Ref_PER_NTM_Mediana', "N/A")
    ref_fcf_ev = referencias_historicas.get('Ref_FCF_Yield_Mediana', "N/A")
    # P/FCF aproximado = 1 / FCF Yield
    p_fcf_implicito = 1 / datos_reales['fcf_yield_mc'] if datos_reales['fcf_yield_mc'] > 0 else 99
    
    # Si el PER es 15x pero el P/FCF es 30x, el beneficio es "de papel", no entra caja.
    if p_fcf_implicito > (ref_per_ltm * 1.2):
        resultados['alertas'].append(f"⚠️ Calidad Baja del Beneficio contable por generación de caja mermada, es decir, P/FCF caro ({p_fcf_implicito:.1f}x) vs PER NTM de Ref: ({ref_per_ltm:.1f}).")
    elif p_fcf_implicito < (ref_per_ltm * 0.95):
        resultados['puntos_fuertes'].append(f"✅ Calidad Alta de Beneficio contable: mejor generacion de caja real P/FCF ({p_fcf_implicito:.1f}x) vs PER LTM de Ref: ({ref_per_ltm:.1f}).")

    # --- FASE 3: FILTRO DE VALORACIÓN (PRECIO) ---
    
    # A.1 PER NTM vs PER NTM Histórico
    if datos_reales['per_ntm'] <= ref_per_ntm * 0.95:
        descuento = (1 - (datos_reales['per_ntm'] / ref_per_ntm)) * 100
        resultados['puntos_fuertes'].append(f"✅ Infravalorada por PER NTM: {datos_reales['per_ntm']:.1f}x (Descuento {descuento:.0f}%) respecto al PER NTM de Ref: {ref_per_ntm:.1f}x.")
    elif datos_reales['per_ntm'] > ref_per_ntm * 1.05:
        resultados['alertas'].append(f"PER NTM Elevado: {datos_reales['per_ntm']:.1f}x vs PER NTM de Ref: {ref_per_ntm:.1f}x.")

    # A.2 PER LTM vs PER LTM Histórico
    if datos_reales['per_ltm'] <= ref_per_ltm * 0.95 and datos_reales['per_ltm'] > 0: # Evitamos punto fuerte si PER LTM es negativo
        descuento = (1 - (datos_reales['per_ltm'] / ref_per_ltm)) * 100
        resultados['puntos_fuertes'].append(f"✅ Infravalorada por PER LTM: {datos_reales['per_ltm']:.1f}x (Descuento {descuento:.0f}%) respecto al PER LTM de Ref: {ref_per_ltm:.1f}x.")
    elif datos_reales['per_ltm'] > ref_per_ltm * 1.05 and datos_reales['per_ltm'] > 0: # Evitamos alerta si PER LTM es negativo (ya avisamos antes)
        resultados['alertas'].append(f"PER LTM Elevado: {datos_reales['per_ltm']:.1f}x vs PER LTM de Ref: {ref_per_ltm:.1f}x.")

    # B. FCF Yield vs Histórico
    if datos_reales['fcf_yield_ev'] >= ref_fcf_ev:
        resultados['puntos_fuertes'].append(f"✅ FCF Yield sobre EV Atractivo: {datos_reales['fcf_yield_ev']:.1%}.")
    
    # C. Crecimiento (Forward vs Trailing)
    # Si PER NTM es menor que LTM, el mercado espera crecimiento de beneficios
    if datos_reales['per_ntm'] < (datos_reales['per_ltm'] * 0.95):
         crecimiento = ((datos_reales['per_ltm'] - datos_reales['per_ntm']) / datos_reales['per_ltm']) * 100
         resultados['puntos_fuertes'].append(f"✅ Crecimiento Esperado: Analistas prevén aumento de beneficios del {crecimiento:.0f}% en los próximos 12 meses.")
    elif datos_reales['per_ntm'] > (datos_reales['per_ltm'] * 1.1) and datos_reales['per_ltm'] > 0: # Evitamos alerta si PER LTM es negativo (ya avisamos antes)
         resultados['alertas'].append("⚠️ Posible Deterioro Esperado: Analistas prevén caída de beneficios.")

    # --- FASE 4: FILTRO DE RETORNO (SHAREHOLDER YIELD) ---
    
    # A. Yield Total vs Histórico
    total_yield = datos_reales['div_yield'] + datos_reales['buyback_yield']
    ref_yield = referencias_historicas.get('Ref_Total_Yield', 3)/100  # Pasamos de % a decimal
    
    if total_yield > (ref_yield + 0.01): # 1% mejor que la historia
        resultados['puntos_fuertes'].append(f"✅ Retorno Total Superior: {total_yield:.1%} (Div + Recompras) vs Histórico {ref_yield:.1%}.")
    elif total_yield < (ref_yield * 0.75):
        resultados['alertas'].append(f"Retorno Bajo: {total_yield:.1%} (Div + Recompras)vs Histórico {ref_yield:.1%}.")

    # B. Payout Ratio: Sostenibilidad del dividendo
    if datos_reales['payout_ratio'] != "N/A":
        if datos_reales['payout_ratio'] < 0.6:
            resultados['puntos_fuertes'].append(f"✅ Payout Ratio Saludable: {datos_reales['payout_ratio']:.1%}, lo que indica sostenibilidad en el dividendo.")
        elif datos_reales['payout_ratio'] > 1.0:
            resultados['alertas'].append(f"⚠️ Payout Ratio Insostenible para los últimos 12 meses: {datos_reales['payout_ratio']:.1%}, la empresa paga más en dividendos de lo que genera en FCF.")

    # --- DECISIÓN FINAL Y LÓGICA DE SEMÁFORO ---
    num_puntos_fuertes = len(resultados['puntos_fuertes'])
    num_alertas = len(resultados['alertas'])
    num_alertas_criticas = len(resultados['alertas_criticas'])
    
    # Regla de Descarte por Valoración Pura (Si está cara por todos lados)
    esta_cara_per_ltm = datos_reales['per_ltm'] > (ref_per_ltm * 1.05) or datos_reales['per_ltm'] <= 0
    esta_cara_per_ntm = datos_reales['per_ntm'] > (ref_per_ntm * 1.05) or datos_reales['per_ntm'] <= 0
    esta_cara_fcf = datos_reales['fcf_yield_ev'] < (ref_fcf_ev * 0.95) or datos_reales['fcf_yield_ev'] <= 0
    no_crece = datos_reales['per_ntm'] >= datos_reales['per_ltm'] or datos_reales['per_ntm'] <= 0
    
    if esta_cara_per_ltm and esta_cara_per_ntm and esta_cara_fcf and no_crece:
        resultados['decision'] = "DESCARTAR"
        resultados['color_logico'] = "red"
        resultados['motivo_principal'] = "Empresa sobrevalorada sin expectativas de crecimiento."
        return resultados

    # Evaluación de Riesgo vs Recompensa
    if num_alertas_criticas == 0 and num_alertas <= 1 and num_puntos_fuertes >= 4:
        resultados['decision'] = "COMPRAR"
        resultados['color_logico'] = "green"
        resultados['motivo_principal'] = "Buena combinación de Calidad Y Precio."

    elif num_alertas_criticas == 0 and num_alertas <= 2 and num_puntos_fuertes >= 3:
        resultados['decision'] = "NEUTRAL/PRECAUCIÓN" # Es buena, pero tiene alguna "pega"
        resultados['color_logico'] = "orange"
        resultados['motivo_principal'] = "Valoración neutral o con riesgos moderados (ver alertas)."
        
    else:
        resultados['decision'] = "DESCARTAR"
        resultados['color_logico'] = "red"
        resultados['motivo_principal'] = "Empresa sobrevalorada y/o acumulación excesiva de riesgos."
        
    return resultados