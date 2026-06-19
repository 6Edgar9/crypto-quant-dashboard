import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import datetime
import numpy as np

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Crypto Quant Master", page_icon="🏦", layout="wide")
st.title("🏦 Panel de Inversión Cuantitativa (Fondo Personal)")

# --- 1. MOTOR DE EXTRACCIÓN DE DATOS (BINANCE API) ---
@st.cache_data(ttl=300) # Se actualiza cada 5 minutos
def obtener_mapa_mercado():
    """Extrae las 100 criptos con mayor volumen de Binance para el Mapa de Calor."""
    try:
        resp = requests.get("https://api.binance.com/api/v3/ticker/24hr", timeout=10)
        df = pd.DataFrame(resp.json())
        df = df[df['symbol'].str.endswith('USDT')]
        df['symbol'] = df['symbol'].str.replace('USDT', '')
        # Convertir a números para poder graficar
        for col in ['priceChangePercent', 'quoteVolume', 'lastPrice']:
            df[col] = df[col].astype(float)
        # Filtrar el Top 100 por volumen de dinero real (liquidez)
        df = df.sort_values(by='quoteVolume', ascending=False).head(100)
        return df
    except:
        return pd.DataFrame()

@st.cache_data(ttl=3600)
def obtener_historico_diario(symbol, dias=1000):
    """Extrae velas diarias precisas."""
    try:
        url = f"https://api.binance.com/api/v3/klines?symbol={symbol}USDT&interval=1d&limit={dias}"
        resp = requests.get(url, timeout=10)
        df = pd.DataFrame(resp.json(), columns=['timestamp', 'Open', 'High', 'Low', 'Close', 'Volume', 'close_time', 'qav', 'num_trades', 'taker_base_vol', 'taker_quote_vol', 'ignore'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df['Close'] = df['Close'].astype(float)
        df.set_index('timestamp', inplace=True)
        return df[['Close']]
    except:
        return pd.DataFrame()

# Variables Globales
df_mercado = obtener_mapa_mercado()
monedas_disponibles = df_mercado['symbol'].tolist() if not df_mercado.empty else ['BTC', 'ETH', 'BNB', 'SOL']

# --- INTERFAZ PRINCIPAL (TABS) ---
tab1, tab2, tab3, tab4 = st.tabs([
    "🗺️ 1. Mapa de Calor (Mercado)", 
    "💼 2. Gestor de Portafolio", 
    "📅 3. Simulador DCA", 
    "🎯 4. Escalera Take-Profit"
])

# ==========================================
# PESTAÑA 1: MAPA DE CALOR (TREEMAP)
# ==========================================
with tab1:
    st.subheader("Radar de Liquidez y Tendencia (Top 100 Binance)")
    st.markdown("Los cuadros más grandes mueven más dinero. **Verde = Sube**, **Rojo = Baja**.")
    
    if not df_mercado.empty:
        # Dibujar Treemap Quant
        fig_tree = px.treemap(
            df_mercado, 
            path=[px.Constant("Ecosistema Cripto"), 'symbol'], 
            values='quoteVolume',
            color='priceChangePercent',
            color_continuous_scale='RdYlGn', # Escala Rojo -> Amarillo -> Verde
            color_continuous_midpoint=0,
            custom_data=['lastPrice', 'priceChangePercent', 'quoteVolume']
        )
        fig_tree.update_traces(
            hovertemplate='<b>%{label}</b><br>Precio: $%{customdata[0]:.4f}<br>Cambio 24h: %{customdata[1]:.2f}%<br>Volumen: $%{customdata[2]:,.0f}'
        )
        fig_tree.update_layout(margin=dict(t=20, l=20, r=20, b=20), height=700, template="plotly_dark")
        st.plotly_chart(fig_tree, use_container_width=True)
    else:
        st.warning("No se pudo cargar el mapa. Verifica la API de Binance.")

# ==========================================
# PESTAÑA 2: GESTOR DE PORTAFOLIO REAL
# ==========================================
with tab2:
    st.subheader("Tu Bóveda de Inversión (PNL en Tiempo Real)")
    
    # Inicializar portafolio vacío en memoria si no existe
    if 'portafolio' not in st.session_state:
        st.session_state.portafolio = pd.DataFrame(
            [{"Moneda": "BTC", "Cantidad": 0.05, "Precio_Compra_Promedio": 45000.0}],
            columns=["Moneda", "Cantidad", "Precio_Compra_Promedio"]
        )

    st.markdown("💡 **Instrucciones:** Haz doble clic en la tabla para añadir tus monedas reales o editar tus compras.")
    
    # Tabla editable interactiva
    df_editado = st.data_editor(
        st.session_state.portafolio,
        num_rows="dynamic",
        column_config={
            "Moneda": st.column_config.SelectboxColumn("Criptomoneda", options=monedas_disponibles, required=True),
            "Cantidad": st.column_config.NumberColumn("Cantidad (Bags)", min_value=0.0, format="%.6f"),
            "Precio_Compra_Promedio": st.column_config.NumberColumn("Precio Promedio ($)", min_value=0.0, format="$%.2f"),
        },
        use_container_width=True
    )
    st.session_state.portafolio = df_editado

    if st.button("🔄 Calcular Valor Actual del Portafolio", type="primary"):
        if not df_editado.empty and not df_mercado.empty:
            resultados = []
            costo_total = 0
            valor_actual_total = 0
            
            for idx, row in df_editado.iterrows():
                moneda = row['Moneda']
                cantidad = row['Cantidad']
                precio_compra = row['Precio_Compra_Promedio']
                
                # Buscar el precio actual en el DataFrame del mercado
                precio_actual = df_mercado.loc[df_mercado['symbol'] == moneda, 'lastPrice'].values
                precio_actual = precio_actual[0] if len(precio_actual) > 0 else 0
                
                costo_base = cantidad * precio_compra
                valor_hoy = cantidad * precio_actual
                pnl = valor_hoy - costo_base
                pnl_porcentaje = (pnl / costo_base * 100) if costo_base > 0 else 0
                
                costo_total += costo_base
                valor_actual_total += valor_hoy
                
                resultados.append({
                    "Activo": moneda,
                    "Precio Actual": precio_actual,
                    "Inversión": costo_base,
                    "Valor Hoy": valor_hoy,
                    "Ganancia/Pérdida": pnl,
                    "Rendimiento (%)": pnl_porcentaje
                })
            
            # --- Renderizar Panel Cuantitativo ---
            col1, col2, col3 = st.columns(3)
            pnl_total = valor_actual_total - costo_total
            rendimiento_total = (pnl_total / costo_total * 100) if costo_total > 0 else 0
            
            col1.metric("Capital Invertido", f"${costo_total:,.2f}")
            col2.metric("Valor del Portafolio", f"${valor_actual_total:,.2f}", f"{rendimiento_total:,.2f}%")
            col3.metric("Ganancia Neta (PNL)", f"${pnl_total:,.2f}", "Rendimiento Global")
            
            st.divider()
            
            # Gráfico de Distribución del Riesgo (Pastel)
            df_res = pd.DataFrame(resultados)
            fig_pie = px.pie(df_res, values='Valor Hoy', names='Activo', hole=0.4, title="Distribución de Riesgo del Portafolio")
            fig_pie.update_layout(template="plotly_dark")
            
            c1, c2 = st.columns([1, 1.5])
            with c1: st.dataframe(df_res.style.format({"Precio Actual": "${:.4f}", "Inversión": "${:.2f}", "Valor Hoy": "${:.2f}", "Ganancia/Pérdida": "${:.2f}", "Rendimiento (%)": "{:.2f}%"}))
            with c2: st.plotly_chart(fig_pie, use_container_width=True)

# ==========================================
# PESTAÑA 3: SIMULADOR DE DCA MÁQUINA DEL TIEMPO
# ==========================================
with tab3:
    st.subheader("Simulador Dollar Cost Averaging (DCA)")
    st.markdown("Descubre qué hubiera pasado si invertías una pequeña cantidad mensual ignorando las caídas del mercado.")
    
    col_d1, col_d2, col_d3 = st.columns(3)
    moneda_dca = col_d1.selectbox("Moneda a acumular:", monedas_disponibles, index=monedas_disponibles.index('BTC') if 'BTC' in monedas_disponibles else 0)
    inversion_mensual = col_d2.number_input("Inversión cada 30 días ($ USDT):", value=100.0, step=50.0)
    fecha_inicio_dca = col_d3.date_input("Comenzando desde:", datetime.date(2022, 1, 1))

    if st.button("🕰️ Iniciar Simulación DCA"):
        with st.spinner("Construyendo máquina del tiempo..."):
            df_hist = obtener_historico_diario(moneda_dca, 1500)
            fecha_dca_dt = pd.to_datetime(fecha_inicio_dca)
            
            if not df_hist.empty:
                df_hist = df_hist[df_hist.index >= fecha_dca_dt]
                
                # Lógica Quant de DCA: Comprar cada 30 días
                # Extraemos 1 día cada 30 filas
                df_compras = df_hist.iloc[::30].copy()
                df_compras['USDT_Invertidos'] = inversion_mensual
                df_compras['Criptos_Compradas'] = inversion_mensual / df_compras['Close']
                
                # Acumulación progresiva
                df_compras['Total_USDT_Invertido'] = df_compras['USDT_Invertidos'].cumsum()
                df_compras['Total_Cripto_Acumulado'] = df_compras['Criptos_Compradas'].cumsum()
                
                # Cruzar el acumulado de regreso al DataFrame diario para graficar la línea de valor
                df_hist['Cripto_Poseida'] = df_compras['Total_Cripto_Acumulado']
                df_hist['Cripto_Poseida'] = df_hist['Cripto_Poseida'].ffill().fillna(0) # Propagar los balances
                df_hist['Total_USDT_Invertido'] = df_compras['Total_USDT_Invertido']
                df_hist['Total_USDT_Invertido'] = df_hist['Total_USDT_Invertido'].ffill().fillna(0)
                
                # Valor del portafolio cada día
                df_hist['Valor_del_Portafolio'] = df_hist['Cripto_Poseida'] * df_hist['Close']
                
                # Resultados Finales
                total_gastado = df_hist['Total_USDT_Invertido'].iloc[-1]
                valor_final = df_hist['Valor_del_Portafolio'].iloc[-1]
                monedas_totales = df_hist['Cripto_Poseida'].iloc[-1]
                roi = ((valor_final - total_gastado) / total_gastado) * 100
                
                st.success(f"### Resultados Estrategia DCA: {moneda_dca}")
                c_a, c_b, c_c = st.columns(3)
                c_a.metric("Dinero que salió de tu bolsillo", f"${total_gastado:,.2f}")
                c_b.metric("Monedas Acumuladas", f"{monedas_totales:,.4f} {moneda_dca}")
                c_c.metric("Valor del Portafolio Hoy", f"${valor_final:,.2f}", f"ROI: {roi:,.2f}%")
                
                # Gráfica de Crecimiento
                fig_dca = go.Figure()
                fig_dca.add_trace(go.Scatter(x=df_hist.index, y=df_hist['Total_USDT_Invertido'], mode='lines', name='Capital Invertido (USDT)', line=dict(color='orange', dash='dash')))
                fig_dca.add_trace(go.Scatter(x=df_hist.index, y=df_hist['Valor_del_Portafolio'], mode='lines', name='Valor del Portafolio', line=dict(color='green', width=2)))
                fig_dca.update_layout(title="Rendimiento de Inversión vs Capital Aportado", template="plotly_dark", hovermode="x unified")
                st.plotly_chart(fig_dca, use_container_width=True)
            else:
                st.error("No hay datos históricos para esta moneda.")

# ==========================================
# PESTAÑA 4: ESCALERA DE TOMA DE GANANCIAS
# ==========================================
with tab4:
    st.subheader("Arquitectura de Salida (Take-Profit Ladder)")
    st.markdown("Nunca vendas todo de golpe. Asegura tu capital inicial y deja correr las ganancias sin estrés.")
    
    col_t1, col_t2, col_t3 = st.columns(3)
    moneda_tp = col_t1.selectbox("Moneda a Planificar:", monedas_disponibles, key="tp_coin")
    inversion_tp = col_t2.number_input("Total Invertido (USDT):", min_value=10.0, value=1000.0, step=100.0)
    precio_compra_tp = col_t3.number_input("Precio Promedio de Compra:", min_value=0.000001, value=50.0, format="%.6f")
    
    if st.button("⚙️ Generar Plan de Salida Institucional"):
        cantidad_monedas = inversion_tp / precio_compra_tp
        
        # Estrategia Conservadora Clásica:
        # 1. Recuperar capital inicial (Vendiendo parte a +100%)
        # 2. Tomar ganancias medias (Vender otra parte a +200%)
        # 3. Dejar un Moonbag (No vender hasta +500%)
        
        estrategia = [
            {"Fase": "1. Primer Cobro", "Objetivo": "+50%", "Porcentaje_a_Vender": 30},
            {"Fase": "2. Recuperar Inversión", "Objetivo": "+100%", "Porcentaje_a_Vender": 30},
            {"Fase": "3. Ganancia Extrema", "Objetivo": "+200%", "Porcentaje_a_Vender": 20},
            {"Fase": "4. Moonbag (Para la Luna)", "Objetivo": "+500%", "Porcentaje_a_Vender": 20},
        ]
        
        datos_plan = []
        monedas_restantes = cantidad_monedas
        
        for paso in estrategia:
            multiplicador = 1 + (int(paso["Objetivo"].replace('+','').replace('%','')) / 100)
            precio_objetivo = precio_compra_tp * multiplicador
            monedas_a_vender = cantidad_monedas * (paso["Porcentaje_a_Vender"] / 100)
            dinero_recuperado = monedas_a_vender * precio_objetivo
            monedas_restantes -= monedas_a_vender
            
            datos_plan.append({
                "Estrategia": paso["Fase"],
                "Precio Objetivo": f"${precio_objetivo:,.4f}",
                "Crecimiento": paso["Objetivo"],
                "Vendes (%)": f"{paso['Porcentaje_a_Vender']}%",
                "Monedas Vendidas": round(monedas_a_vender, 4),
                "Bolsillo (USDT Extraídos)": dinero_recuperado
            })
            
        df_tp = pd.DataFrame(datos_plan)
        
        st.write(f"**Tienes {cantidad_monedas:,.4f} {moneda_tp} compradas a ${precio_compra_tp:,.4f}**")
        st.table(df_tp.style.format({"Bolsillo (USDT Extraídos)": "${:,.2f}"}))
        
        total_recuperado = df_tp["Bolsillo (USDT Extraídos)"].sum()
        st.success(f"🏆 Si se cumplen los objetivos, transformarías tus **${inversion_tp:,.2f}** iniciales en **${total_recuperado:,.2f} USDT** en efectivo.")