import pandas as pd
import re
import sys

# --- Listas de Domínio (Valores Permitidos) ---

# Valores permitidos para a coluna UNIDADE
DOMINIO_UNIDADE = {'CM', 'M', 'MM'}

# Valores permitidos para a coluna USOPROD
DOMINIO_USOPROD = {
    '1', '2', '4', 'B', 'C', 'D', 'E', 'F', 
    'I', 'M', 'O', 'P', 'R', 'T', 'V'
}

# Valores permitidos para colunas Sim/Não
DOMINIO_SIM_NAO = {'S', 'N'}


# --- Função Principal de Validação ---

def validar_produtos(caminho_arquivo):
    """
    Função principal para carregar e validar a planilha de produtos (TGFPRO).
    """
    
    erros_encontrados = []
    
    # ----------------------------------------------------
    # 1. CARREGAR OS DADOS
    # ----------------------------------------------------
    try:
        # Usamos 'latin-1' e dtype=str por padrão
        df = pd.read_csv(caminho_arquivo, sep=';', dtype=str, encoding='latin-1')
        df = df.fillna('')
    except FileNotFoundError:
        print(f"Erro fatal: Arquivo não encontrado em '{caminho_arquivo}'")
        return None # Retorna None em caso de falha de leitura
    except Exception as e:
        print(f"Erro ao ler o CSV: {e}")
        return None # Retorna None em caso de falha de leitura

    # ----------------------------------------------------
    # 2. CORREÇÕES AUTOMÁTICAS E "LIMPEZA" (PREPARAÇÃO)
    # ----------------------------------------------------
    
    # Converte colunas de domínio para maiúsculas (e remove espaços)
    df['UNIDADE_limpo'] = df['UNIDADE'].str.upper().str.strip()
    df['USOPROD_limpo'] = df['USOPROD'].str.upper().str.strip()
    df['TEMIPICOMPRA_limpo'] = df['TEMIPICOMPRA'].str.upper().str.strip()
    df['TEMIPIVENDA_limpo'] = df['TEMIPIVENDA'].str.upper().str.strip()
    df['USACODBARRASQTD_limpo'] = df['USACODBARRASQTD'].str.upper().str.strip()
    
    # Remove pontos/barras do NCM
    df['NCM_limpo'] = df['NCM'].str.replace(r'[./-]', '', regex=True)

    # ----------------------------------------------------
    # 3. VALIDAÇÃO DE REGRAS (LINHA A LINHA)
    # ----------------------------------------------------
    print(f"Iniciando validação de {len(df)} produtos...")

    for index, row in df.iterrows():
        linha_num = index + 2 
        
        def adicionar_erro(coluna, valor, mensagem):
            erros_encontrados.append({
                "linha": linha_num,
                "coluna": coluna,
                "valor_encontrado": str(valor),
                "erro": mensagem
            })

        # --- Regras do "Leia-me" (TGFPRO) ---
        
        # [Obrigatório] AD_IDEXTERNO
        if not row['AD_IDEXTERNO']:
            adicionar_erro('AD_IDEXTERNO', row['AD_IDEXTERNO'], "Campo obrigatório está vazio.")
        elif len(row['AD_IDEXTERNO']) > 256:
            adicionar_erro('AD_IDEXTERNO', row['AD_IDEXTERNO'], "Tamanho máximo (256) excedido.")

        # [Obrigatório] ID_EXTERNO_CODGRUPOPROD
        if not row['ID_EXTERNO_CODGRUPOPROD']:
            adicionar_erro('ID_EXTERNO_CODGRUPOPROD', row['ID_EXTERNO_CODGRUPOPROD'], "Campo obrigatório está vazio.")
        
        # [Obrigatório] CODVOL
        if not row['CODVOL']:
            adicionar_erro('CODVOL', row['CODVOL'], "Campo obrigatório (Unidade padrão) está vazio.")
        elif len(row['CODVOL']) > 2:
            adicionar_erro('CODVOL', row['CODVOL'], "Tamanho máximo (2) excedido.")

        # [Obrigatório] DESCRPROD
        if not row['DESCRPROD']:
            adicionar_erro('DESCRPROD', row['DESCRPROD'], "Campo obrigatório (Descrição) está vazio.")
        elif len(row['DESCRPROD']) > 100:
            adicionar_erro('DESCRPROD', row['DESCRPROD'], "Tamanho máximo (100) excedido.")

        # [Obrigatório] MARCA
        if not row['MARCA']:
            adicionar_erro('MARCA', row['MARCA'], "Campo obrigatório está vazio.")
        elif len(row['MARCA']) > 20:
            adicionar_erro('MARCA', row['MARCA'], "Tamanho máximo (20) excedido.")

        # [Obrigatório] NCM
        ncm = row['NCM_limpo']
        if not ncm:
            adicionar_erro('NCM', row['NCM'], "Campo obrigatório está vazio.")
        elif not ncm.isdigit():
            adicionar_erro('NCM', row['NCM'], "NCM deve conter apenas números.")
        elif len(ncm) > 10:
            adicionar_erro('NCM', row['NCM'], "Tamanho máximo (10) excedido.")

        # [Obrigatório] REFERENCIA
        if not row['REFERENCIA']:
            adicionar_erro('REFERENCIA', row['REFERENCIA'], "Campo obrigatório está vazio.")
        elif len(row['REFERENCIA']) > 15:
            adicionar_erro('REFERENCIA', row['REFERENCIA'], "Tamanho máximo (15) excedido.")

        # --- Validação de Domínio (Valores Permitidos) ---

        # [Domínio] UNIDADE
        unidade = row['UNIDADE_limpo']
        if unidade and unidade not in DOMINIO_UNIDADE: # Se preenchido, valida
            adicionar_erro('UNIDADE', row['UNIDADE'], f"Valor inválido. Permitidos: {', '.join(DOMINIO_UNIDADE)}.")

        # [Domínio] USOPROD
        usoprod = row['USOPROD_limpo']
        if usoprod and usoprod not in DOMINIO_USOPROD: # Se preenchido, valida
            adicionar_erro('USOPROD', row['USOPROD'], f"Valor inválido. Não está na lista de 'Usado como'.")

        # [Domínio] TEMIPICOMPRA
        temipicompra = row['TEMIPICOMPRA_limpo']
        if temipicompra and temipicompra not in DOMINIO_SIM_NAO:
            adicionar_erro('TEMIPICOMPRA', row['TEMIPICOMPRA'], "Valor inválido. Permitido apenas 'S' ou 'N'.")

        # [Domínio] TEMIPIVENDA
        temipivenda = row['TEMIPIVENDA_limpo']
        if temipivenda and temipivenda not in DOMINIO_SIM_NAO:
            adicionar_erro('TEMIPIVENDA', row['TEMIPIVENDA'], "Valor inválido. Permitido apenas 'S' ou 'N'.")

        # [Domínio] USACODBARRASQTD
        usacodbq = row['USACODBARRASQTD_limpo']
        if usacodbq and usacodbq not in DOMINIO_SIM_NAO:
            adicionar_erro('USACODBARRASQTD', row['USACODBARRASQTD'], "Valor inválido. Permitido apenas 'S' ou 'N'.")

        # TODO: Adicionar validações de duplicidade (AD_IDEXTERNO)
        # TODO: Adicionar validações de Chave Estrangeira (ID_EXTERNO_CODGRUPOPROD)

    print(f"Validação concluída. Total de erros encontrados: {len(erros_encontrados)}")
    return erros_encontrados

# --- Bloco de Execução Principal ---

if __name__ == "__main__":
    
    # Nome do arquivo de produtos que o script vai procurar
    ARQUIVO_DE_ENTRADA = "produtos.csv" 
    
    # 1. Executa o validador
    erros = validar_produtos(ARQUIVO_DE_ENTRADA)
    
    # 2. Exibe o relatório de erros de forma legível
    if erros is None:
        print("\n❌ A validação falhou e não pôde ser concluída.")
    elif not erros:
        print("\n✅ Nenhum erro encontrado. A planilha está pronta para importação!")
    else:
        print("\n❌ Erros de validação encontrados:")
        df_erros = pd.DataFrame(erros)
        
        for linha, grupo in df_erros.groupby('linha'):
            print(f"\n--- Erros na Linha {linha} ---")
            for _, erro in grupo.iterrows():
                print(f"  - Coluna: '{erro['coluna']}'")
                print(f"    Valor:  '{erro['valor_encontrado']}'")
                print(f"    Erro:   {erro['erro']}")