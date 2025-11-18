import streamlit as st
import pandas as pd
import os

# Importa as funções de validação
from validador_de_parceiro import validar_parceiros
from validador_de_produto import validar_produtos
from validador_de_estoque import validar_estoque

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="Validador CSV",
    page_icon="favicon.png", # Usa a logo na guia do navegador
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

# --- FUNÇÃO DE RELATÓRIO ---
def exibir_relatorio_erros(erros):
    if erros is None:
        st.error("❌ A validação falhou e não pôde ser concluída.")
    elif not erros:
        st.success("✅ SUCESSO! Nenhum erro encontrado. Planilha pronta para importação.")
        st.balloons() 
    else:
        st.error(f"❌ Foram encontrados {len(erros)} erros.")
        
        df_erros = pd.DataFrame(erros)
        
        # 1. Converte o DataFrame de erros para CSV (usando ponto e vírgula e UTF-8 para compatibilidade)
        csv_erros = df_erros.to_csv(index=False, sep=';', encoding='utf-8')
        
        # 2. EXIBE O BOTÃO DE DOWNLOAD (com type="primary" para destaque)
        st.download_button(
            label="⬇️ BAIXAR RELATÓRIO DE ERROS COMPLETO",
            data=csv_erros,
            file_name='relatorio_erros_validacao.csv',
            mime='text/csv',
            type="primary" # Torna o botão verde/azul neon, destacando-o
        )

        # 3. Exibe a tabela na interface (abaixo do botão)
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
# Usamos uma proporção de 1 (logo) : 4 (título centralizado) : 1 (espaço vazio)
col_logo, col_center, col_right_spacer = st.columns([1, 4, 1])

with col_logo:
    try:
        st.image("logo.png", width=250)
    except:
        st.warning("Logo não encontrada")

with col_center:
    # 1. Título principal CENTRALIZADO E BALANCEADO
    # Adicionamos um pequeno padding superior (20px) para alinhar melhor verticalmente com a logo
    st.markdown("<h1 style='text-align: center; font-size: 32px; padding-top: 20px;'>Agente Validador de ERP</h1>", unsafe_allow_html=True)
    
    # 2. Subtítulo CENTRALIZADO
    st.markdown("<h5 style='text-align: center; margin-top: 10px;'>Selecione abaixo qual tipo de planilha você deseja validar</h5>", unsafe_allow_html=True)
    
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

# 1. Tela Inicial (IF)
if st.session_state['pagina_atual'] == 'home':
    # O comando 'pass' é obrigatório aqui para o Python aceitar o bloco vazio
    pass 

# 2. Tela Parceiros (ELIF)
elif st.session_state['pagina_atual'] == 'parceiros':
    st.header("Validação de Parceiros")
    st.subheader("Faça o upload do arquivo `parceiros.csv` abaixo:")
    arquivo_upado = st.file_uploader(" ", type=["csv"], key="uploader_parceiros")
    
    if arquivo_upado and st.button("Iniciar Validação", type="primary", key="btn_parceiros"):
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
    
    if arquivo_upado and st.button("Iniciar Validação", type="primary", key="btn_produtos"):
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

    if arquivo_estoque and arquivo_mestre and st.button("Iniciar Validação Cruzada", type="primary", key="btn_estoque"):
        with open(TEMP_ESTOQUE, "wb") as f: f.write(arquivo_estoque.getbuffer())
        with open(TEMP_MESTRE_PRODUTO, "wb") as f: f.write(arquivo_mestre.getbuffer())
        
        with st.spinner("Cruzando dados com o mestre..."):
            erros = validar_estoque(TEMP_ESTOQUE)
            
        exibir_relatorio_erros(erros)
        
        if os.path.exists(TEMP_ESTOQUE): os.remove(TEMP_ESTOQUE)
        if os.path.exists(TEMP_MESTRE_PRODUTO): os.remove(TEMP_MESTRE_PRODUTO)