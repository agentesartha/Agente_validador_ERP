import pandas as pd
import re
import sys

# --- Funções de Validação de Documentos (CPF/CNPJ) ---
# (Estas são as lógicas de cálculo de dígito verificador. 
#  Elas são complexas, mas essenciais para o agente.)

def _calcular_digito_cpf(cpf_parcial):
    """Calcula um dígito verificador de CPF."""
    soma = 0
    fator = len(cpf_parcial) + 1
    for digito in cpf_parcial:
        soma += int(digito) * fator
        fator -= 1
    resto = soma % 11
    return 0 if resto < 2 else 11 - resto

def validar_cpf(cpf):
    """Valida um CPF completo (11 dígitos)."""
    if not cpf.isdigit() or len(cpf) != 11:
        return False
    # Verifica se são todos dígitos iguais (inválido)
    if len(set(cpf)) == 1:
        return False
        
    cpf_parcial = cpf[:9]
    digito1 = _calcular_digito_cpf(cpf_parcial)
    
    cpf_parcial += str(digito1)
    digito2 = _calcular_digito_cpf(cpf_parcial)
    
    return cpf == f"{cpf[:9]}{digito1}{digito2}"

def _calcular_digito_cnpj(cnpj_parcial):
    """Calcula um dígito verificador de CNPJ."""
    soma = 0
    # Fatores de multiplicação do CNPJ
    fatores = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    if len(cnpj_parcial) == 13: # Cálculo do segundo dígito
        fatores.insert(0, 6)
        
    for i, digito in enumerate(cnpj_parcial):
        soma += int(digito) * fatores[i]
        
    resto = soma % 11
    return 0 if resto < 2 else 11 - resto

def validar_cnpj(cnpj):
    """Valida um CNPJ completo (14 dígitos)."""
    if not cnpj.isdigit() or len(cnpj) != 14:
        return False
    # Verifica se são todos dígitos iguais (inválido)
    if len(set(cnpj)) == 1:
        return False

    cnpj_parcial = cnpj[:12]
    digito1 = _calcular_digito_cnpj(cnpj_parcial)
    
    cnpj_parcial += str(digito1)
    digito2 = _calcular_digito_cnpj(cnpj_parcial)

    return cnpj == f"{cnpj[:12]}{digito1}{digito2}"

# --- Função Principal de Validação ---

def validar_parceiros(caminho_arquivo):
    """
    Função principal para carregar e validar a planilha de parceiros (TGFPAR).
    """
    
    # Lista para armazenar todos os erros encontrados
    erros_encontrados = []
    
    # ----------------------------------------------------
    # 1. CARREGAR OS DADOS
    # ----------------------------------------------------
    try:
        # dtype=str garante que CNPJs e CEPs não percam o zero à esquerda
        df = pd.read_csv(caminho_arquivo, sep=';', dtype=str)
        # Substitui valores nulos (NaN) por strings vazias para evitar erros
        df = df.fillna('')
    except FileNotFoundError:
        print(f"Erro fatal: Arquivo não encontrado em '{caminho_arquivo}'")
        return []
    except Exception as e:
        print(f"Erro ao ler o CSV: {e}")
        return []

    # ----------------------------------------------------
    # 2. CORREÇÕES AUTOMÁTICAS E "LIMPEZA" (PREPARAÇÃO)
    # ----------------------------------------------------
    # Cria novas colunas "limpas" para validação, preservando as originais
    
    # Remove ".", "/", "-" de CGC_CPF
    df['CGC_CPF_limpo'] = df['CGC_CPF'].str.replace(r'[./-]', '', regex=True)
    
    # Remove "-" de CEP
    df['CEP_limpo'] = df['CEP'].str.replace('-', '', regex=True)
    df['CPL_CEPENTREGA_limpo'] = df['CPL_CEPENTREGA'].str.replace('-', '', regex=True)
    
    # Converte colunas de domínio para maiúsculas
    df['TIPPESSOA_limpo'] = df['TIPPESSOA'].str.upper()
    df['ATIVO_limpo'] = df['ATIVO'].str.upper()
    df['CLIENTE_limpo'] = df['CLIENTE'].str.upper()
    df['FORNECEDOR_limpo'] = df['FORNECEDOR'].str.upper()

    # ----------------------------------------------------
    # 3. VALIDAÇÃO DE REGRAS (LINHA A LINHA)
    # ----------------------------------------------------
    print(f"Iniciando validação de {len(df)} parceiros...")

    for index, row in df.iterrows():
        # O número da linha no arquivo (index + 2) facilita para o usuário
        linha_num = index + 2 
        
        def adicionar_erro(coluna, valor, mensagem):
            """Função helper para adicionar erros à lista."""
            erros_encontrados.append({
                "linha": linha_num,
                "coluna": coluna,
                "valor_encontrado": str(valor),
                "erro": mensagem
            })

        # --- Regras do "Leia-me" (TGFPAR) ---
        
        # [Obrigatório] AD_IDEXTERNO
        if not row['AD_IDEXTERNO']:
            adicionar_erro('AD_IDEXTERNO', row['AD_IDEXTERNO'], "Campo obrigatório está vazio.")
        
        # [Obrigatório] NOMEPARC
        if not row['NOMEPARC']:
            adicionar_erro('NOMEPARC', row['NOMEPARC'], "Campo obrigatório (Nome do Parceiro) está vazio.")
        
        # [Domínio] TIPPESSOA
        if not row['TIPPESSOA_limpo']:
            adicionar_erro('TIPPESSOA', row['TIPPESSOA'], "Campo obrigatório (Tipo de Pessoa) está vazio.")
        elif row['TIPPESSOA_limpo'] not in ('F', 'J'):
            adicionar_erro('TIPPESSOA', row['TIPPESSOA'], "Valor inválido. Permitido apenas 'F' ou 'J'.")

        # [Formato] EMAIL
        if not row['EMAIL']:
            adicionar_erro('EMAIL', row['EMAIL'], "Campo obrigatório (Email) está vazio.")
        elif not re.match(r"[^@]+@[^@]+\.[^@]+", row['EMAIL']):
            adicionar_erro('EMAIL', row['EMAIL'], "Formato de e-mail inválido.")

        # [Formato] CEP
        if not row['CEP_limpo']:
            adicionar_erro('CEP', row['CEP'], "Campo obrigatório (CEP) está vazio.")
        elif not row['CEP_limpo'].isdigit() or len(row['CEP_limpo']) != 8:
            adicionar_erro('CEP', row['CEP'], "Formato inválido. CEP deve ter 8 dígitos numéricos.")

        # --- VALIDAÇÃO CONDICIONAL (A "INTELIGÊNCIA") ---
        
        tipo_pessoa = row['TIPPESSOA_limpo']
        documento = row['CGC_CPF_limpo']
        
        if not documento:
            adicionar_erro('CGC_CPF', row['CGC_CPF'], "Campo obrigatório (CNPJ/CPF) está vazio.")
        
        elif tipo_pessoa == 'F':
            # Se for Pessoa Física...
            if len(documento) != 11:
                adicionar_erro('CGC_CPF', row['CGC_CPF'], f"Tipo Pessoa é 'F', mas o documento não tem 11 dígitos (tem {len(documento)}).")
            elif not validar_cpf(documento):
                adicionar_erro('CGC_CPF', row['CGC_CPF'], "Tipo Pessoa é 'F', mas o CPF é inválido (dígito verificador não confere).")
                
        elif tipo_pessoa == 'J':
            # Se for Pessoa Jurídica...
            if len(documento) != 14:
                adicionar_erro('CGC_CPF', row['CGC_CPF'], f"Tipo Pessoa é 'J', mas o documento não tem 14 dígitos (tem {len(documento)}).")
            elif not validar_cnpj(documento):
                adicionar_erro('CGC_CPF', row['CGC_CPF'], "Tipo Pessoa é 'J', mas o CNPJ é inválido (dígito verificador não confere).")

        # [Regra de Negócio] Razão Social vs Nome
        if tipo_pessoa == 'F' and row['NOMEPARC'] != row['RAZAOSOCIAL']:
             adicionar_erro('RAZAOSOCIAL', row['RAZAOSOCIAL'], "Para Pessoa Física, a Razão Social deve ser IDÊNTICA ao Nome do Parceiro.")
             
        # TODO: Adicionar validações de duplicidade (AD_IDEXTERNO, CGC_CPF)
        # TODO: Adicionar validações de Chave Estrangeira (ID_EXTERNO_CODCID, etc.)

    print(f"Validação concluída. Total de erros encontrados: {len(erros_encontrados)}")
    return erros_encontrados

# --- Bloco de Execução Principal ---

if __name__ == "__main__":
    
    # Ponto de entrada do script.
    # Certifique-se de ter o arquivo CSV no mesmo diretório ou ajuste o caminho.
    
    # Use 'parceiros_com_erros.csv' ou o nome do seu arquivo de teste
    ARQUIVO_DE_ENTRADA = "parceiros.csv" 
    
    # 1. Executa o validador
    erros = validar_parceiros(ARQUIVO_DE_ENTRADA)
    
    # 2. Exibe o relatório de erros de forma legível
    if not erros:
        print("\n✅ Nenhum erro encontrado. A planilha está pronta para importação!")
    else:
        print("\n❌ Erros de validação encontrados:")
        # Converte a lista de erros em um DataFrame para melhor visualização
        df_erros = pd.DataFrame(erros)
        
        # Agrupa os erros pela linha, para o usuário corrigir mais fácil
        for linha, grupo in df_erros.groupby('linha'):
            print(f"\n--- Erros na Linha {linha} ---")
            for _, erro in grupo.iterrows():
                print(f"  - Coluna: '{erro['coluna']}'")
                print(f"    Valor:  '{erro['valor_encontrado']}'")
                print(f"    Erro:   {erro['erro']}")