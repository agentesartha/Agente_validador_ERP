# Dockerfile (Corrigido)

# 1. Imagem Base
FROM python:3.10-slim

# 2. Definir o diretório de trabalho
WORKDIR /app

# --- NOVO BLOCO: INSTALAÇÃO DO GIT ---
RUN apt update && apt install git -y 
# --- FIM DO NOVO BLOCO ---

# 3. Instalar dependências
# Copia APENAS o requirements.txt. Isso é bom para o cache.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# A linha "COPY . ." foi REMOVIDA. O "Portal" (mounts)
# no devcontainer.json cuidará dos arquivos.

# 4. Comando para manter o container "vivo"
CMD ["tail", "-f", "/dev/null"]