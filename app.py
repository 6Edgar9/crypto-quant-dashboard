import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import datetime
import time
import requests

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Crypto Quant Panel", page_icon="📈", layout="wide")
st.title("📈 Panel de Análisis Cripto Cuantitativo")

# --- FUNCIONES DE CÁLCULO ---
@st.cache_data(ttl=3600) # Cache de 1 hora para no saturar la API
def obtener_monedas_mercado():
    try:
        # Extraemos la lista oficial de KuCoin (Sin bloqueo de IP para USA)
        resp = requests.get("https://api.kucoin.com/api/v2/symbols", timeout=5)
        data = resp.json()
        monedas = [item['baseCurrency'] for item in data['data'] if item['quoteCurrency'] == 'USDT' and item['enableTrading']]
        return sorted(list(set(monedas)))
    except:
        return ['BTC', 'ETH', 'BNB', 'SOL', 'XRP', 'ADA', 'DOGE']

def calcular_sma(series, ventana=50): return series.rolling(window=ventana).mean()
def calcular_ema(series, ventana=21): return series.ewm(span=ventana, adjust=False).mean()
def calcular_rsi(series, ventana=14):
    delta = series.diff()
    ganancia = delta.clip(lower=0)
    perdida = -delta.clip(upper=0)
    avg_ganancia = ganancia.ewm(com=ventana - 1, adjust=False).mean()
    avg_perdida = perdida.ewm(com=ventana - 1, adjust=False).mean()
    rs = avg_ganancia / avg_perdida.replace(0, 1e-10)
    return 100 - (100 / (1 + rs))

# --- VARIABLES DE ESTADO ---
if 'datos_procesados' not in st.session_state:
    st.session_state.datos_procesados = {}
if 'resumen_df' not in st.session_state:
    st.session_state.resumen_df = pd.DataFrame()

# --- BARRA LATERAL (CONTROLES) ---
with st.sidebar:
    st.header("⚙️ Parámetros")
    monedas_mercado = obtener_monedas_mercado()
    
    monedas_seleccionadas = st.multiselect("Selecciona Criptomonedas:", monedas_mercado, default=[])
    
    # Fecha dinámica seteada al día 1 del mes actual automáticamente
    hoy = datetime.date.today()
    primer_dia_mes = hoy.replace(day=1)
    fecha_inicio = st.date_input("Fecha de inicio:", value=primer_dia_mes)
    
    btn_analizar = st.button("🚀 Analizar Datos", use_container_width=True, type="primary")

# --- LÓGICA DE EXTRACCIÓN (NUEVO MOTOR KUCOIN) ---
if btn_analizar:
    if not monedas_seleccionadas:
        st.sidebar.error("Selecciona al menos una moneda.")
    else:
        with st.spinner("Descargando datos históricos del Exchange (Anti-Bloqueos)..."):
            # Pedimos 100 días de colchón para que el SMA y el RSI nazcan calculados
            fecha_amortiguada = fecha_inicio - datetime.timedelta(days=100)
            start_ts = int(time.mktime(fecha_amortiguada.timetuple()))
            
            datos_resumen = []
            st.session_state.datos_procesados.clear()
            
            for cripto in monedas_seleccionadas:
                # Endpoint de KuCoin seguro para la nube
                url = f"https://api.kucoin.com/api/v1/market/candles?type=1day&symbol={cripto}-USDT&startAt={start_ts}"
                
                # Simulamos ser un navegador común para evitar cualquier filtro
                headers = {'User-Agent': 'Mozilla/5.0'}
                resp = requests.get(url, headers=headers, timeout=10)
                
                if resp.status_code != 200:
                    st.toast(f"⚠️ Error de conexión con el exchange para {cripto}")
                    continue
                    
                data = resp.json()
                if data.get('code') != '200000' or not data.get('data'):
                    st.toast(f"⚠️ Sin datos históricos en este exchange para {cripto}")
                    continue
                
                # KuCoin devuelve: [timestamp, open, close, high, low, volume, turnover]
                df = pd.DataFrame(data['data'], columns=['timestamp', 'Open', 'Close', 'High', 'Low', 'Volume', 'Turnover'])
                
                # KuCoin entrega los datos al revés (del más nuevo al más viejo). Los invertimos.
                df = df.iloc[::-1].reset_index(drop=True)
                
                df['timestamp'] = pd.to_datetime(df['timestamp'].astype(int), unit='s')
                df.set_index('timestamp', inplace=True)
                
                for col in ['Open', 'High', 'Low', 'Close']:
                    df[col] = df[col].astype(float)
                
                if df.empty or len(df) < 50:
                    st.toast(f"⚠️ Historial insuficiente para calcular RSI en {cripto}")
                    continue
                
                # Inyección de Indicadores Técnicos
                df['SMA_50'] = calcular_sma(df['Close'], 50)
                df['EMA_21'] = calcular_ema(df['Close'], 21)
                df['RSI_14'] = calcular_rsi(df['Close'], 14)
                
                # Filtramos para mostrar desde el día que elegiste en el calendario
                fecha_inicio_dt = pd.to_datetime(fecha_inicio)
                df_filtrado = df.loc[fecha_inicio_dt:]
                
                if df_filtrado.empty: 
                    st.toast(f"⚠️ No hay datos recientes desde tu fecha para {cripto}")
                    continue
                
                st.session_state.datos_procesados[cripto] = df_filtrado
                
                p_actual = df_filtrado['Close'].iloc[-1]
                p_max = df_filtrado['High'].max()
                rsi_act = df_filtrado['RSI_14'].iloc[-1]
                sma_act = df_filtrado['SMA_50'].iloc[-1]
                
                datos_resumen.append({
                    'Moneda': cripto,
                    'Precio ($)': round(p_actual, 4),
                    'RSI (14d)': round(rsi_act, 2),
                    'Estado': "🔴 Sobrecompra" if rsi_act > 70 else ("🟢 Sobreventa" if rsi_act < 30 else "Neutral"),
                    'Caída vs Máx (%)': f"{round(((p_max - p_actual)/p_max)*100, 2)}%",
                    'Tendencia': "📈 Alcista" if p_actual > sma_act else "📉 Bajista"
                })
            
            if datos_resumen:
                st.session_state.resumen_df = pd.DataFrame(datos_resumen)
            else:
                st.sidebar.error("Ninguna moneda tuvo datos suficientes. Intenta otra fecha.")

# --- INTERFAZ PRINCIPAL (TABS) ---
if not st.session_state.datos_procesados:
    st.info("👈 Selecciona tus parámetros en la barra lateral y presiona 'Analizar Datos' para comenzar.")
else:
    tab1, tab2, tab3 = st.tabs(["📊 Mercado y Gráficos", "🧮 Simulador USDT", "🚨 Alertas Estratégicas"])
    
    # PESTAÑA 1: TABLA Y GRÁFICOS
    with tab1:
        st.subheader("Métricas de Resumen")
        st.dataframe(st.session_state.resumen_df, use_container_width=True)
        
        st.divider()
        moneda_grafico = st.selectbox("Selecciona moneda para ver gráfico técnico:", list(st.session_state.datos_procesados.keys()))
        
        df_g = st.session_state.datos_procesados[moneda_grafico]
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.7, 0.3])
        
        fig.add_trace(go.Candlestick(x=df_g.index, open=df_g['Open'], high=df_g['High'], low=df_g['Low'], close=df_g['Close'], name="Precio"), row=1, col=1)
        fig.add_trace(go.Scatter(x=df_g.index, y=df_g['EMA_21'], line=dict(color='orange', width=1.5), name='EMA 21'), row=1, col=1)
        fig.add_trace(go.Scatter(x=df_g.index, y=df_g['SMA_50'], line=dict(color='blue', width=1.5), name='SMA 50'), row=1, col=1)
        
        fig.add_trace(go.Scatter(x=df_g.index, y=df_g['RSI_14'], line=dict(color='purple', width=1.5), name='RSI'), row=2, col=1)
        fig.add_hline(y=70, line_dash="dash", line_color="red", row=2, col=1)
        fig.add_hline(y=30, line_dash="dash", line_color="green", row=2, col=1)
        fig.update_yaxes(range=[10, 90], row=2, col=1)
        
        fig.update_layout(height=600, template="plotly_dark", xaxis_rangeslider_visible=False, margin=dict(l=20, r=20, t=30, b=20))
        st.plotly_chart(fig, use_container_width=True)

    # PESTAÑA 2: SIMULADOR
    with tab2:
        st.subheader("Simulador del Escenario Perfecto")
        col1, col2 = st.columns(2)
        sim_moneda = col1.selectbox("Moneda a simular:", list(st.session_state.datos_procesados.keys()), key="sim_coin")
        usdt_inicial = col2.number_input("USDT a invertir:", min_value=10.0, value=1000.0, step=100.0)
        
        if st.button("Calcular Retorno Histórico"):
            df_s = st.session_state.datos_procesados[sim_moneda]
            p_min, p_max = df_s['Low'].min(), df_s['High'].max()
            monedas_compradas = usdt_inicial / p_min
            valor_final = monedas_compradas * p_max
            ganancia = valor_final - usdt_inicial
            
            st.success(f"### Resultados para {sim_moneda}")
            c1, c2, c3 = st.columns(3)
            c1.metric("Compraste en (Mínimo)", f"${p_min:,.4f}")
            c2.metric("Vendiste en (Máximo)", f"${p_max:,.4f}")
            c3.metric("Ganancia Neta", f"${ganancia:,.2f}", f"+{((ganancia/usdt_inicial)*100):.2f}%")

    # PESTAÑA 3: ALERTAS
    with tab3:
        st.subheader("Risk/Reward Screener")
        colA, colB, colC = st.columns(3)
        alerta_moneda = colA.selectbox("Moneda:", list(st.session_state.datos_procesados.keys()), key="al_coin")
        
        p_actual_al = st.session_state.datos_procesados[alerta_moneda]['Close'].iloc[-1]
        
        p_compra = colB.number_input("Comprar si cae a:", value=float(round(p_actual_al * 0.90, 4)), step=1.0)
        p_venta = colC.number_input("Vender si sube a:", value=float(round(p_actual_al * 1.20, 4)), step=1.0)
        
        if st.button("Evaluar Estrategia"):
            if p_compra >= p_venta:
                st.error("El precio de venta debe ser mayor al de compra.")
            else:
                dist_compra = ((p_actual_al - p_compra) / p_actual_al) * 100
                dist_venta = ((p_venta - p_actual_al) / p_actual_al) * 100
                rrr = (p_venta - p_actual_al) / (p_actual_al - p_compra) if (p_actual_al - p_compra) > 0 else 0
                
                st.write(f"**Precio Actual:** ${p_actual_al:,.4f}")
                st.write(f"**Distancia a Compra:** Caída del {dist_compra:.2f}% | **Distancia a Venta:** Subida del {dist_venta:.2f}%")
                st.write(f"**Ratio Riesgo/Beneficio:** 1 : {rrr:.2f}")
                
                rsi_al = st.session_state.datos_procesados[alerta_moneda]['RSI_14'].iloc[-1]
                if p_actual_al <= p_compra: st.success("🔥 ¡ALERTA! Precio en zona de compra.")
                elif rrr > 2 and rsi_al < 40: st.info("🟢 Buen escenario técnico. RSI sano.")
                elif rsi_al > 70: st.error("🔴 Cuidado: Activo sobrecomprado.")
                else: st.warning("🟡 Zona neutral. Espera a que baje hacia tu compra.")