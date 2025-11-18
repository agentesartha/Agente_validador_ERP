import streamlit as st
import pandas as pd
import os

# Importa as funções de validação que você criou
from validador_de_parceiro import validar_parceiros
from validador_de_produto import validar_produtos
from validador_de_estoque import validar_estoque

# --- Constantes para nomes de arquivos temporários ---
# O Streamlit lida com arquivos em memória; nós os salvaremos
# temporariamente com esses nomes para que nossos validadores 
# (que esperam caminhos de arquivo) possam encontrá-los.

TEMP_PARCEIRO = "temp_parceiros.csv"
TEMP_PRODUTO = "temp_produtos.csv"
TEMP_ESTOQUE = "temp_estoque.csv"
TEMP_MESTRE_PRODUTO = "mestre_produtos.csv" # Nome exigido pelo validador de estoque


def exibir_relatorio_erros(erros):
    """Função helper para mostrar o relatório de erros no Streamlit."""
    if erros is None:
        st.error("❌ A validação falhou e não pôde ser concluída (Verifique os arquivos).")
    elif not erros:
        st.success("✅ Nenhum erro encontrado. A planilha está pronta para importação!")
    else:
        st.error("❌ Erros de validação encontrados:")
        df_erros = pd.DataFrame(erros)
        
        # Formata o DataFrame para melhor visualização
        df_erros = df_erros.set_index('linha')
        df_erros = df_erros[['coluna', 'valor_encontrado', 'erro']]
        st.dataframe(df_erros)

# --- Interface do Usuário (UI) ---

st.set_page_config(layout="wide")
st.title("🤖 Agente de Validação de Planilhas de ERP")
st.subheader("Faça o upload dos arquivos para validação")

# Menu de seleção para o tipo de validação
tipo_validacao = st.selectbox(
    "1. Qual planilha você quer validar?",
    ("Selecione...", "Parceiros", "Produtos", "Estoque")
)

# --- LÓGICA DE VALIDAÇÃO ---

if tipo_validacao == "Parceiros":
    arquivo_upado = st.file_uploader("2. Faça o upload da planilha `parceiros.csv`", type="csv")
    
    if st.button("Validar Parceiros"):
        if arquivo_upado is not None:
            # Salva o arquivo temporariamente
            with open(TEMP_PARCEIRO, "wb") as f:
                f.write(arquivo_upado.getbuffer())
            
            # Executa o validador
            with st.spinner("Validando..."):
                erros = validar_parceiros(TEMP_PARCEIRO)
            
            # Exibe os resultados
            exibir_relatorio_erros(erros)
            
            # Limpa o arquivo temporário
            os.remove(TEMP_PARCEIRO)
        else:
            st.warning("Por favor, faça o upload do arquivo.")

# ---
elif tipo_validacao == "Produtos":
    arquivo_upado = st.file_uploader("2. Faça o upload da planilha `produtos.csv`", type="csv")
    
    if st.button("Validar Produtos"):
        if arquivo_upado is not None:
            # Salva o arquivo temporariamente
            with open(TEMP_PRODUTO, "wb") as f:
                f.write(arquivo_upado.getbuffer())

            # Executa o validador
            with st.spinner("Validando..."):
                erros = validar_produtos(TEMP_PRODUTO)

            # Exibe os resultados
            exibir_relatorio_erros(erros)

            # Limpa o arquivo temporário
            os.remove(TEMP_PRODUTO)
        else:
            st.warning("Por favor, faça o upload do arquivo.")

# ---
elif tipo_validacao == "Estoque":
    st.info("Para validar o Estoque, precisamos de 2 arquivos:")
    
    # O validador de estoque precisa de DOIS arquivos
    arquivo_estoque = st.file_uploader("2. Faça o upload da planilha `estoque.csv`", type="csv")
    arquivo_mestre_prod = st.file_uploader(f"3. Faça o upload do arquivo mestre `{TEMP_MESTRE_PRODUTO}`", type="csv")

    if st.button("Validar Estoque"):
        if arquivo_estoque is not None and arquivo_mestre_prod is not None:
            # Salva os arquivos temporariamente com os nomes que o validador espera
            with open(TEMP_ESTOQUE, "wb") as f:
                f.write(arquivo_estoque.getbuffer())
            with open(TEMP_MESTRE_PRODUTO, "wb") as f:
                f.write(arquivo_mestre_prod.getbuffer())
            
            # Executa o validador
            with st.spinner("Carregando mestres e validando estoque..."):
                erros = validar_estoque(TEMP_ESTOQUE)
                
            # Exibe os resultados
            exibir_relatorio_erros(erros)

            # Limpa os arquivos temporários
            os.remove(TEMP_ESTOQUE)
            os.remove(TEMP_MESTRE_PRODUTO)
        else:
            st.warning("Por favor, faça o upload dos DOIS arquivos.")