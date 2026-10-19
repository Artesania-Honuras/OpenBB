"""Panel visual 100% local para OpenBB.

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
st.caption("Datos públicos normalizados · 100% en tu equipo · sin nube ni login")

if not viva:
    st.warning(
        "La API no responde. Arranca el backend en otra ventana y pulsa Refrescar:\n\n"
        "```powershell\n.\\run-openbb-api.ps1\n```"
    )
    st.stop()


# --------------------------------------------------------------------------
# Pestañas
# --------------------------------------------------------------------------
tab_resumen, tab_tipos, tab_riesgo, tab_macro, tab_cot, tab_contexto, tab_api = st.tabs(
    ["Resumen", "Tipos", "Riesgo", "Macro", "Posicionamiento", "Contexto Freqtrade", "API"]
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
        gdp = serie("/api/v1/economy/gdp/real", provider="oecd")

        t2 = ultimo(tasas, "year_2")
        t10 = ultimo(tasas, "year_10")
        pendiente = (t10 - t2) * 100 if t2 is not None and t10 is not None else None

        c1, c2, c3, c4, c5, c6 = st.columns(6)
        c1.metric("Fed funds", f"{ultimo(effr, 'rate') * 100:.2f}%" if ultimo(effr, "rate") else "—")
        c2.metric("Treasury 10a", f"{t10 * 100:.2f}%" if t10 is not None else "—")
        c3.metric(
            "Pendiente 10a-2a",
            f"{pendiente:+.0f} pb" if pendiente is not None else "—",
            help="Positiva = curva normal; negativa = invertida",
        )
        c4.metric("VIX", f"{ultimo(vix, 'close'):.1f}" if ultimo(vix, "close") else "—")
        c5.metric("EUR/USD", f"{ultimo(eurusd, 'close'):.4f}" if ultimo(eurusd, "close") else "—")
        c6.metric("CPI interanual", f"{ultimo(cpi, 'value') * 100:.1f}%" if ultimo(cpi, "value") else "—")

        st.divider()
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

        with st.expander("Ver datos crudos"):
            st.dataframe(effr.tail(50), width="stretch")
    except Exception as e:  # noqa: BLE001
        st.error(f"No se pudo cargar el resumen: {e}")

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
            st.subheader("Curva de treasuries")
            st.line_chart(t.set_index("date")[cols] * 100, y_label="%")

            if "year_2" in t.columns and "year_10" in t.columns:
                pend = (t["year_10"] - t["year_2"]) * 100
                pend.index = t["date"]
                st.subheader("Pendiente 10a − 2a")
                st.area_chart(pend, y_label="puntos básicos")
                st.caption("Por debajo de 0 la curva está invertida.")

            with st.expander("Ver tabla"):
                st.dataframe(t.tail(60), width="stretch")
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

        a, b = st.columns(2)
        with a:
            st.subheader("VIX")
            if not vix.empty:
                st.line_chart(vix.set_index("date")["close"], y_label="puntos")
        with b:
            st.subheader("S&P 500")
            if not spx.empty:
                st.line_chart(spx.set_index("date")["close"], y_label="puntos")
    except Exception as e:  # noqa: BLE001
        st.error(f"No se pudo cargar el riesgo: {e}")

# --- Macro -----------------------------------------------------------------
with tab_macro:
    try:
        cpi = recortar(serie("/api/v1/economy/cpi", provider="oecd"))
        gdp = serie("/api/v1/economy/gdp/real", provider="oecd")

        if not cpi.empty:
            cpi = cpi.copy()
            cpi["interanual"] = pd.to_numeric(cpi["value"], errors="coerce") * 100
            st.subheader("Inflación interanual (EE. UU.)")
            st.line_chart(cpi.set_index("date")["interanual"], y_label="%")

        if not gdp.empty:
            gdp = gdp.copy()
            gdp["interanual"] = pd.to_numeric(gdp["value"], errors="coerce").pct_change(4) * 100
            st.subheader("PIB real interanual")
            st.line_chart(gdp.dropna(subset=["interanual"]).set_index("date")["interanual"], y_label="%")

        with st.expander("Ver tablas"):
            st.dataframe(cpi.tail(24), width="stretch")
            st.dataframe(gdp.tail(12), width="stretch")
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
            st.line_chart(
                cot.set_index("report_date")["large_specs_net"] / 1000,
                y_label="miles de contratos",
            )
            c1, c2 = st.columns(2)
            c1.metric("Neto especulativo", f"{ultimo(cot, 'large_specs_net') / 1000:,.1f} mil")
            c2.metric("% del interés abierto", f"{ultimo(cot, 'large_specs_net_pct_oi'):.1f}%" if ultimo(cot, "large_specs_net_pct_oi") else "—")
            with st.expander("Ver tabla"):
                st.dataframe(cot.tail(30), width="stretch")
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
            if DIAS:
                ctx = ctx[ctx.index >= pd.Timestamp.now() - pd.Timedelta(days=DIAS)]

            st.caption(f"{len(ctx):,} filas · {len(ctx.columns)} columnas · último {ctx.index[-1]:%Y-%m-%d}")

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("VIX", f"{ctx['vix'].iloc[-1]:.1f}")
            c2.metric("Curva 10a-2a", f"{ctx['slope_10y_2y'].iloc[-1] * 100:+.0f} pb")
            c3.metric("CPI interanual", f"{ctx['cpi_yoy'].iloc[-1]:.1f}%")
            c4.metric("COT neto", f"{ctx['cot_net'].iloc[-1]:,.0f} mil")

            st.subheader("Series del contexto")
            elegidas = st.multiselect(
                "Columnas",
                options=list(ctx.columns),
                default=["vix", "slope_10y_2y", "cpi_yoy"],
            )
            if elegidas:
                st.line_chart(ctx[elegidas])

            with st.expander("Ver tabla completa"):
                st.dataframe(ctx.tail(120), width="stretch")
                st.download_button(
                    "Descargar CSV",
                    data=ctx.to_csv().encode("utf-8"),
                    file_name="contexto_diario.csv",
                    mime="text/csv",
                )
        except Exception as e:  # noqa: BLE001
            st.error(f"No se pudo leer el contexto: {e}")

# --- API -------------------------------------------------------------------
with tab_api:
    st.subheader("Endpoints que usa este panel")
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
        n = len(spec.get("paths", {}))
        st.metric("Rutas disponibles", n)
    except Exception as e:  # noqa: BLE001
        st.warning(f"No se pudo leer OpenAPI: {e}")

    try:
        with st.expander("Ver respuesta cruda de effr"):
            st.json(_get("/api/v1/fixedincome/rate/effr", provider="federal_reserve"))
    except Exception as e:  # noqa: BLE001
        st.warning(f"No se pudo consultar effr: {e}")

st.divider()
st.caption("OpenBB local · datos de proveedores públicos · nada sale de tu equipo salvo las consultas de datos")
