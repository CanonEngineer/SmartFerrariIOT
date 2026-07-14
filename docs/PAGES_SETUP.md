# GitHub Pages (ativar no site)

O botão **github-pages** com **X vermelho** NÃO é normal.
Significa que o deploy automático falhou (em geral porque a fonte do Pages
ainda não estava correta).

## Como publicar o Demo Lab (2 minutos)

1. Abra: https://github.com/CanonEngineer/SmartFerrariIOT/settings/pages
2. Em **Build and deployment → Source**, escolha:
   - **Deploy from a branch**
3. Branch: `gh-pages`
4. Folder: `/ (root)`
5. Clique em **Save**
6. Espere ~1 minuto e abra:
   - https://canonengineer.github.io/SmartFerrariIOT/
   - https://canonengineer.github.io/SmartFerrariIOT/demo/

Os botões do README apontam para `https://canonengineer.github.io/SmartFerrariIOT/demo/standalone.html`.
Cada `push` em `main` republica esta pasta via `.github/workflows/deploy-pages.yml`.

### Alternativa sem Actions

Se preferir sem workflow: Source = branch `main`, Folder = `/docs`.
