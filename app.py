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

    # Huella de la version que estas viendo. Si esta hora no coincide con la
    # ultima modificacion de `app.py`, la pestaña esta mostrando una copia
    # vieja: cerrada y abierta de nuevo. Sin esto no hay forma de saberlo.
    _version = datetime.fromtimestamp((ROOT / "app.py").stat().st_mtime)
    _informes = len(list((ROOT / "data").glob("reporte_*.txt")))
    st.caption(f"Versión del panel: **{_version:%Y-%m-%d %H:%M}** · {_informes} reportes")


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
tab_resumen, tab_guia, tab_tipos, tab_riesgo, tab_macro, tab_cot, tab_contexto, tab_estrategia, tab_api = st.tabs(
    [
        "Resumen",
        "Guía",
        "Tipos",
        "Riesgo",
        "Macro",
        "Posicionamiento",
        "Contexto Freqtrade",
        "Estrategia",
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

        # --- capa rapida: termometro de apalancamiento (fuente externa) --------
        st.divider()
        st.subheader("Capa rápida: apalancamiento en cripto")
        try:
            ruta_ctx = ROOT / "data" / "context" / "contexto_diario.parquet"
            ctx_f = pd.read_parquet(ruta_ctx) if ruta_ctx.exists() else pd.DataFrame()
            if "funding_btc_anual" in ctx_f.columns:
                s_fnd = pd.to_numeric(ctx_f["funding_btc_anual"], errors="coerce").dropna()
                s_fnd.index = pd.to_datetime(s_fnd.index)
                fnd = float(s_fnd.iloc[-1])
                ventana = s_fnd.tail(365)
                p85 = float(ventana.quantile(0.85))
                p15 = float(ventana.quantile(0.15))
                if fnd > p85:
                    etiqueta_f, ayuda_f = "euforia", "Los largos pagan caro por apalancarse."
                elif fnd < p15:
                    etiqueta_f, ayuda_f = "pánico", "Los largos cobran por estar largos."
                else:
                    etiqueta_f, ayuda_f = "normal", "Apalancamiento en su rango habitual."

                cm, cc = st.columns([1, 2])
                with cm:
                    st.metric(
                        "Funding BTC",
                        f"{fnd:+.1f}% anual",
                        help="Lo que cuesta estar largo en el perpetuo de BTC, en % anual. "
                             "Positivo = los largos pagan a los cortos. Es el termómetro "
                             "del apalancamiento, no una señal.",
                    )
                    st.caption(f"{etiqueta_f.capitalize()} · {ayuda_f}")
                with cc:
                    st.line_chart(s_fnd.tail(180), y_label="% anual", height=180)

                st.caption(
                    f"Percentiles de 1 año: p15 {p15:+.1f}% · p85 {p85:+.1f}%. "
                    "**Ojo:** medido en `E-08`, este dato **no** sirve como filtro de "
                    "entrada (0/7 y 1/7 baten la referencia). Infórmate, no operes con él."
                )
            else:
                st.info(
                    "El contexto no tiene la columna de funding. Regenéralo con:\n\n"
                    "```powershell\n.\\venvs\\openbb\\Scripts\\python.exe scripts\\puente_freqtrade.py --exportar\n```"
                )
        except Exception as e:  # noqa: BLE001
            st.error(f"No se pudo leer la capa rápida: {e}")

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

# --- Estrategia ------------------------------------------------------------
with tab_estrategia:
    st.subheader("Qué se ha probado y qué dijeron los números")
    st.caption(
        "Los números de abajo salen de los archivos crudos que escriben los validadores. "
        "Esta pestaña no recalcula nada por su cuenta: si un número no está en un archivo, "
        "no está aquí."
    )

    st.markdown("#### La puerta de graduación")
    st.caption(
        "Una estrategia solo se instala en los bots de Freqtrade si cumple las cuatro "
        "condiciones a la vez. Hoy no cumple ninguna, y la última candidata cayó antes "
        "de llegar al riesgo."
    )
    puerta = pd.DataFrame([
        {
            "Criterio": "≥ 2/3 de los activos baten su referencia de misma exposición",
            "Medido": "1/7 en E-07 · 0/7 en E-08 y E-09 · rotación: no aplica",
            "Estado": "❌",
        },
        {
            "Criterio": "Bate la referencia (no solo ser positivo)",
            "Medido": "Rotación +95,8 % vs cesta +370,3 % · Calmar 1,09 vs 4,52",
            "Estado": "❌ E-16",
        },
        {
            "Criterio": "Monte Carlo: P(pérdida) < 25 % y DD p95 < 20 %",
            "Medido": "DD rotación −87,9 % · walk-forward DD mediano −92,1 % (peor −97,4 %)",
            "Estado": "❌",
        },
        {
            "Criterio": "Supervivencia en ≥ 60 % de las ventanas walk-forward",
            "Medido": "5/11 calendario real · 6/11 mediana del walk-forward (era 7/11 en la fase 0)",
            "Estado": "❌ E-16",
        },
        {
            "Criterio": "Sobrevive a las 42 fases del rebalanceo",
            "Medido": "18/42 baten la cesta con 24 pares · 1/42 con 7 pares (y esa es la fase 0)",
            "Estado": "❌ E-17",
        },
    ])
    st.dataframe(puerta, hide_index=True, width="stretch")

    st.markdown("#### La prueba que la tumbó: la fase del rebalanceo")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("42 fases posibles", "40× de rango", help="De +95,8 % a +3.776 %, mismo motor y mismos datos.")
    c2.metric("Rotación (lunes)", "+95,8 %", delta="−274,5 pts vs cesta", delta_color="inverse")
    c3.metric("Cesta sin rotar", "+370,3 %", help="Los 24 pares a peso igual, sin decisiones.")
    c4.metric("P(azar ≥ rotación)", "24,0 %", delta="no significativo", delta_color="off")
    st.caption(
        "«Semanal» no dice **cuándo**. El validador rebalanceaba cada 7 días desde una fase "
        "arbitraria: con el lunes 00:00 —el calendario natural— la rotación cae en el "
        "**mínimo** de las 42 fases. Elegir el miércoles porque da +3.776 % sería "
        "data snooping sobre 42 variantes. El número honesto es el de la implementación "
        "elegida a priori, y ese número pierde contra no hacer nada."
    )

    st.markdown("#### Y no era solo la regla fija: el walk-forward entero (E-17)")
    st.caption(
        "Repetido el walk-forward completo en las 42 fases, en los dos universos. "
        "Lo que se publicó era la fase 0."
    )
    e1, e2, e3, e4 = st.columns(4)
    e1.metric("24 pares · Calmar mediano", "3,56", delta="cesta 4,52", delta_color="inverse")
    e2.metric("24 pares · fases que baten la cesta", "18/42", delta="43 %", delta_color="off")
    e3.metric("7 pares · fases que baten la cesta", "1/42", delta="y es la fase 0", delta_color="off")
    e4.metric("7 pares · Calmar de la fase 0", "19,22", help="El máximo exacto de las 42 fases. Su mediana es 1,55.")
    st.caption(
        "En 7 pares, el resultado publicado (+1.538 %, Calmar 19,22) es el **máximo exacto** "
        "de 42 intentos y la única fase que bate a la cesta. En 24 pares, la fase 0 está "
        "pegada al máximo (36,45) y solo 18 de 42 fases superan a la cesta. La rama de "
        "momentum se cierra: no es un ajuste, es que no hay mecanismo."
    )

    st.markdown("#### Qué se instalaría")
    st.error(
        "**Nada.** La regla `E-14` (+820 %) no era una ventaja: era la mediana de 42 fases "
        "de un parámetro que nunca se declaró. La implementación natural da **+95,8 %**, "
        "**pierde contra la cesta** (+370,3 %) y **no se distingue del azar** (P = 24 %). "
        "El código está escrito y verificado (`C-33`), y **no se copia a Freqtrade**."
    )
    st.caption(
        "El sleeve del 10 % y su bootstrap (`E-15`) siguen siendo aritmética correcta, pero "
        "dimensionaban una regla que no supera la puerta. No se borran: se quedan como "
        "método para cuando exista algo que dimensionar."
    )

    ruta_dim = ROOT / "data" / "reporte_dimensionado.csv"
    if ruta_dim.exists():
        with st.expander("Ver el dimensionado que se había calculado (E-15, sin objeto)"):
            dim = pd.read_csv(ruta_dim)
            dim.columns = [
                "Sleeve %", "CAGR mediano %", "Caída típica %", "Caída 5 % peor %",
                "P(caída > 20 %) %", "P(año perdedor) %", "P(año < −25 %) %",
            ][: len(dim.columns)]
            st.dataframe(dim.round(1), hide_index=True, width="stretch")
            st.caption(
                "Bootstrap por bloques de 7 días, 1.000 caminos, sobre la curva de la regla "
                "refutada. Se conserva como referencia del método, no como recomendación."
            )

    st.markdown("#### Experimentos")
    experimentos = pd.DataFrame([
        {
            "ID": "E-07",
            "Qué se probó": "Cruce EMA 20/50 + contexto macro",
            "Resultado": "+8,2 % OOS mediano · 1/7 baten la referencia",
            "Veredicto": "❌ Sin ventaja",
        },
        {
            "ID": "E-08",
            "Qué se probó": "Funding de perpetuos como filtro de entrada",
            "Resultado": "Evitar el funding alto: −8 pts de mediana (0/7)",
            "Veredicto": "❌ Descartado",
        },
        {
            "ID": "E-09",
            "Qué se probó": "Gestión de salida con la entrada fija",
            "Resultado": "Stop móvil −4,6 · break-even −4,3 · media rápida −13,5 pts",
            "Veredicto": "❌ Descartado",
        },
        {
            "ID": "E-10",
            "Qué se probó": "Momentum transversal (rotación entre pares)",
            "Resultado": "+1.112 % · percentil 99 frente a elegir pares al azar · DD −81,7 %",
            "Veredicto": "⚠️ Ventaja sí, riesgo no",
        },
        {
            "ID": "E-11",
            "Qué se probó": "Control de riesgo: régimen, volatilidad objetivo, criterio",
            "Resultado": "Régimen y vol descartados; selección por Calmar adoptada (Calmar 19,2 vs 13,7)",
            "Veredicto": "⚠️ Parcial",
        },
        {
            "ID": "E-12",
            "Qué se probó": "Momentum absoluto: mantener solo los K que conserven su tendencia",
            "Resultado": "Baja el DD a −59/−76 % y hunde el Calmar (19,2 → 2,0/10,6/4,0)",
            "Veredicto": "❌ Descartado",
        },
        {
            "ID": "E-13",
            "Qué se probó": "Universo ampliado de 7 a 24 pares (velas verificadas)",
            "Resultado": "+3.118 % y Calmar 35,8 vs 19,2… pero el DD EMPEORA: −87,1 % vs −80,0 %",
            "Veredicto": "❌ Hipótesis refutada",
        },
        {
            "ID": "E-14",
            "Qué se probó": "Configuración fija, sin re-optimizar (lo que se instala)",
            "Resultado": "+820 % · Calmar 9,95 · 7/11 ventanas… con UNA fase del rebalanceo",
            "Veredicto": "❌ Refutado por E-16",
        },
        {
            "ID": "E-15",
            "Qué se probó": "Dimensionado: traducir la caída del sleeve a la cartera",
            "Resultado": "Sleeve 10 % → caída típica −13 %, 5 % peor −22 %, 1 año perdedor de cada 5",
            "Veredicto": "⚪ Sin objeto tras E-16",
        },
        {
            "ID": "E-16",
            "Qué se probó": "La fase del rebalanceo: 42 fases posibles, cesta y azar del mismo calendario",
            "Resultado": "Rango +95,8 % a +3.776 % · lunes (a priori) +95,8 % vs cesta +370,3 % · P(azar) 24 %",
            "Veredicto": "❌ No desplegable",
        },
        {
            "ID": "E-17",
            "Qué se probó": "La fase en TODA la cadena: walk-forward completo × 42 fases × 2 universos",
            "Resultado": "24 pares: mediana +342 %, Calmar 3,56 vs 4,52, 18/42 baten la cesta · 7 pares: 1/42",
            "Veredicto": "❌ Rama cerrada",
        },
    ])
    st.dataframe(experimentos, hide_index=True, width="stretch")
    st.caption(
        "Dos avisos que quedan por escrito: la volatilidad objetivo gana en las cuatro "
        "medidas con 24 pares y las perdía las cuatro con 7 (inestable, no se adopta), y "
        "con 24 pares la mediana del azar pasa a ser **negativa**, así que el percentil "
        "frente al azar deja de ser comparable entre universos."
    )

    st.markdown("#### Reportes crudos")
    st.caption(
        "Salida literal de los validadores, sin reinterpretar. Elige uno en la lista; "
        "se muestra tal cual, con su tamaño y su número de líneas."
    )

    def _leer_reporte(ruta):
        """Lee reportes en UTF-8, UTF-8 con BOM o UTF-16 (PowerShell antiguo)."""
        crudo = ruta.read_bytes()
        if crudo[:2] in (b"\xff\xfe", b"\xfe\xff"):
            return crudo.decode("utf-16"), "utf-16"
        if crudo[:3] == b"\xef\xbb\xbf":
            return crudo.decode("utf-8-sig"), "utf-8 con BOM"
        return crudo.decode("utf-8", errors="replace"), "utf-8"

    informes = sorted((ROOT / "data").glob("reporte_*.txt"))
    if not informes:
        st.info("Todavía no hay reportes en `data/`.")
    else:
        elegido = st.selectbox(
            "Reporte",
            [r.name for r in informes],
            label_visibility="collapsed",
        )
        ruta = next(r for r in informes if r.name == elegido)
        texto, codificacion = _leer_reporte(ruta)
        texto = texto.replace("\r\n", "\n").replace("\r", "\n")
        lineas = texto.splitlines()

        if codificacion != "utf-8":
            st.warning(
                f"Este archivo está en **{codificacion}** y se está leyendo igualmente, "
                "pero conviene normalizarlo: `python scripts\\normalizar_reportes.py`."
            )

        c1, c2, c3 = st.columns([3, 1, 1])
        c1.caption(f"**{ruta.name}** · {len(lineas)} líneas · {ruta.stat().st_size / 1024:.1f} KB")
        c2.download_button(
            "Descargar",
            texto,
            file_name=ruta.name,
            mime="text/plain",
            width="stretch",
        )
        c3.caption(f"codificación: {codificacion}")

        with st.container(height=520, border=True):
            st.code(texto, language="text")

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
