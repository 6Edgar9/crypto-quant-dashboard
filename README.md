# 📈 CryptoQuant Dashboard

Una aplicación web desarrollada en **Python** y **Streamlit** diseñada para realizar análisis cuantitativo, evaluar riesgo de mercado y simular retornos históricos de criptomonedas.

## 🚀 Características
* **Conexión API en Vivo:** Extrae listas de tokens dinámicos de Binance y cruza datos históricos precisos usando Yahoo Finance.
* **Motor de Análisis Técnico:** Calcula e interactúa con gráficos avanzados de Velas Japonesas, Media Móvil Simple (SMA 50), Media Móvil Exponencial (EMA 21) e Índice de Fuerza Relativa (RSI 14).
* **What-If Simulator:** Permite al usuario ingresar una cantidad en USDT y calcular matemáticamente los escenarios de máxima ganancia en el rango histórico seleccionado.
* **Risk/Reward Screener:** Un sistema de evaluación que calcula el ratio Riesgo/Beneficio (RRR) y lee el indicador RSI para dictaminar si el precio actual está en zona de sobrecompra, sobreventa o neutral.

## 🛠️ Tecnologías Usadas
* `Python 3.10+`
* `Streamlit` (Frontend web)
* `Pandas` (Limpieza y manipulación de DataFrames)
* `yfinance` (Ingesta de datos de mercado)
* `Plotly` (Visualización interactiva)

## 🌐 Demo en Vivo
Puedes probar la aplicación funcionando en tiempo real aquí: https://crypto-quant-dashboard.streamlit.app/