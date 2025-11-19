import streamlit as st
import pandas as pd
import os

# Importa as funções de validação
from validador_de_parceiro import validar_parceiros
from validador_de_produto import validar_produtos
from validador_de_estoque import validar_estoque

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="Validador ERP",
    page_icon="favicon.png",
    layout="wide"
)

# --- CONSTANTES ---
TEMP_PARCEIRO = "temp_parceiros.csv"
TEMP_PRODUTO = "temp_produtos.csv"
TEMP_ESTOQUE = "temp_estoque.csv"
TEMP_MESTRE_PRODUTO = "mestre_produtos.csv"

# --- GERENCIAMENTO DE ESTADO ---
if 'pagina_atual' not in st.session_state:
    st.session_state['pagina_atual'] = 'home'

def set_pagina(nome_pagina):
    st.session_state['pagina_atual'] = nome_pagina

# --- FUNÇÃO DE RELATÓRIO (REMOVIDO OS BALÕES) ---
def exibir_relatorio_erros(erros, df_corrigido): 
    
    # 1. TRATAMENTO DE ERRO CRÍTICO (Quando o DF corrigido é None)
    if erros is None or df_corrigido is None:
        st.error("❌ A validação falhou e não pôde ser concluída. Motivo: Coluna obrigatória faltando, erro na leitura ou arquivo corrompido.")
        
        if erros is not None and isinstance(erros, list):
             df_erros = pd.DataFrame(erros)
             st.subheader("Detalhes do Erro Crítico:")
             st.dataframe(df_erros, use_container_width=True, hide_index=True)
        return

    # 2. Caso de Sucesso
    elif not erros:
        st.success("✅ SUCESSO! Nenhum erro encontrado. Planilha pronta para importação.")
        # Linha st.balloons() removida
        
    # 3. Caso de Erros Encontrados (e o DF está OK para download)
    else:
        st.error(f"❌ Foram encontrados {len(erros)} erros.") 
        
        # 1. Botões de Download (Em duas colunas)
        col_err, col_corr = st.columns(2)
        
        # Botão 1: Relatório de Erros
        with col_err:
            df_erros = pd.DataFrame(erros)
            csv_erros = df_erros.to_csv(index=False, sep=';', encoding='utf-8')
            st.download_button(
                label="⬇️ BAIXAR RELATÓRIO DE ERROS",
                data=csv_erros,
                file_name='relatorio_erros_validacao.csv',
                mime='text/csv',
                type="secondary"
            )
        
        # Botão 2: Planilha Corrigida
        with col_corr:
            csv_corrigido = df_corrigido.to_csv(index=False, sep=';', encoding='utf-8')
            st.download_button(
                label="⬇️ BAIXAR PLANILHA CORRIGIDA",
                data=csv_corrigido,
                file_name='planilha_corrigida_com_erros.csv',
                mime='text/csv',
                type="primary"
            )

        # 2. Exibe a tabela de erros
        df_erros = pd.DataFrame(erros)
        st.dataframe(
            df_erros, 
            use_container_width=True,
            hide_index=True,
            column_config={
                "linha": st.column_config.NumberColumn("Linha", format="%d"),
                "coluna": "Nome da Coluna",
                "valor_encontrado": "Valor Inválido",
                "erro": "Descrição do Erro"
            }
        )

# --- CABEÇALHO E LOGO ---
col_logo, col_center, col_right_spacer = st.columns([1, 4, 1])

with col_logo:
    try:
        st.image("logo.png", width=250)
    except:
        st.warning("Logo não encontrada")

with col_center:
    st.markdown("<h1 style='text-align: center; font-size: 32px; padding-top: 20px;'>Agente Validador de ERP</h1>", unsafe_allow_html=True)
    st.markdown("<h5 style='text-align: center; margin-top: 10px;'>Selecione abaixo qual tipo de planilha você deseja validar</h5>", unsafe_allow_html=True)

st.divider() 

# --- BOTÕES DE NAVEGAÇÃO ---
col1, col2, col3 = st.columns(3)

with col1:
    if st.button("👥 Validar Parceiros", use_container_width=True):
        set_pagina('parceiros')

with col2:
    if st.button("📦 Validar Produtos", use_container_width=True):
        set_pagina('produtos')

with col3:
    if st.button("🏭 Validar Estoque", use_container_width=True):
        set_pagina('estoque')

st.divider()

# --- CONTEÚDO DINÂMICO ---

# 1. Tela Inicial (HOME)
if st.session_state['pagina_atual'] == 'home':
    st.info("💡 **Novidade:** O sistema agora corrige automaticamente erros simples como formatação, espaços extras, e padronização de campos!")

# 2. Tela Parceiros
elif st.session_state['pagina_atual'] == 'parceiros':
    st.header("Validação de Parceiros")
    st.subheader("Faça o upload do arquivo `parceiros.csv` abaixo:")
    arquivo_upado = st.file_uploader(" ", type=["csv"], key="uploader_parceiros")
    
    if arquivo_upado and st.button("Iniciar Validação", type="secondary", key="btn_parceiros"):
        with open(TEMP_PARCEIRO, "wb") as f:
            f.write(arquivo_upado.getbuffer())
        
        with st.spinner("Analisando regras de negócio e aplicando correções..."):
            erros, df_corrigido = validar_parceiros(TEMP_PARCEIRO)
        
        exibir_relatorio_erros(erros, df_corrigido, "parceiros_corrigido.csv")
        if os.path.exists(TEMP_PARCEIRO): os.remove(TEMP_PARCEIRO)

# 3. Tela Produtos
elif st.session_state['pagina_atual'] == 'produtos':
    st.header("Validação de Produtos")
    st.subheader("Faça o upload do arquivo `produtos.csv` abaixo:")
    arquivo_upado = st.file_uploader(" ", type=["csv"], key="uploader_produtos")
    
    if arquivo_upado and st.button("Iniciar Validação", type="secondary", key="btn_produtos"):
        with open(TEMP_PRODUTO, "wb") as f:
            f.write(arquivo_upado.getbuffer())
            
        with st.spinner("Analisando NCMs, unidades, regras e corrigindo..."):
            erros, df_corrigido = validar_produtos(TEMP_PRODUTO)
            
        exibir_relatorio_erros(erros, df_corrigido, "produtos_corrigido.csv")
        if os.path.exists(TEMP_PRODUTO): os.remove(TEMP_PRODUTO)

# 4. Tela Estoque
elif st.session_state['pagina_atual'] == 'estoque':
    st.header("Validação de Estoque")
    st.warning("⚠️ Atenção: Necessário arquivo Mestre de Produtos exportado do ERP.")
    
    col_a, col_b = st.columns(2)
    with col_a:
        st.subheader("1. Planilha de Estoque (`estoque.csv`)")
        arquivo_estoque = st.file_uploader(" ", type=["csv"], key="uploader_estoque")
    with col_b:
        st.subheader("2. Mestre de Produtos (`mestre_produtos.csv`)")
        arquivo_mestre = st.file_uploader(" ", type=["csv"], key="uploader_mestre_prod")

    if arquivo_estoque and arquivo_mestre and st.button("Iniciar Validação Cruzada", type="secondary", key="btn_estoque"):
        with open(TEMP_ESTOQUE, "wb") as f: f.write(arquivo_estoque.getbuffer())
        with open(TEMP_MESTRE_PRODUTO, "wb") as f: f.write(arquivo_mestre.getbuffer())
        
        with st.spinner("Cruzando dados com o mestre e corrigindo..."):
            erros, df_corrigido = validar_estoque(TEMP_ESTOQUE)
            
        exibir_relatorio_erros(erros, df_corrigido, "estoque_corrigido.csv")
        
        if os.path.exists(TEMP_ESTOQUE): os.remove(TEMP_ESTOQUE)
        if os.path.exists(TEMP_MESTRE_PRODUTO): os.remove(TEMP_MESTRE_PRODUTO)