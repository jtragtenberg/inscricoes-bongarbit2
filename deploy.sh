#!/usr/bin/env bash
set -e

echo "Baixando planilha e gerando dashboard..."
python3 build_dashboard.py

echo "Encriptando..."
npx staticrypt@3.5.4 index.html --password senhasecreta --short
cp encrypted/index.html index.html
rm -rf encrypted/

echo "Publicando..."
git add index.html
if git diff --cached --quiet; then
  echo "Nenhuma mudança — site já está atualizado."
else
  git commit -m "Atualiza dashboard $(date '+%Y-%m-%d %H:%M')"
  git push origin main
  echo "✓ Site atualizado: https://jtragtenberg.github.io/inscricoes-bongarbit2/"
fi
