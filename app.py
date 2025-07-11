import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# ETFs avec type
ETFS = {
    'Lyxor MSCI World (WLD.PA)': {'ticker': 'WLD.PA', 'type': 'capitalisant'},
    'iShares Core MSCI World (IWDA.AS)': {'ticker': 'IWDA.AS', 'type': 'capitalisant'},
    'Amundi MSCI World (CW8.PA)': {'ticker': 'CW8.PA', 'type': 'capitalisant'},
    'iShares MSCI World Dist (IWRD.L)': {'ticker': 'IWRD.L', 'type': 'distribuant'},
    'SPDR MSCI World Dist (SWRD.L)': {'ticker': 'SWRD.L', 'type': 'distribuant'},
}

def simulate_dca(ticker, montant_mensuel, duree_annees, taux_impot=30):
    start_date = pd.Timestamp.today() - pd.DateOffset(years=duree_annees)
    etf = yf.Ticker(ticker)
    df = etf.history(start=start_date)
    if df.empty:
        return None
    # On prend la dernière clôture de chaque mois
    df = df.resample('M').last()[['Close', 'Dividends']].fillna(0)
    
    parts_achetees = montant_mensuel / df['Close']
    parts_cumulees = parts_achetees.cumsum()
    valeur_portefeuille = parts_cumulees * df['Close']
    
    div_brut = (parts_cumulees.shift(1).fillna(0) * df['Dividends']).sum()
    div_net = div_brut * (1 - taux_impot / 100)
    valeur_finale = valeur_portefeuille.iloc[-1] + div_net
    
    total_investi = montant_mensuel * 12 * duree_annees
    rendement_net_annuel = (valeur_finale / total_investi) ** (1/duree_annees) - 1
    
    return {
        "valeur_finale": valeur_finale,
        "div_brut": div_brut,
        "div_net": div_net,
        "rendement_net_annuel": rendement_net_annuel,
        "dates": valeur_portefeuille.index,
        "valeurs": valeur_portefeuille.values
    }

st.title("Simulateur ETF DCA")

# UI : Multi-select avec infos types
selection = st.multiselect(
    "Sélectionnez les ETFs à comparer",
    options=list(ETFS.keys()),
    default=['Lyxor MSCI World (WLD.PA)', 'iShares MSCI World Dist (IWRD.L)']
)

montant = st.number_input("Montant investi chaque mois (€)", min_value=10, value=100)
duree = st.slider("Durée de l'investissement (années)", min_value=1, max_value=30, value=10)
impot = st.slider("Taux d'imposition sur dividendes (%)", min_value=0, max_value=50, value=30)

if st.button("Lancer la simulation"):

    if not selection:
        st.warning("Veuillez sélectionner au moins un ETF.")
    else:
        resultats = {}
        fig = go.Figure()

        for etf_nom in selection:
            info = ETFS[etf_nom]
            sim = simulate_dca(info['ticker'], montant, duree, impot)

            if sim is None:
                st.error(f"Pas de données pour {etf_nom}")
                continue

            # Sauvegarder résultats
            resultats[etf_nom] = sim

            # Trace graphique
            fig.add_trace(go.Scatter(
                x=sim["dates"],
                y=sim["valeurs"],
                mode='lines',
                name=f"{etf_nom} ({info['type']})"
            ))

        fig.update_layout(
            title=f"Évolution portefeuille sur {duree} ans",
            xaxis_title="Date",
            yaxis_title="Valeur du portefeuille (€)",
            template="plotly_white"
        )
        st.plotly_chart(fig, use_container_width=True)

        # Résumé des résultats
        rows = []
        for etf_nom, sim in resultats.items():
            rows.append({
                "ETF": etf_nom,
                "Type": ETFS[etf_nom]['type'],
                "Valeur finale (€)": round(sim["valeur_finale"], 2),
                "Dividendes bruts (€)": round(sim["div_brut"], 2),
                "Dividendes nets (€)": round(sim["div_net"], 2),
                "Rendement net annuel (%)": round(sim["rendement_net_annuel"] * 100, 2),
            })

        df_res = pd.DataFrame(rows)
        st.dataframe(df_res.style.format({
            "Valeur finale (€)": "{:,.2f}",
            "Dividendes bruts (€)": "{:,.2f}",
            "Dividendes nets (€)": "{:,.2f}",
            "Rendement net annuel (%)": "{:.2f} %"
        }))
