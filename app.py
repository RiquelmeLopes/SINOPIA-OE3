import streamlit as st
import pandas as pd
import plotly.express as px
import requests
import unidecode

# Configuração da página
st.set_page_config(page_title="Geração de Insumos", layout="wide")

# ==============================================================================
# FUNÇÕES DE CARREGAMENTO E PROCESSAMENTO (CACHED)
# ==============================================================================

@st.cache_data
def load_data(uploaded_file):
    """Carrega o CSV e faz o pré-processamento básico."""
    try:
        try:
            df = pd.read_csv(uploaded_file)
        except:
            uploaded_file.seek(0)
            df = pd.read_csv(uploaded_file, sep=';')

        # Mapeamento de colunas para garantir compatibilidade
        cols_map = {
            'created_at': 'data_criacao',
            'user_type': 'tipo_usuario',
            'current_institution_id': 'instituicao',
        }
        df.rename(columns=cols_map, inplace=True)

        # Tratamento de Datas
        if 'data_criacao' in df.columns:
            df["data_criacao"] = pd.to_datetime(df["data_criacao"], errors="coerce")
            df["ano_mes"] = df["data_criacao"].dt.to_period("M").astype(str)
        
        if 'deadline' in df.columns and 'data_criacao' in df.columns:
            df["deadline"] = pd.to_datetime(df["deadline"], errors="coerce")
            df["prazo_dias"] = (df["deadline"] - df["data_criacao"]).dt.days

        return df
    except Exception as e:
        st.error(f"Erro ao processar o arquivo: {e}")
        return None

@st.cache_data
def get_geojson_pe():
    """Baixa GeoJSON de PE."""
    url = "https://raw.githubusercontent.com/tbrugz/geodata-br/master/geojson/geojs-26-mun.json"
    return requests.get(url).json()

# ==============================================================================
# INTERFACE DO USUÁRIO
# ==============================================================================

st.title("📊 SINOPIA - Geração de Insumos")
st.markdown("---")

# 1. Upload
st.sidebar.header("Carregar Dados")
uploaded_file = st.file_uploader("Faça upload do CSV", type=["csv"])

if uploaded_file is not None:
    df = load_data(uploaded_file)
    
    if df is not None:
        st.success(f"Dados carregados: {df.shape[0]} linhas encontradas.")
        
        st.markdown("### Seleção de Visualizações")

        # 2. Lista de Opções
        opcoes_disponiveis = [
            "Quantidade de Atendimentos por Estado (Mensal)",
            "Prazo Médio por Município (Mensal)",
            "Quantidade de Atendimentos por Município (Mensal)",
            "Distribuição por Tipo de Usuário (Pizza)",
            "Top 10 Instituições",
            "Mapa de Calor - Pernambuco"
        ]

        # O usuário pode selecionar vários itens
        graficos_selecionados = st.multiselect(
            "Selecione quais gráficos você deseja gerar (digite para buscar):",
            options=opcoes_disponiveis,
            placeholder="Escolha um ou mais gráficos..."
        )

        # 3. Botão de Gerar
        if st.button("Gerar Insumos", type="primary"):
            
            if not graficos_selecionados:
                st.warning("Selecione pelo menos uma opção acima.")
            else:
                st.markdown("---")
                
                # Loop para gerar cada gráfico selecionado
                for grafico in graficos_selecionados:
                    
                    st.subheader(f"📌 {grafico}") # Título para cada seção
                    
                    # --- GRÁFICO 1 ---
                    if grafico == "Quantidade de Atendimentos por Estado (Mensal)":
                        if 'estado' in df.columns:
                            df_estado = df.groupby(["ano_mes", "estado"]).size().reset_index(name="qtd")
                            fig = px.bar(df_estado, x="ano_mes", y="qtd", color="estado", 
                                         text="qtd")
                            fig.update_traces(textposition="outside")
                            st.plotly_chart(fig, use_container_width=True)
                        else:
                            st.warning("Coluna 'estado' não encontrada.")

                    # --- GRÁFICO 2 ---
                    elif grafico == "Prazo Médio por Município (Mensal)":
                        if 'prazo_dias' in df.columns and 'municipio' in df.columns:
                            df_prazo = df.groupby(["ano_mes", "municipio"])["prazo_dias"].mean().reset_index()
                            fig = px.line(df_prazo, x="ano_mes", y="prazo_dias", color="municipio", markers=True)
                            st.plotly_chart(fig, use_container_width=True)
                        else:
                            st.warning("Colunas para cálculo de prazo ausentes.")

                    # --- GRÁFICO 3 ---
                    elif grafico == "Quantidade de Atendimentos por Município (Mensal)":
                        if 'municipio' in df.columns:
                            df_mun = df.groupby(["ano_mes", "municipio"]).size().reset_index(name="qtd")
                            fig = px.bar(df_mun, x="ano_mes", y="qtd", color="municipio", text="qtd")
                            fig.update_traces(textposition="outside")
                            st.plotly_chart(fig, use_container_width=True)
                        else:
                            st.warning("Coluna 'municipio' não encontrada.")

                    # --- GRÁFICO 4 ---
                    elif grafico == "Distribuição por Tipo de Usuário (Pizza)":
                        if 'tipo_usuario' in df.columns:
                            df_pie = df["tipo_usuario"].value_counts().reset_index()
                            df_pie.columns = ["tipo_usuario", "qtd"]
                            fig = px.pie(df_pie, names="tipo_usuario", values="qtd", hole=0.35)
                            st.plotly_chart(fig, use_container_width=True)
                        else:
                            st.warning("Coluna 'tipo_usuario' não encontrada.")

                    # --- GRÁFICO 5 ---
                    elif grafico == "Top 10 Instituições":
                        if 'instituicao' in df.columns:
                            df_top = df["instituicao"].value_counts().head(10).reset_index()
                            df_top.columns = ["instituicao", "qtd"]
                            fig = px.bar(df_top, x="qtd", y="instituicao", orientation="h", text="qtd")
                            fig.update_yaxes(categoryorder="total ascending")
                            fig.update_traces(textposition="outside")
                            st.plotly_chart(fig, use_container_width=True)
                        else:
                            st.warning("Coluna 'instituicao' não encontrada.")

                    # --- GRÁFICO 6 (MAPA) ---
                    elif grafico == "Mapa de Calor - Pernambuco":
                        if 'municipio' in df.columns:
                            # O mapa pode demorar um pouquinho, então colocamos um aviso visual
                            with st.spinner("Renderizando mapa..."):
                                df_mapa = df['municipio'].value_counts().reset_index()
                                df_mapa.columns = ['municipio', 'qtd']
                                
                                geojson_pe = get_geojson_pe()
                                
                                df_mapa['municipio_norm'] = df_mapa['municipio'].apply(
                                    lambda x: unidecode.unidecode(str(x).strip().upper())
                                )
                                
                                props = list(geojson_pe['features'][0]['properties'].keys())
                                nome_campo = 'name' if 'name' in props else props[0]

                                for feature in geojson_pe['features']:
                                    feature['properties']['NOME_NORM'] = unidecode.unidecode(
                                        str(feature['properties'][nome_campo]).strip().upper()
                                    )

                                fig = px.choropleth_mapbox(
                                    df_mapa,
                                    geojson=geojson_pe,
                                    locations='municipio_norm',
                                    featureidkey='properties.NOME_NORM',
                                    color='qtd',
                                    color_continuous_scale='YlOrRd',
                                    mapbox_style='carto-positron',
                                    zoom=6.2,
                                    center={'lat': -8.28, 'lon': -37.98},
                                    opacity=0.8
                                )
                                fig.update_geos(fitbounds="locations", visible=False)
                                fig.update_layout(margin={"r":0,"t":0,"l":0,"b":0})
                                
                                st.plotly_chart(fig, use_container_width=True)
                        else:
                            st.warning("Coluna 'municipio' necessária para o mapa.")
                    
                    # Adiciona uma linha divisória entre os gráficos
                    st.markdown("---")

else:
    st.info("Aguardando upload do arquivo CSV.")