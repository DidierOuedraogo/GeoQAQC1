import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from io import StringIO
import base64

# Configuration de la page
st.set_page_config(
    page_title="GeoQAQC",
    page_icon="📊",
    layout="wide"
)

# Auteur et informations
st.sidebar.markdown("### GeoQAQC")
st.sidebar.markdown("*Contrôle Qualité des Analyses Chimiques des Roches*")
st.sidebar.markdown("---")
st.sidebar.markdown("**Auteur:** Didier Ouedraogo, P.Geo")
st.sidebar.markdown("**Version:** 1.0.0")

# Titre principal
st.title("GeoQAQC")
st.markdown("### Contrôle Qualité des Analyses Chimiques des Roches")

# Onglets
tabs = st.tabs(["Type de Contrôle", "Importation des Données", "Analyse"])

with tabs[0]:
    st.header("Choisir le Type de Carte de Contrôle")
    
    control_type = st.selectbox(
        "Type de contrôle:",
        ["Standards CRM", "Blancs", "Duplicatas (nuage de points et régression)"],
        key="control_type"
    )
    
    if control_type == "Standards CRM":
        col1, col2 = st.columns(2)
        
        with col1:
            reference_value = st.number_input(
                "Valeur de référence:",
                min_value=0.0,
                step=0.0001,
                format="%.4f",
                key="reference_value"
            )
            
            reference_stddev = st.number_input(
                "Écart-type de référence:",
                min_value=0.0,
                step=0.0001,
                format="%.4f",
                key="reference_stddev"
            )
        
        with col2:
            tolerance_type = st.radio(
                "Type de tolérance:",
                ["Pourcentage (%)", "Multiple de l'écart-type"],
                key="tolerance_type"
            )
            
            if tolerance_type == "Pourcentage (%)":
                tolerance_value = st.number_input(
                    "Tolérance (%):",
                    min_value=0.0,
                    max_value=100.0,
                    value=10.0,
                    step=0.1,
                    key="tolerance_percent"
                )
            else:
                tolerance_value = st.number_input(
                    "Multiple de l'écart-type:",
                    min_value=0.0,
                    value=2.0,
                    step=0.1,
                    key="tolerance_stddev"
                )

# Fonction pour calculer les limites pour les CRM
def calculate_crm_limits(reference_value, tolerance_type, tolerance_value, reference_stddev=None):
    if tolerance_type == "Pourcentage (%)":
        tolerance = tolerance_value / 100
        upper_limit = reference_value * (1 + tolerance)
        lower_limit = reference_value * (1 - tolerance)
    else:  # Multiple de l'écart-type
        if reference_stddev is None or reference_stddev == 0:
            st.error("L'écart-type de référence doit être défini et supérieur à zéro pour utiliser ce type de tolérance.")
            return None, None
        upper_limit = reference_value + (tolerance_value * reference_stddev)
        lower_limit = reference_value - (tolerance_value * reference_stddev)
    
    return lower_limit, upper_limit

# Dans le deuxième onglet - Importation des données
with tabs[1]:
    st.header("Importer les Données")
    
    import_method = st.radio(
        "Méthode d'importation:",
        ["Téléchargement de fichier", "Copier-coller des données"],
        key="import_method"
    )
    
    if import_method == "Téléchargement de fichier":
        uploaded_file = st.file_uploader("Choisir un fichier CSV", type=["csv", "txt"])
        
        if uploaded_file is not None:
            separator = st.selectbox(
                "Séparateur:",
                [",", ";", "Tab"],
                key="file_separator"
            )
            
            sep_dict = {",": ",", ";": ";", "Tab": "\t"}
            try:
                if separator == "Tab":
                    df = pd.read_csv(uploaded_file, sep="\t")
                else:
                    df = pd.read_csv(uploaded_file, sep=separator)
                
                st.session_state.data = df
                st.success(f"Fichier chargé avec succès! {len(df)} lignes et {len(df.columns)} colonnes.")
                st.write("Aperçu des données:")
                st.dataframe(df.head())
            except Exception as e:
                st.error(f"Erreur lors du chargement du fichier: {e}")
    else:
        pasted_data = st.text_area(
            "Collez vos données (format CSV ou tableau séparé par des tabulations):",
            height=200,
            key="pasted_data"
        )
        
        separator = st.selectbox(
            "Séparateur:",
            [",", ";", "Tab"],
            key="paste_separator"
        )
        
        if st.button("Traiter les données"):
            if pasted_data:
                sep_dict = {",": ",", ";": ";", "Tab": "\t"}
                try:
                    df = pd.read_csv(StringIO(pasted_data), sep=sep_dict[separator])
                    st.session_state.data = df
                    st.success(f"Données traitées avec succès! {len(df)} lignes et {len(df.columns)} colonnes.")
                    st.write("Aperçu des données:")
                    st.dataframe(df.head())
                except Exception as e:
                    st.error(f"Erreur lors du traitement des données: {e}")
            else:
                st.warning("Veuillez coller des données avant de les traiter.")

# Dans le troisième onglet - Analyse
with tabs[2]:
    st.header("Analyse des Données")
    
    if 'data' not in st.session_state:
        st.warning("Aucune donnée n'a été importée. Veuillez d'abord importer des données dans l'onglet 'Importation des Données'.")
    else:
        df = st.session_state.data
        control_type = st.session_state.control_type
        
        # Sélection des colonnes selon le type de contrôle
        if control_type == "Standards CRM":
            col1, col2 = st.columns(2)
            with col1:
                id_column = st.selectbox("Colonne ID/échantillon:", df.columns, key="crm_id_column")
            with col2:
                value_column = st.selectbox("Colonne des valeurs mesurées:", df.columns, key="crm_value_column")
                
            if st.button("Générer la Carte de Contrôle"):
                # Préparation des données
                data = df[[id_column, value_column]].copy()
                data = data.dropna()
                data[value_column] = pd.to_numeric(data[value_column], errors='coerce')
                data = data.dropna()
                
                if data.empty:
                    st.error("Aucune donnée numérique valide trouvée pour l'analyse.")
                else:
                    # Récupération des paramètres
                    reference_value = st.session_state.reference_value
                    tolerance_type = st.session_state.tolerance_type
                    
                    if tolerance_type == "Pourcentage (%)":
                        tolerance_value = st.session_state.tolerance_percent
                    else:
                        tolerance_value = st.session_state.tolerance_stddev
                        
                    reference_stddev = st.session_state.reference_stddev if 'reference_stddev' in st.session_state else 0
                    
                    # Calcul des limites
                    lower_limit, upper_limit = calculate_crm_limits(
                        reference_value,
                        tolerance_type,
                        tolerance_value,
                        reference_stddev
                    )
                    
                    if lower_limit is not None and upper_limit is not None:
                        # Statistiques
                        values = data[value_column].values
                        mean = np.mean(values)
                        std_dev = np.std(values)
                        min_val = np.min(values)
                        max_val = np.max(values)
                        
                        # Création du graphique avec Plotly
                        fig = go.Figure()
                        
                        # Données mesurées
                        fig.add_trace(go.Scatter(
                            x=data[id_column],
                            y=data[value_column],
                            mode='lines+markers',
                            name='Valeur mesurée',
                            line=dict(color='rgb(75, 192, 192)', width=2),
                            marker=dict(size=8)
                        ))
                        
                        # Valeur de référence
                        fig.add_trace(go.Scatter(
                            x=data[id_column],
                            y=[reference_value] * len(data),
                            mode='lines',
                            name='Valeur référence',
                            line=dict(color='rgb(54, 162, 235)', width=2, dash='dash')
                        ))
                        
                        # Limites
                        fig.add_trace(go.Scatter(
                            x=data[id_column],
                            y=[upper_limit] * len(data),
                            mode='lines',
                            name='Limite supérieure',
                            line=dict(color='rgb(255, 99, 132)', width=2, dash='dash')
                        ))
                        
                        fig.add_trace(go.Scatter(
                            x=data[id_column],
                            y=[lower_limit] * len(data),
                            mode='lines',
                            name='Limite inférieure',
                            line=dict(color='rgb(255, 99, 132)', width=2, dash='dash')
                        ))
                        
                        # Mise en forme
                        fig.update_layout(
                            title=f"GeoQAQC - Carte de Contrôle CRM - {value_column}",
                            xaxis_title=id_column,
                            yaxis_title=value_column,
                            height=600,
                            hovermode="closest"
                        )
                        
                        st.plotly_chart(fig, use_container_width=True)
                        
                        # Tableau des statistiques
                        st.subheader("Statistiques")
                        
                        stats_col1, stats_col2 = st.columns(2)
                        
                        with stats_col1:
                            st.markdown(f"**Valeur de référence:** {reference_value:.4f}")
                            
                            if reference_stddev > 0:
                                st.markdown(f"**Écart-type de référence:** {reference_stddev:.4f}")
                            
                            if tolerance_type == "Pourcentage (%)":
                                st.markdown(f"**Tolérance:** {tolerance_value:.2f}%")
                            else:
                                st.markdown(f"**Tolérance:** {tolerance_value:.1f} × écart-type")
                        
                        with stats_col2:
                            st.markdown(f"**Moyenne:** {mean:.4f}")
                            st.markdown(f"**Écart-type:** {std_dev:.4f}")
                            st.markdown(f"**Min:** {min_val:.4f}")
                            st.markdown(f"**Max:** {max_val:.4f}")
                        
                        # Tableau de données
                        st.subheader("Résultats détaillés")
                        
                        # Création d'un DataFrame avec les résultats
                        results_df = data.copy()
                        results_df['Écart (%)'] = ((results_df[value_column] - reference_value) / reference_value) * 100
                        
                        if reference_stddev > 0:
                            results_df['Z-score'] = (results_df[value_column] - reference_value) / reference_stddev
                        
                        results_df['Statut'] = results_df[value_column].apply(
                            lambda x: 'OK' if lower_limit <= x <= upper_limit else 'Hors limites'
                        )
                        
                        # Afficher le tableau avec coloration conditionnelle
                        st.dataframe(results_df.style.apply(
                            lambda x: ['background-color: #ffcccc' if v == 'Hors limites' else '' for v in x],
                            subset=['Statut']
                        ))
                        
                        # Bouton d'export
                        csv = results_df.to_csv(index=False)
                        b64 = base64.b64encode(csv.encode()).decode()
                        href = f'<a href="data:file/csv;base64,{b64}" download="geoqaqc_crm_results.csv">Télécharger les résultats (CSV)</a>'
                        st.markdown(href, unsafe_allow_html=True)
                        
        elif control_type == "Duplicatas (nuage de points et régression)":
            col1, col2 = st.columns(2)
            with col1:
                original_column = st.selectbox("Colonne des valeurs originales:", df.columns, key="duplicate_original_column")
            with col2:
                replicate_column = st.selectbox("Colonne des valeurs dupliquées:", df.columns, key="duplicate_replicate_column")
            
            if st.button("Générer la Carte de Contrôle"):
                # Préparation des données
                data = df[[original_column, replicate_column]].copy()
                data = data.dropna()
                data[original_column] = pd.to_numeric(data[original_column], errors='coerce')
                data[replicate_column] = pd.to_numeric(data[replicate_column], errors='coerce')
                data = data.dropna()
                
                if data.empty:
                    st.error("Aucune donnée numérique valide trouvée pour l'analyse.")
                else:
                    # Calcul de la régression linéaire
                    x = data[original_column].values
                    y = data[replicate_column].values
                    
                    slope, intercept = np.polyfit(x, y, 1)
                    r = np.corrcoef(x, y)[0, 1]
                    
                    # Calcul des statistiques
                    differences = np.abs(y - x)
                    mean_diff = np.mean(differences)
                    
                    relative_diff = np.abs(y - x) / ((x + y) / 2) * 100
                    mean_relative_diff = np.nanmean(relative_diff)
                    
                    # Création du graphique avec Plotly
                    fig = go.Figure()
                    
                    # Nuage de points
                    fig.add_trace(go.Scatter(
                        x=data[original_column],
                        y=data[replicate_column],
                        mode='markers',
                        name='Duplicatas',
                        marker=dict(
                            color='rgb(75, 192, 192)',
                            size=10,
                            opacity=0.8
                        )
                    ))
                    
                    # Ligne de régression
                    x_range = np.linspace(min(x), max(x), 100)
                    y_pred = slope * x_range + intercept
                    
                    fig.add_trace(go.Scatter(
                        x=x_range,
                        y=y_pred,
                        mode='lines',
                        name=f'Régression linéaire (y = {slope:.4f}x + {intercept:.4f})',
                        line=dict(color='rgb(255, 99, 132)', width=2)
                    ))
                    
                    # Ligne d'égalité parfaite (y = x)
                    fig.add_trace(go.Scatter(
                        x=x_range,
                        y=x_range,
                        mode='lines',
                        name='Ligne d\'égalité (y=x)',
                        line=dict(color='rgb(54, 162, 235)', width=2, dash='dash')
                    ))
                    
                    # Mise en forme
                    fig.update_layout(
                        title=f"GeoQAQC - Analyse des Duplicatas - {original_column} vs {replicate_column}",
                        xaxis_title=original_column,
                        yaxis_title=replicate_column,
                        height=600,
                        hovermode="closest"
                    )
                    
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # Tableau des statistiques
                    st.subheader("Statistiques")
                    
                    st.markdown(f"**Équation de régression:** y = {slope:.4f}x + {intercept:.4f}")
                    st.markdown(f"**Coefficient de corrélation (R²):** {r*r:.4f}")
                    st.markdown(f"**Différence absolue moyenne:** {mean_diff:.4f}")
                    st.markdown(f"**Différence relative moyenne:** {mean_relative_diff:.2f}%")
                    
                    # Tableau de données
                    st.subheader("Résultats détaillés")
                    
                    # Création d'un DataFrame avec les résultats
                    results_df = data.copy()
                    results_df['Diff. Abs.'] = np.abs(results_df[replicate_column] - results_df[original_column])
                    results_df['Diff. Rel. (%)'] = np.abs(results_df[replicate_column] - results_df[original_column]) / ((results_df[original_column] + results_df[replicate_column]) / 2) * 100
                    
                    st.dataframe(results_df)
                    
                    # Bouton d'export
                    csv = results_df.to_csv(index=False)
                    b64 = base64.b64encode(csv.encode()).decode()
                    href = f'<a href="data:file/csv;base64,{b64}" download="geoqaqc_duplicate_results.csv">Télécharger les résultats (CSV)</a>'
                    st.markdown(href, unsafe_allow_html=True)
                    
        elif control_type == "Blancs":
            col1, col2 = st.columns(2)
            with col1:
                id_column = st.selectbox("Colonne ID/échantillon:", df.columns, key="blank_id_column")
            with col2:
                value_column = st.selectbox("Colonne des valeurs mesurées:", df.columns, key="blank_value_column")
            
            if st.button("Générer la Carte de Contrôle"):
                # Préparation des données
                data = df[[id_column, value_column]].copy()
                data = data.dropna()
                data[value_column] = pd.to_numeric(data[value_column], errors='coerce')
                data = data.dropna()
                
                if data.empty:
                    st.error("Aucune donnée numérique valide trouvée pour l'analyse.")
                else:
                    # Calcul des statistiques
                    values = data[value_column].values
                    mean = np.mean(values)
                    std_dev = np.std(values)
                    min_val = np.min(values)
                    max_val = np.max(values)
                    
                    # Limites de détection estimées
                    lod = mean + 3 * std_dev
                    
                    # Création du graphique avec Plotly
                    fig = go.Figure()
                    
                    # Données mesurées
                    fig.add_trace(go.Scatter(
                        x=data[id_column],
                        y=data[value_column],
                        mode='lines+markers',
                        name='Valeur mesurée',
                        line=dict(color='rgb(75, 192, 192)', width=2),
                        marker=dict(size=8)
                    ))
                    
                    # Moyenne
                    fig.add_trace(go.Scatter(
                        x=data[id_column],
                        y=[mean] * len(data),
                        mode='lines',
                        name='Moyenne',
                        line=dict(color='rgb(54, 162, 235)', width=2, dash='dash')
                    ))
                    
                    # Limite de détection
                    fig.add_trace(go.Scatter(
                        x=data[id_column],
                        y=[lod] * len(data),
                        mode='lines',
                        name='Limite de détection (LOD)',
                        line=dict(color='rgb(255, 99, 132)', width=2, dash='dash')
                    ))
                    
                    # Mise en forme
                    fig.update_layout(
                        title=f"GeoQAQC - Carte de Contrôle Blancs - {value_column}",
                        xaxis_title=id_column,
                        yaxis_title=value_column,
                        height=600,
                        hovermode="closest"
                    )
                    
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # Tableau des statistiques
                    st.subheader("Statistiques")
                    
                    st.markdown(f"**Moyenne:** {mean:.4f}")
                    st.markdown(f"**Écart-type:** {std_dev:.4f}")
                    st.markdown(f"**Min:** {min_val:.4f}")
                    st.markdown(f"**Max:** {max_val:.4f}")
                    st.markdown(f"**Limite de détection estimée (LOD):** {lod:.4f}")
                    
                    # Tableau de données
                    st.subheader("Résultats détaillés")
                    
                    # Création d'un DataFrame avec les résultats
                    results_df = data.copy()
                    results_df['Statut'] = results_df[value_column].apply(
                        lambda x: 'OK' if x <= lod else 'Élevé'
                    )
                    
                    # Afficher le tableau avec coloration conditionnelle
                    st.dataframe(results_df.style.apply(
                        lambda x: ['background-color: #ffcccc' if v == 'Élevé' else '' for v in x],
                        subset=['Statut']
                    ))
                    
                    # Bouton d'export
                    csv = results_df.to_csv(index=False)
                    b64 = base64.b64encode(csv.encode()).decode()
                    href = f'<a href="data:file/csv;base64,{b64}" download="geoqaqc_blank_results.csv">Télécharger les résultats (CSV)</a>'
                    st.markdown(href, unsafe_allow_html=True)

# Footer
st.markdown("---")
st.markdown("**GeoQAQC** © 2025 - Développé par Didier Ouedraogo, P.Geo")