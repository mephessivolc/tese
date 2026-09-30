# Utiliza a imagem oficial completa do TeX Live
FROM texlive/texlive:latest

# Define o diretório de trabalho dentro do container
WORKDIR /workspace

# Cria a pasta 'build' caso ela ainda não exista
RUN mkdir -p /workspace/build

# Comando padrão para compilar o arquivo main.tex enviando os resultados para a pasta build
CMD ["latexmk", "-pdf", "-outdir=build", "main.tex"]