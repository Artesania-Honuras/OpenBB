"""Panel visual 100 % local para OpenBB.

Consume la API local en 127.0.0.1:6900 y muestra los datos en el navegador.
No usa servicios en la nube, no requiere login.

Uso:
    .\\run-openbb-app.ps1

Queda en http://127.0.0.1:8501
"""

from __future__ import annotations

import json
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent
API = "http://127.0.0.1:6900"
PB = 10_000  # 1 punto porcentual = 100 puntos básicos

st.set_page_config(
    page_title="OpenBB local",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)


# --------------------------------------------------------------------------
# Acceso a la API
# --------------------------------------------------------------------------
@st.cache_data(ttl=300, show_spinner=False)
def _get(path: str, **params) -> dict:
    url = f"{API}{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url, timeout=120) as r:
        return json.loads(r.read())


@st.cache_data(ttl=30, show_spinner=False)
def api_viva() -> bool:
    try:
        _get("/api/v1/cftc/cot_search")
        return True
    except Exception:
        return False


def serie(path: str, fecha: str = "date", **params) -> pd.DataFrame:
    data = _get(path, **params)
    df = pd.DataFrame(data.get("results", []))
    if df.empty:
        return df
    if fecha in df.columns:
        df[fecha] = pd.to_datetime(df[fecha])
        df = df.sort_values(fecha)
    return df


def recortar(df: pd.DataFrame, fecha: str = "date") -> pd.DataFrame:
    if df.empty or DIAS == 0 or fecha not in df.columns:
        return df
    corte = pd.Timestamp.now() - pd.Timedelta(days=DIAS)
    return df[df[fecha] >= corte]


def ultimo(df: pd.DataFrame, col: str) -> float | None:
    if df.empty or col not in df.columns:
        return None
    s = pd.to_numeric(df[col], errors="coerce").dropna()
    return float(s.iloc[-1]) if len(s) else None


# --------------------------------------------------------------------------
# Traducción de columnas
# --------------------------------------------------------------------------
MAPA_EFFR = {
    "date": "Fecha",
    "rate": "Tasa efectiva",
    "target_range_upper": "Techo del rango",
    "target_range_lower": "Piso del rango",
    "volume": "Volumen",
}

MAPA_TASAS = {
    "date": "Fecha",
    "year_2": "2 años",
    "year_5": "5 años",
    "year_10": "10 años",
    "year_30": "30 años",
}

MAPA_COT = {
    "report_date": "Fecha",
    "large_specs_net": "Neto especulativo",
    "large_specs_net_pct_oi": "% del interés abierto",
    "open_interest": "Interés abierto",
}

MAPA_CTX = {
    "yield_2y": "Bono 2a (%)",
    "yield_10y": "Bono 10a (%)",
    "slope_10y_2y": "Pendiente 10a-2a (%)",
    "fed_funds": "Fed funds (%)",
    "vix": "VIX",
    "spx": "S&P 500",
    "eurusd": "EUR/USD",
    "cpi_yoy": "Inflación interanual (%)",
    "gdp_yoy": "PIB interanual (%)",
    "cot_net": "COT neto (miles)",
    "ff_mkt_rf": "Factor mercado (%)",
    "ff_smb": "Factor tamaño (%)",
    "ff_hml": "Factor valor (%)",
    "funding_btc_anual": "Funding BTC (% anual)",
}


def tabla(df: pd.DataFrame, mapa: dict, columnas: list[str] | None = None,
          escala: list[str] | None = None) -> pd.DataFrame:
    """Selecciona, traduce y (opcionalmente) escala columnas para mostrar."""
    cols = [c for c in (columnas or list(mapa)) if c in df.columns]
    out = df[cols].rename(columns=mapa).copy()
    for c in escala or []:
        if c in out.columns:
            out[c] = pd.to_numeric(out[c], errors="coerce") * 100
    if "Fecha" in out.columns:
        out["Fecha"] = pd.to_datetime(out["Fecha"]).dt.strftime("%Y-%m-%d")
    return out


# --------------------------------------------------------------------------
# Lectura del régimen
# --------------------------------------------------------------------------
def regimen(vix: float | None, pendiente_pb: float | None,
            cpi: float | None) -> dict | None:
    if vix is None and pendiente_pb is None and cpi is None:
        return None

    detalles: list[str] = []
    nivel = 0

    if vix is not None:
        if vix < 15:
            detalles.append(f"**VIX {vix:.1f}** — calma; el mercado no descuenta estrés.")
        elif vix < 20:
            detalles.append(f"**VIX {vix:.1f}** — volatilidad normal.")
            nivel += 1
        elif vix < 25:
            detalles.append(f"**VIX {vix:.1f}** — tensión; suben los movimientos bruscos.")
            nivel += 2
        else:
            detalles.append(f"**VIX {vix:.1f}** — estrés alto; riesgo de caídas rápidas.")
            nivel += 3

    if pendiente_pb is not None:
        if pendiente_pb < 0:
            detalles.append(
                f"**Curva {pendiente_pb:+.0f} pb** — invertida; históricamente "
                "anticipa desaceleración en 6-18 meses."
            )
            nivel += 3
        elif pendiente_pb < 50:
            detalles.append(
                f"**Curva {pendiente_pb:+.0f} pb** — plana; el mercado duda del crecimiento."
            )
            nivel += 1
        else:
            detalles.append(
                f"**Curva {pendiente_pb:+.0f} pb** — normal; el ciclo no muestra tensión."
            )

    if cpi is not None:
        if cpi > 4:
            detalles.append(f"**Inflación {cpi:.1f}%** — alta; presión para que los tipos sigan altos.")
            nivel += 2
        elif cpi > 2:
            detalles.append(f"**Inflación {cpi:.1f}%** — moderada.")
            nivel += 1
        else:
            detalles.append(f"**Inflación {cpi:.1f}%** — baja.")

    if nivel >= 5:
        veredicto = "defensivo"
    elif nivel >= 2:
        veredicto = "neutral"
    else:
        veredicto = "favorable"

    return {"veredicto": veredicto, "detalles": detalles, "nivel": nivel}


# --------------------------------------------------------------------------
# Barra lateral
# --------------------------------------------------------------------------
with st.sidebar:
    st.title("📈 OpenBB local")
    viva = api_viva()
    if viva:
        st.success("API conectada", icon="🟢")
    else:
        st.error("API caída", icon="🔴")
        st.code(r".\run-openbb-api.ps1", language="powershell")

    DIAS = st.selectbox(
        "Rango de datos",
        options=[30, 90, 365, 1825, 0],
        index=2,
        format_func=lambda x: "Todo el histórico" if x == 0 else f"Últimos {x} días",
    )

    if st.button("🔄 Refrescar datos", width="stretch"):
        st.cache_data.clear()
        st.rerun()

    st.divider()
    st.caption(f"API: `{API}`")
    st.markdown("[Abrir documentación /docs](http://127.0.0.1:6900/docs)")
    st.caption(f"Actualizado: {datetime.now():%Y-%m-%d %H:%M}")


st.title("OpenBB local")
st.caption("Datos públicos normalizados · 100 % en tu equipo · sin nube ni login")

if not viva:
    st.warning(
        "La API no responde. Arranca el backend en otra ventana y pulsa Refrescar:\n\n"
        "```powershell\n.\\run-openbb-api.ps1\n```"
    )
    st.stop()


# --------------------------------------------------------------------------
# Pestañas
# --------------------------------------------------------------------------
tab_resumen, tab_guia, tab_tipos, tab_riesgo, tab_macro, tab_cot, tab_contexto, tab_api = st.tabs(
    [
        "Resumen",
        "Guía",
        "Tipos",
        "Riesgo",
        "Macro",
        "Posicionamiento",
        "Contexto Freqtrade",
        "API",
    ]
)

# --- Resumen ---------------------------------------------------------------
with tab_resumen:
    try:
        effr = serie("/api/v1/fixedincome/rate/effr", provider="federal_reserve")
        tasas = serie(
            "/api/v1/fixedincome/government/treasury_rates",
            provider="federal_reserve",
            start_date="2000-01-01",
        )
        vix = serie("/api/v1/index/price/historical", symbol="VIX", provider="cboe")
        eurusd = serie("/api/v1/currency/price/historical", symbol="EURUSD", provider="ecb")
        cpi = serie("/api/v1/economy/cpi", provider="oecd")

        t2 = ultimo(tasas, "year_2")
        t10 = ultimo(tasas, "year_10")
        pendiente_pb = (t10 - t2) * PB if t2 is not None and t10 is not None else None
        vix_hoy = ultimo(vix, "close")
        cpi_hoy = ultimo(cpi, "value")
        cpi_pct = cpi_hoy * 100 if cpi_hoy is not None else None

        c1, c2, c3, c4, c5, c6 = st.columns(6)
        c1.metric(
            "Fed funds",
            f"{ultimo(effr, 'rate') * 100:.2f}%" if ultimo(effr, "rate") else "—",
            help="Tasa efectiva de los fondos federales. Es el coste del dinero a corto plazo.",
        )
        c2.metric(
            "Bono 10 años",
            f"{t10 * 100:.2f}%" if t10 is not None else "—",
            help="Rentabilidad del Treasury a 10 años. Referencia global del coste del capital.",
        )
        c3.metric(
            "Pendiente 10a-2a",
            f"{pendiente_pb:+.0f} pb" if pendiente_pb is not None else "—",
            help="Diferencia entre el bono a 10 y a 2 años. Negativa = curva invertida.",
        )
        c4.metric(
            "VIX",
            f"{vix_hoy:.1f}" if vix_hoy is not None else "—",
            help="Volatilidad implícita del S&P 500. Mide el miedo del mercado.",
        )
        c5.metric(
            "EUR/USD",
            f"{ultimo(eurusd, 'close'):.4f}" if ultimo(eurusd, "close") else "—",
            help="Tipo de cambio euro-dólar. Afecta a importaciones, inflación y activos en USD.",
        )
        c6.metric(
            "Inflación interanual",
            f"{cpi_pct:.1f}%" if cpi_pct is not None else "—",
            help="Variación anual del IPC de EE. UU. Condiciona la política de la Fed.",
        )

        st.divider()

        r = regimen(vix_hoy, pendiente_pb, cpi_pct)
        if r:
            icono = {"favorable": "🟢", "neutral": "🟡", "defensivo": "🔴"}[r["veredicto"]]
            cuerpo = "\n".join(f"- {d}" for d in r["detalles"])
            texto = f"{icono} **Entorno {r['veredicto']}**\n\n{cuerpo}"
            if r["veredicto"] == "favorable":
                st.success(texto)
            elif r["veredicto"] == "neutral":
                st.warning(texto)
            else:
                st.error(texto)
            st.caption(
                "Lectura de contexto, no una señal de compra o venta. "
                "Sirve para decidir cuánto riesgo asumir, no cuándo entrar."
            )

        a, b = st.columns(2)
        with a:
            st.subheader("Tipos de la Fed")
            e = recortar(effr)
            if not e.empty:
                st.line_chart(e.set_index("date")["rate"] * 100, y_label="%")
        with b:
            st.subheader("VIX")
            v = recortar(vix)
            if not v.empty:
                st.line_chart(v.set_index("date")["close"], y_label="puntos")

        with st.expander("¿Qué significa cada número?"):
            st.markdown(
                """
- **Fed funds**: lo que cuesta pedir dinero a un día. Si sube, el dinero se encarece
  y los activos de riesgo suelen sufrir.
- **Bono 10 años**: la referencia para valorar acciones, hipotecas y deuda. Si sube
  con fuerza, las acciones caras (tecnología, crecimiento) suelen corregir.
- **Pendiente 10a-2a**: positiva = economía en expansión; negativa (invertida) =
  el mercado espera recortes porque ve venir una desaceleración.
- **VIX**: por debajo de 15 hay calma; entre 15 y 20, normalidad; por encima de 25,
  estrés; por encima de 30, pánico.
- **EUR/USD**: un dólar fuerte presiona materias primas y emergentes; un euro fuerte
  resta competitividad a las exportaciones europeas.
- **Inflación**: por encima del 3 % la Fed mantiene tipos altos; por debajo del 2 %
  tiene margen para recortar.
"""
            )

        with st.expander("Ver datos crudos de la tasa de la Fed"):
            st.dataframe(
                tabla(effr.tail(50), MAPA_EFFR, escala=["Tasa efectiva",
                      "Techo del rango", "Piso del rango"]),
                width="stretch",
                hide_index=True,
            )
    except Exception as e:  # noqa: BLE001
        st.error(f"No se pudo cargar el resumen: {e}")

# --- Guía ------------------------------------------------------------------
with tab_guia:
    st.subheader("Qué estás viendo y para qué sirve")
    st.markdown(
        """
Este panel no genera señales de compra ni de venta. Muestra el **entorno** en el que
opera tu estrategia técnica. La idea es sencilla: el mismo cruce de medias funciona
distinto con el VIX a 12 que con el VIX a 35.
"""
    )

    st.markdown(
        """
| Indicador | Qué mide | Cómo se lee | Uso en trading |
|---|---|---|---|
| **Fed funds** | Coste del dinero a un día | Sube = política restrictiva | Evitar apalancamiento cuando sube rápido |
| **Bono 10 años** | Coste del capital a largo plazo | Sube = descuentan más los beneficios futuros | Malo para crecimiento y cripto |
| **Pendiente 10a-2a** | Forma de la curva | Negativa = invertida | Señal de cautela a 6-18 meses |
| **VIX** | Miedo implícito del S&P 500 | <15 calma · 15-20 normal · >25 estrés | Reducir tamaño cuando supera 25 |
| **S&P 500** | Bolsa americana | Tendencia y máximos/mínimos | Referencia de riesgo global |
| **EUR/USD** | Fuerza relativa euro-dólar | Dólar fuerte = presión global | Afecta a activos cotizados en USD |
| **Inflación** | IPC interanual | >3 % = tipos altos más tiempo | Reduce el apetito por riesgo |
| **PIB** | Crecimiento real | Cae = desaceleración | Confirma el ciclo |
| **COT** | Posicionamiento especulativo | Extremos = posible agotamiento | Contrario solo en extremos |
| **Fama-French** | Factores mercado, tamaño, valor | Explican retornos por estilo | Diagnóstico, no señal |
| **Funding BTC** | Coste de estar largo en el perpetuo | Positivo = los largos pagan (euforia) · negativo = pánico | Termómetro de apalancamiento, no filtro |
"""
    )

    st.info(
        "**Cómo usarlo en la práctica:** míralo una vez al día, antes de operar. "
        "Si el entorno es defensivo, baja el tamaño de posición o no operes. "
        "Si es favorable, tu estrategia técnica tiene viento a favor. "
        "Nunca lo uses como gatillo de entrada."
    )

    st.warning(
        "**Lo que ya medimos:** este contexto, aplicado a un cruce EMA 20/50, no batió "
        "a la referencia de misma exposición en 0 de 7 pares (2021-2026). El funding se "
        "probó como filtro de entrada y tampoco pasa la puerta: evitar el funding alto "
        "resta 8 puntos de mediana; exigir funding positivo sube 2,1 puntos, pero sigue "
        "en 1 de 7. Sirve como termómetro, no como fuente de alfa."
    )

    st.subheader("Glosario rápido")
    st.markdown(
        """
- **Punto básico (pb)**: una centésima de punto porcentual. 100 pb = 1 %.
- **Curva invertida**: el bono a 2 años paga más que el de 10; suele preceder recesiones.
- **Régimen**: combinación de volatilidad, tipos e inflación que define el apetito por riesgo.
- **Exposición**: porcentaje del capital que está en el mercado.
- **Referencia de misma exposición**: comparar contra estar invertido el mismo tiempo, sin strategy.
"""
    )

# --- Tipos -----------------------------------------------------------------
with tab_tipos:
    try:
        tasas = serie(
            "/api/v1/fixedincome/government/treasury_rates",
            provider="federal_reserve",
            start_date="2000-01-01",
        )
        if tasas.empty:
            st.info("Sin datos de treasuries.")
        else:
            t = recortar(tasas)
            cols = [c for c in ["year_2", "year_5", "year_10", "year_30"] if c in t.columns]
            st.subheader("Curva de treasuries de EE. UU.")
            st.caption(
                "Cada línea es lo que paga el Gobierno por prestarse dinero a ese plazo. "
                "Cuando la curva se aplana o se invierte, el mercado anticipa menos crecimiento."
            )
            st.line_chart(t.set_index("date")[cols] * 100, y_label="%")

            if "year_2" in t.columns and "year_10" in t.columns:
                pend = (t["year_10"] - t["year_2"]) * PB
                pend.index = t["date"]
                st.subheader("Pendiente 10a − 2a")
                st.area_chart(pend, y_label="puntos básicos")
                st.caption("Por debajo de 0 la curva está invertida: señal clásica de cautela.")

            with st.expander("Ver tabla (traducida)"):
                st.dataframe(
                    tabla(
                        t.tail(60),
                        MAPA_TASAS,
                        escala=["2 años", "5 años", "10 años", "30 años"],
                    ),
                    width="stretch",
                    hide_index=True,
                )
    except Exception as e:  # noqa: BLE001
        st.error(f"No se pudieron cargar los tipos: {e}")

# --- Riesgo ----------------------------------------------------------------
with tab_riesgo:
    try:
        vix = recortar(serie("/api/v1/index/price/historical", symbol="VIX", provider="cboe"))
        spx = recortar(serie("/api/v1/index/price/historical", symbol="SPX", provider="cboe"))

        c1, c2, c3 = st.columns(3)
        c1.metric("VIX actual", f"{ultimo(vix, 'close'):.1f}" if ultimo(vix, "close") else "—")
        c2.metric("S&P 500", f"{ultimo(spx, 'close'):,.0f}" if ultimo(spx, "close") else "—")
        if not vix.empty and len(vix) > 30:
            cambio = (vix["close"].iloc[-1] / vix["close"].iloc[-30] - 1) * 100
            c3.metric("VIX vs hace 30 ruedas", f"{cambio:+.1f}%")

        st.caption(
            "El VIX mide cuánto paga el mercado por protegerse. Sube rápido cuando hay miedo "
            "y suele caer cuando la calma vuelve. El S&P 500 es la referencia de riesgo global."
        )

        a, b = st.columns(2)
        with a:
            st.subheader("VIX (miedo)")
            if not vix.empty:
                st.line_chart(vix.set_index("date")["close"], y_label="puntos")
        with b:
            st.subheader("S&P 500 (riesgo)")
            if not spx.empty:
                st.line_chart(spx.set_index("date")["close"], y_label="puntos")
    except Exception as e:  # noqa: BLE001
        st.error(f"No se pudo cargar el riesgo: {e}")

# --- Macro -----------------------------------------------------------------
with tab_macro:
    try:
        cpi = recortar(serie("/api/v1/economy/cpi", provider="oecd"))
        gdp = serie("/api/v1/economy/gdp/real", provider="oecd")

        st.caption(
            "Datos con retraso real de publicación (45 días). No sirven para operar el día, "
            "sirven para saber en qué parte del ciclo estás."
        )

        if not cpi.empty:
            cpi = cpi.copy()
            cpi["interanual"] = pd.to_numeric(cpi["value"], errors="coerce") * 100
            st.subheader("Inflación interanual (EE. UU.)")
            st.line_chart(cpi.set_index("date")["interanual"], y_label="%")

        if not gdp.empty:
            gdp = gdp.copy()
            gdp["interanual"] = pd.to_numeric(gdp["value"], errors="coerce").pct_change(4) * 100
            st.subheader("PIB real interanual")
            st.line_chart(
                gdp.dropna(subset=["interanual"]).set_index("date")["interanual"],
                y_label="%",
            )

        with st.expander("Ver tablas"):
            st.dataframe(cpi.tail(24), width="stretch", hide_index=True)
            st.dataframe(gdp.tail(12), width="stretch", hide_index=True)
    except Exception as e:  # noqa: BLE001
        st.error(f"No se pudo cargar el macro: {e}")

# --- Posicionamiento -------------------------------------------------------
with tab_cot:
    try:
        cot = recortar(
            serie("/api/v1/cftc/cot_positioning", fecha="report_date", provider="cftc"),
            fecha="report_date",
        )
        if cot.empty:
            st.info("Sin datos de COT.")
        else:
            st.subheader("Posicionamiento especulativo (COT)")
            st.caption(
                "Cuántos contratos netos tienen los fondos especulativos. Los extremos "
                "suelen marcar agotamiento de tendencia; el resto del tiempo no dice nada."
            )
            st.line_chart(
                cot.set_index("report_date")["large_specs_net"] / 1000,
                y_label="miles de contratos",
            )
            c1, c2 = st.columns(2)
            c1.metric(
                "Neto especulativo",
                f"{ultimo(cot, 'large_specs_net') / 1000:,.1f} mil contratos",
            )
            pct_oi = ultimo(cot, "large_specs_net_pct_oi")
            c2.metric("% del interés abierto", f"{pct_oi:.1f}%" if pct_oi else "—")
            with st.expander("Ver tabla (traducida)"):
                st.dataframe(
                    tabla(cot.tail(30), MAPA_COT),
                    width="stretch",
                    hide_index=True,
                )
    except Exception as e:  # noqa: BLE001
        st.error(f"No se pudo cargar el COT: {e}")

# --- Contexto Freqtrade ----------------------------------------------------
with tab_contexto:
    ruta = ROOT / "data" / "context" / "contexto_diario.parquet"
    if not ruta.exists():
        st.warning(
            "No hay contexto exportado. Genera el archivo con:\n\n"
            "```powershell\n.\\venvs\\openbb\\Scripts\\python.exe scripts\\puente_freqtrade.py --exportar\n```"
        )
    else:
        try:
            ctx = pd.read_parquet(ruta)
            ctx.index = pd.to_datetime(ctx.index)
            ctx = ctx.sort_index()

            edad = (datetime.now() - datetime.fromtimestamp(ruta.stat().st_mtime)).days
            if edad >= 2:
                st.warning(
                    f"El archivo tiene {edad} días sin reexportarse. Las últimas filas son "
                    "copia del último dato (forward fill). Para actualizarlo:\n\n"
                    "```powershell\n.\\venvs\\openbb\\Scripts\\python.exe scripts\\puente_freqtrade.py --exportar --forzar\n```"
                )

            if DIAS:
                ctx = ctx[ctx.index >= pd.Timestamp.now() - pd.Timedelta(days=DIAS)]

            st.caption(
                f"{len(ctx):,} filas · {len(ctx.columns)} columnas · "
                f"última fecha {ctx.index[-1]:%Y-%m-%d} · archivo con {edad} días"
            )
            st.info(
                "Estas son las columnas exactas que ve tu estrategia de Freqtrade. "
                "Van retrasadas a propósito (1 a 45 días) para no usar información del futuro."
            )

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("VIX", f"{ctx['vix'].iloc[-1]:.1f}")
            c2.metric("Curva 10a-2a", f"{ctx['slope_10y_2y'].iloc[-1] * PB:+.0f} pb")
            c3.metric("Inflación interanual", f"{ctx['cpi_yoy'].iloc[-1]:.1f}%")
            if "funding_btc_anual" in ctx.columns:
                c4.metric(
                    "Funding BTC",
                    f"{ctx['funding_btc_anual'].iloc[-1]:+.1f}% anual",
                    help="Lo que cuesta estar largo en el perpetuo. Positivo = los largos "
                         "pagan a los cortos (euforia); negativo = pánico.",
                )
            else:
                c4.metric("COT neto", f"{ctx['cot_net'].iloc[-1]:,.0f} mil")

            st.subheader("Series del contexto")
            traducido = ctx.rename(columns=MAPA_CTX)
            elegidas = st.multiselect(
                "Columnas",
                options=list(traducido.columns),
                default=["VIX", "Inflación interanual (%)", "Funding BTC (% anual)"],
            )
            if elegidas:
                st.line_chart(traducido[elegidas])
                st.caption("Ojo: las series tienen escalas distintas; compara forma, no nivel.")

            with st.expander("Ver tabla completa (traducida)"):
                st.dataframe(traducido.tail(120), width="stretch")
                st.download_button(
                    "Descargar CSV",
                    data=traducido.to_csv().encode("utf-8"),
                    file_name="contexto_diario.csv",
                    mime="text/csv",
                )
        except Exception as e:  # noqa: BLE001
            st.error(f"No se pudo leer el contexto: {e}")

# --- API -------------------------------------------------------------------
with tab_api:
    st.subheader("Endpoints que usa este panel")
    st.caption(
        "OpenBB nombra sus rutas en inglés; los datos y las etiquetas del panel están en español."
    )
    st.markdown(
        """
| Sección | Endpoint |
|---|---|
| Fed funds | `/api/v1/fixedincome/rate/effr?provider=federal_reserve` |
| Treasuries | `/api/v1/fixedincome/government/treasury_rates?provider=federal_reserve` |
| VIX / S&P | `/api/v1/index/price/historical?symbol=VIX&provider=cboe` |
| EUR/USD | `/api/v1/currency/price/historical?symbol=EURUSD&provider=ecb` |
| Inflación | `/api/v1/economy/cpi?provider=oecd` |
| PIB | `/api/v1/economy/gdp/real?provider=oecd` |
| COT | `/api/v1/cftc/cot_positioning?provider=cftc` |
"""
    )
    st.markdown("[Abrir Swagger completo](http://127.0.0.1:6900/docs)")

    try:
        spec = _get("/openapi.json")
        st.metric("Rutas disponibles", len(spec.get("paths", {})))
    except Exception as e:  # noqa: BLE001
        st.warning(f"No se pudo leer OpenAPI: {e}")

    try:
        with st.expander("Ver respuesta cruda de la tasa de la Fed"):
            st.json(_get("/api/v1/fixedincome/rate/effr", provider="federal_reserve"))
    except Exception as e:  # noqa: BLE001
        st.warning(f"No se pudo consultar la tasa: {e}")

st.divider()
st.caption(
    "OpenBB local · datos de proveedores públicos · nada sale de tu equipo "
    "salvo las consultas de datos"
)
