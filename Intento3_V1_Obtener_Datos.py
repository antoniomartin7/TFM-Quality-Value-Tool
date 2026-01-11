# NOMBRE DEL FICHERO: gestor_datos.py

import yfinance as yf
import pandas as pd
import json

def _obtener_valor_ttm(df_quarterly, keys_posibles):
    """
    Función auxiliar para calcular el TTM (Trailing Twelve Months) que es lo mismo que LTM,
    sumando los últimos 4 trimestres disponibles de un DataFrame.
    """
    if df_quarterly is None or df_quarterly.empty:
        return 0.0
    
    # Buscamos la primera clave que exista en el índice
    key_encontrada = None
    for k in keys_posibles:
        if k in df_quarterly.index:
            key_encontrada = k
            break
            
    if key_encontrada:
        try:
            # Seleccionamos la fila
            fila = df_quarterly.loc[key_encontrada]
            # Seleccionamos hasta las últimas 4 columnas (trimestres)
            # Yahoo suele ordenar columnas de más reciente (izq) a más antiguo (der)
            ultimos_4_q = fila.iloc[:4]
            
            # Si hay menos de 4 trimestres (ej. IPO reciente), sumamos lo que haya
            return ultimos_4_q.sum()
        except Exception:
            return 0.0
    return 0.0

def _obtener_dato_reciente_balance(df_balance, keys_posibles, fallback_value=0):
    """
    Para datos de BALANCE (Deuda, Caja), no se suman trimestres.
    Se coge el dato del ÚLTIMO trimestre disponible (la foto más reciente).
    """
    if df_balance is None or df_balance.empty:
        return fallback_value
        
    for k in keys_posibles:
        if k in df_balance.index:
            try:
                # Retornamos el dato de la columna 0 (el trimestre más reciente)
                return df_balance.loc[k].iloc[0]
            except:
                continue
    return fallback_value

def obtener_datos_financieros(ticker_symbol):
    """
    Descarga y calcula ratios usando TTM (Últimos 4 Trimestres) real.
    """
    try:
        empresa = yf.Ticker(ticker_symbol)
        data = {}

        # --- 1. DATOS ESTÁTICOS Y PRECIO ---
        info = empresa.info
        history = empresa.history(period="5y")
        data['history'] = history
        fast_info = empresa.fast_info
        
        # Precio (Lógica de respaldo robusta)
        precio = fast_info.get('last_price')
        if not precio: precio = info.get('currentPrice')
        if not precio: precio = info.get('previousClose', 0)
        data['precio'] = precio
        
        # Market Cap
        m_cap = fast_info.get('market_cap')
        if not m_cap: m_cap = info.get('marketCap', 0)
        data['market_cap'] = m_cap

        # --- 2. CARGA DE DATAFRAMES TRIMESTRALES ---
        # Estos son vitales para el cálculo TTM
        q_cashflow = empresa.quarterly_cashflow
        q_financials = empresa.quarterly_financials
        q_balance = empresa.quarterly_balance_sheet

        # --- 3. RATIOS BÁSICOS ---
        # A) CÁLCULO MANUAL DEL PER LTM (Price to Earnings)
        # En lugar de fiarnos de 'trailingPE', lo calculamos: Market Cap / Beneficio Neto TTM
        keys_ni = ['Net Income', 'Net Income Common Stockholders', 'Net Income Continuous Operations']
        net_income_ttm = _obtener_valor_ttm(q_financials, keys_ni)
        data['net_income_ttm'] = net_income_ttm # Guardamos el dato bruto por si acaso

        if net_income_ttm > 0:
            # Caso Normal: Empresa con beneficios
            # Usamos el Market Cap que ya obtuvimos arriba
            if data['market_cap'] > 0:
                data['per_ltm'] = data['market_cap'] / net_income_ttm
            else:
                data['per_ltm'] = 0.0 # Error si no hay Market Cap
        elif net_income_ttm < 0:
            # Caso Pérdidas: Asignamos valor de alerta
            # ESTRATEGIA: Asignamos -1.0 para que el Gatekeeper detecte la alerta crítica.
            data['per_ltm'] = -1.0
        else:
            # Caso 0 o Error de datos (sin financial reports)
            data['per_ltm'] = 0.0

        # B) Cálculo PER NTM (Forward PE)
        data['per_ntm'] = info.get('forwardPE', 0)
        
        # C) Dividendo
        raw_div_yield = info.get('dividendYield', 0)
        if raw_div_yield is None: raw_div_yield = 0
        data['div_yield'] = raw_div_yield / 100 if raw_div_yield > 0.2 else raw_div_yield

        # --- 4. CÁLCULOS DE FLUJOS Y EBITDA TTM REALES (SUMA 4 TRIMESTRES) ---

        # A) CAPEX TTM
        keys_capex = ['Capital Expenditure', 'CapitalExpenditures', 'Purchase Of PPE', 'Net PPE Purchase And Sale']
        # El Capex suele ser negativo, obtenemos la suma y luego usaremos abs
        capex_ttm_raw = _obtener_valor_ttm(q_cashflow, keys_capex)
        capex_ttm = abs(capex_ttm_raw) # Lo guardamos positivo para restar luego

        # B) OPERATING CASH FLOW (OCF) TTM
        keys_ocf = ['Operating Cash Flow', 'Total Cash From Operating Activities']
        ocf_ttm = _obtener_valor_ttm(q_cashflow, keys_ocf)

        # C) RECOMPRAS Y EMISIONES TTM
        keys_recompras = ['Repurchase Of Capital Stock', 'Purchase Of Stock', 'Stock Repurchase']
        recompras_ttm_raw = _obtener_valor_ttm(q_cashflow, keys_recompras) # Suele ser negativo
        
        keys_emisiones = ['Issuance Of Capital Stock']
        emisiones_ttm = _obtener_valor_ttm(q_cashflow, keys_emisiones) # Suele ser positivo
        
        # Cálculo Neto TTM
        recompras_netas_ttm = abs(recompras_ttm_raw) - emisiones_ttm

        # D) EBITDA TTM
        # Intentamos obtenerlo de financials trimestrales (Suma de 4Q)
        keys_ebitda = ['Normalized EBITDA', 'EBITDA']
        ebitda_ttm = _obtener_valor_ttm(q_financials, keys_ebitda)
        
        # Si no está en financials, usamos el dato de 'info' (que suele ser TTM) como fallback
        if ebitda_ttm == 0:
            ebitda_ttm = info.get('ebitda', 0)

        # --- 5. DATOS DE BALANCE (FOTO MÁS RECIENTE Q1) ---
        
        # Deuda Total (Último trimestre)
        keys_debt = ['Total Debt', 'Total Debt And Capital Lease Obligation']
        total_debt = _obtener_dato_reciente_balance(q_balance, keys_debt, fallback_value=info.get('totalDebt', 0))
        
        # Caja Total (Último trimestre)
        keys_cash = ['Cash And Cash Equivalents', 'Cash Cash Equivalents And Short Term Investments', 'Total Cash']
        total_cash = _obtener_dato_reciente_balance(q_balance, keys_cash, fallback_value=info.get('totalCash', 0))
        
        # Enterprise Value (Recalculado con datos frescos)
        # EV = MarketCap + Deuda - Caja
        ev_calculado = data['market_cap'] + total_debt - total_cash
        data['enterprise_value'] = ev_calculado if ev_calculado > 0 else data['market_cap']

        # --- 6. CÁLCULO DE RATIOS FINALES ---

        # 6.1 Buyback Yield
        if data['market_cap'] > 0:
            data['buyback_yield'] = recompras_netas_ttm / data['market_cap']
        else:
            data['buyback_yield'] = 0.0

        # 6.2 Solvencia (Deuda Neta / (EBITDA TTM - Capex TTM))
        deuda_neta = total_debt - total_cash
        flujo_solvencia = ebitda_ttm - capex_ttm # EBITDA - Capex (Owner Earnings proxy)
        
        if flujo_solvencia > 0:
            data['ratio_solvencia'] = deuda_neta / flujo_solvencia
        else:
            data['ratio_solvencia'] = "N/A" # Riesgo alto si flujo es negativo

        # 6.3 FCF Yield (Sobre EV)
        # FCF TTM = OCF TTM - Capex TTM
        fcf_ttm = ocf_ttm - capex_ttm
        
        if data['enterprise_value'] > 0:
            data['fcf_yield_ev'] = fcf_ttm / data['enterprise_value']
        else:
            data['fcf_yield_ev'] = 0.0

        #6.4.1 FCF Yield (Sobre Market Cap)
        if data['market_cap'] > 0:
            data['fcf_yield_mc'] = fcf_ttm / data['market_cap']
        else:
            data['fcf_yield_mc'] = 0.0

        # 6.4 Yield Total (Dividendo + Recompras)
        total_yield = data['div_yield'] + data['buyback_yield']
        data['total_yield'] = total_yield

        # 6.5 Payout Ratio (Dividendo / FCF)
        if data['fcf_yield_mc'] > 0:
            data['payout_ratio'] = (data['div_yield'] / data['fcf_yield_mc'])
        else:
            data['payout_ratio'] = "N/A"
            
        # GUARDAMOS DATOS INTERMEDIOS (Opcional, para debug)
        data['debug_capex_ttm'] = capex_ttm
        data['debug_ebitda_ttm'] = ebitda_ttm
        data['debug_fcf_ttm'] = fcf_ttm


        # --- 7. EXTRACCIÓN DE NOTICIAS (CONTEXTO CUALITATIVO) ---
        try:
            # Recuperamos la lista bruta (o lista vacía si es None)
            noticias_raw = empresa.news or []
            titulares = []
            
            # Procesamos hasta 8 noticias como en tu referencia
            for n in noticias_raw[:8]:
                # Lógica robusta: Yahoo a veces anida la info en 'content'
                content = n.get("content", {})
                
                # Prioridad 1: Buscar dentro de 'content' (title > headline > summary)
                # Prioridad 2: Buscar en la raíz (fallback por si cambia la API)
                titulo = (content.get("title") or 
                          content.get("headline") or 
                          content.get("summary") or 
                          n.get("title")) # Fallback a raíz
                
                if titulo:
                    titulares.append(titulo)
            
            # Gestión de lista vacía
            if not titulares:
                titulares = ["No hay noticias recientes disponibles en Yahoo Finance."]
                
            # Guardamos como LISTA (gestor_ia.py se encarga de convertirlo a texto con saltos de línea)
            data['noticias'] = titulares
            
        except Exception as e:
            # En caso de error inesperado, no rompemos el programa, devolvemos aviso
            print(f"Aviso: Error procesando noticias para {ticker_symbol}: {e}")
            data['noticias'] = ["No se pudieron recuperar noticias recientes (Error API)."]

        return data

    except Exception as e:
        print(f"Error crítico en gestor_datos (TTM) para {ticker_symbol}: {e}")
        return None

        return data
        return data

    except Exception as e:
        print(f"Error crítico en gestor_datos (TTM) para {ticker_symbol}: {e}")
        return None

# ==========================================
# BLOQUE DE PRUEBA
# ==========================================
if __name__ == "__main__":
    
    TICKER_TEST = "PAHGF" 
    print(f"\n--- 🧪 TEST TTM (Últimos 4 Trimestres) PARA: {TICKER_TEST} ---")
    
    datos = obtener_datos_financieros(TICKER_TEST)
    
    if datos:
        print("\n✅ EXTRACCIÓN TTM EXITOSA.")
        
        print("\n📊 DATOS CALCULADOS (TTM Real):")
        print(f"   > Precio:            ${datos['precio']:.2f}")
        print(f"   > Market Cap:        ${datos['market_cap']:,.0f}")
        print(f"   > EV (Calc):         ${datos['enterprise_value']:,.0f}")
        print("-" * 30)
        print(f"   > EBITDA (4Q Sum):   ${datos.get('debug_ebitda_ttm',0):,.0f}")
        print(f"   > CAPEX (4Q Sum):    ${datos.get('debug_capex_ttm',0):,.0f}")
        print(f"   > FCF (4Q Sum):      ${datos.get('debug_fcf_ttm',0):,.0f}")
        print("-" * 30)
        print(f"   > PER (LTM):         {datos['per_ltm']:.1f}x")
        print(f"   > PER (NTM):         {datos['per_ntm']:.1f}x")
        print("-" * 30)
        print(f"   > Div Yield:         {datos['div_yield']*100:.2f}%")
        print(f"   > Buyback Yield:     {datos['buyback_yield']*100:.2f}%")
        print(f"   > FCF Yield (EV):    {datos['fcf_yield_ev']*100:.2f}%")
        print(f"   > FCF Yield (MC):    {datos['fcf_yield_mc']*100:.2f}%")
        print(f"   > Solvencia (D/E-C): {datos['ratio_solvencia']:.2f}x")
        print("-" * 30)
        print(datos['noticias'][:5])  # Mostramos las primeras 5 noticias como prueba
    else:
        print("\n❌ FALLO: La función devolvió None.")