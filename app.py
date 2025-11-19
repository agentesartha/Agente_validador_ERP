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
    page_icon="favicon.png", # Usa o arquivo favicon.png
    layout="wide"
)

# --- CONSTANTES ---
TEMP_PARCEIRO = "temp_parceiros.csv"
TEMP_PRODUTO = "temp_produtos.csv"
TEMP_ESTOQUE = "temp_estoque.csv"
TEMP_MESTRE_PRODUTO = "mestre_produtos.csv"

# --- GERENCIAMENTO DE ESTADO (MEMÓRIA DO CLICK) ---
if 'pagina_atual' not in st.session_state:
    st.session_state['pagina_atual'] = 'home'

def set_pagina(nome_pagina):
    st.session_state['pagina_atual'] = nome_pagina

# --- FUNÇÃO DE RELATÓRIO (COMPLETA COM OS DOIS BOTÕES) ---
# AGORA RECEBE 'erros' E 'df_corrigido'
def exibir_relatorio_erros(erros, df_corrigido):
    if erros is None:
        st.error("❌ A validação falhou e não pôde ser concluída. (Erro de Leitura Crítico)")
    elif not erros:
        st.success("✅ SUCESSO! Nenhum erro encontrado. Planilha pronta para importação.")
        st.balloons() 
        
        # 1. BOTÃO DOWNLOAD (CORRIGIDO) - Se não há erros, o botão principal é a planilha corrigida
        csv_corrigido = df_corrigido.to_csv(index=False, sep=';', encoding='utf-8')
        st.download_button(
            label="⬇️ BAIXAR PLANILHA CORRIGIDA (SEM ERROS)",
            data=csv_corrigido,
            file_name='planilha_corrigida_sem_erros.csv',
            mime='text/csv',
            type="primary"
        )
        
    else:
        # Se houver erros, exibe a tabela de erros E os dois botões

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
        
# --- Mude a Chamada da Validação (Bloco Parceiros) ---
# Você precisa mudar a chamada na função 'app.py' para desestruturar os dois resultados:

# No bloco 'elif st.session_state['pagina_atual'] == 'parceiros':', a chamada deve ser:
# ANTES: erros = validar_parceiros(TEMP_PARCEIRO)
# DEPOIS:
#
# resultados = validar_parceiros(TEMP_PARCEIRO)
# if resultados is None:
#     erros, df_corrigido = None, None
# else:
#     erros, df_corrigido = resultados # Recebe a lista de erros E o DF
#
# exibir_relatorio_erros(erros, df_corrigido)

# --- CABEÇALHO E LOGO ---
# Usamos [1, 4, 1] para balancear a logo e centralizar visualmente o texto
col_logo, col_center, col_right_spacer = st.columns([1, 4, 1])

with col_logo:
    try:
        st.image("logo.png", width=250)
    except:
        st.warning("Logo não encontrada")

with col_center:
    # 1. Título principal CENTRALIZADO
    st.markdown("<h1 style='text-align: center; font-size: 32px; padding-top: 20px;'>Agente Validador de ERP</h1>", unsafe_allow_html=True)
    
    # 2. Subtítulo CENTRALIZADO
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
    pass 

# 2. Tela Parceiros (ELIF)
elif st.session_state['pagina_atual'] == 'parceiros':
    st.header("Validação de Parceiros")
    st.subheader("Faça o upload do arquivo `parceiros.csv` abaixo:")
    arquivo_upado = st.file_uploader(" ", type=["csv"], key="uploader_parceiros")
    
    # Botão Iniciar Validação com type="secondary" (cor neutra)
    if arquivo_upado and st.button("Iniciar Validação", type="secondary", key="btn_parceiros"):
        with open(TEMP_PARCEIRO, "wb") as f:
            f.write(arquivo_upado.getbuffer())
        
        with st.spinner("Analisando regras de negócio..."):
            erros = validar_parceiros(TEMP_PARCEIRO)
        
        exibir_relatorio_erros(erros)
        if os.path.exists(TEMP_PARCEIRO): os.remove(TEMP_PARCEIRO)

# 3. Tela Produtos (ELIF)
elif st.session_state['pagina_atual'] == 'produtos':
    st.header("Validação de Produtos")
    st.subheader("Faça o upload do arquivo `produtos.csv` abaixo:")
    arquivo_upado = st.file_uploader(" ", type=["csv"], key="uploader_produtos")
    
    # Botão Iniciar Validação com type="secondary" (cor neutra)
    if arquivo_upado and st.button("Iniciar Validação", type="secondary", key="btn_produtos"):
        with open(TEMP_PRODUTO, "wb") as f:
            f.write(arquivo_upado.getbuffer())
            
        with st.spinner("Analisando NCMs, unidades e regras..."):
            erros = validar_produtos(TEMP_PRODUTO)
            
        exibir_relatorio_erros(erros)
        if os.path.exists(TEMP_PRODUTO): os.remove(TEMP_PRODUTO)

# 4. Tela Estoque (ELIF)
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

    # Botão Iniciar Validação com type="secondary" (cor neutra)
    if arquivo_estoque and arquivo_mestre and st.button("Iniciar Validação Cruzada", type="secondary", key="btn_estoque"):
        with open(TEMP_ESTOQUE, "wb") as f: f.write(arquivo_estoque.getbuffer())
        with open(TEMP_MESTRE_PRODUTO, "wb") as f: f.write(arquivo_mestre.getbuffer())
        
        with st.spinner("Cruzando dados com o mestre..."):
            erros = validar_estoque(TEMP_ESTOQUE)
            
        exibir_relatorio_erros(erros)
        
        if os.path.exists(TEMP_ESTOQUE): os.remove(TEMP_ESTOQUE)
        if os.path.exists(TEMP_MESTRE_PRODUTO): os.remove(TEMP_MESTRE_PRODUTO)