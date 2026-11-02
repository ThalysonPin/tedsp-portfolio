# TEDSP — Currículo e portfólio

Site pessoal de **Thalyson Emanuel**, com foco em IA, automação e desenvolvimento. Apresenta experiência profissional, estudos de caso, competências, formação e contato para recrutadores.

## Recursos

- Conteúdo em português e inglês, com seletor de idioma.
- Layout editorial claro e responsivo para computador e celular.
- Estudos de caso com detalhes em diálogos acessíveis.
- Currículos em PDF de uma página nos dois idiomas.
- Painel `/secret-admin` com login, publicação de conteúdo e uploads persistentes no Coolify.
- Navegação por teclado e respeito à preferência por movimento reduzido.

## Tecnologias

HTML, CSS e JavaScript puro na interface. Python 3.13 e SQLite no serviço administrativo, sem dependências externas. A cópia no GitHub Pages continua estática; o painel funciona na aplicação do Coolify.

## Executar localmente

Com Python 3 instalado, execute na pasta do projeto:

```sh
python3 -m http.server 4173 --directory dist
```

Abra <http://localhost:4173> no navegador. Esse comando mostra apenas a versão estática. Para testar login, edição e uploads, consulte [a configuração do painel](docs/admin.md).

## Estrutura e edição

| Arquivo | Conteúdo |
| --- | --- |
| `dist/index.html` | Estrutura da página, metadados e apresentação inicial |
| `dist/styles.css` | Cores, tipografia, layout e adaptação para celular |
| `dist/content.json` | Conteúdo inicial PT/EN, experiências, projetos, perfil e temas |
| `dist/site-content.js` | Cópia estática do conteúdo inicial para o GitHub Pages |
| `dist/app.js` | Renderização e interações do portfólio |
| `dist/content-runtime.js` | Perfil, temas e projetos administrados |
| `dist/admin/` | Interface do painel administrativo |
| `server/admin_server.py` | Login, publicação, SQLite e uploads |
| `dist/portrait.jpg` | Foto de perfil |
| `dist/curriculo-thalyson-pt.pdf` | Currículo em português |
| `dist/curriculo-thalyson-en.pdf` | Currículo em inglês |

No site de produção, edite o conteúdo em `/secret-admin`. O botão **Salvar e publicar** atualiza o portfólio imediatamente. Mudanças de conteúdo feitas no painel ficam no volume do Coolify, não criam commits no GitHub e sobrevivem a novos deploys. Os campos em PT e EN são editados separadamente; o painel não inventa traduções.

`dist/content.json` inicializa um banco novo. Em alterações pelo código, edite esse arquivo e regenere sua cópia estática (`window.PORTFOLIO_CONTENT = <JSON>;` em `dist/site-content.js`). O banco existente não é sobrescrito por um novo deploy. Exporte o JSON pelo painel para guardar uma cópia das edições; as fotos e PDFs exigem também backup do volume.

Os currículos são PDFs independentes. Ao alterar a carreira, envie os PDFs atualizados na área **Arquivos** do painel. Para regenerar os PDFs iniciais pelo código, use:

```sh
python3 -m pip install reportlab
python3 scripts/generate_cv.py
```

O gerador usa o conteúdo inicial de `dist/content.json`. Os resumos dos projetos selecionados ficam no próprio script. Ele atualiza os links de download e a cópia estática do conteúdo. Inclua os dois PDFs, `content.json`, `site-content.js`, `app.js` e `index.html` no commit. Ele não altera o banco do painel já instalado. O deploy no Coolify continua manual.

Os diagramas dos estudos de caso representam os fluxos descritos; não são demonstrações executáveis.

## Hospedagem

O endereço de produção é <https://tedsptech.com/>, com DNS administrado na Hostinger.

A publicação na VPS é gerenciada pelo Coolify e usa a branch `main`:

- `Dockerfile.coolify` executa os testes, sincroniza as issues públicas e suas imagens e inicia o servidor Python.
- `docker-compose.coolify.yml` conecta o site à rede externa `coolify-edge`, com o alias estável `tedsp-portfolio`, sem publicar portas adicionais na VPS.
- O volume `portfolio-data`, montado em `/data`, guarda o banco SQLite e os uploads fora da imagem de deploy.
- No Coolify, o projeto usa o build pack Docker Compose, o arquivo `/docker-compose.coolify.yml` e o cache de build desativado para atualizar as issues a cada publicação.

Para colocar alterações no ar, faça o push para `main` e clique em **Deploy** na aplicação do Coolify. Uma nova publicação também atualiza a seção de projetos com o estado atual das issues. Os eventos de issues do GitHub Pages não iniciam automaticamente uma publicação no Coolify.

Na primeira instalação do painel, configure `PUBLIC_ORIGIN=https://tedsptech.com` e `ADMIN_SETUP_TOKEN` nas variáveis da aplicação no Coolify e faça o deploy manual. Em `/secret-admin`, use o código de configuração para definir a senha do e-mail `thalysonemanuels.p@gmail.com`. [Instruções e recuperação de acesso](docs/admin.md).

O workflow `.github/workflows/pages.yml` continua disponível para publicar uma cópia estática no GitHub Pages. Ele recebe eventos de push, issues e execução manual. O login e as edições do painel são exclusivos da aplicação Python no Coolify.

## Projetos sincronizados das issues

A seção “Projetos no GitHub”, dentro de Projetos, publica **todas as issues deste repositório**, abertas ou fechadas. O visitante lê a documentação e vê as imagens no próprio site, sem precisar acessar o repositório privado.

Para incluir um projeto:

1. Crie uma issue com título, descrição e imagens.
2. Clique em **Deploy** no Coolify para atualizar o site de produção. O workflow “Publish portfolio to GitHub Pages” atualiza a cópia do Pages quando uma issue é aberta, editada, etiquetada, fechada, reaberta, transferida ou excluída.

Issues fechadas continuam visíveis. Excluir ou transferir uma issue para outro repositório a retira do site. Pull requests e comentários não entram na sincronização. O título, corpo, etiquetas, data de atualização e imagens de todas as issues são publicados no site público. Esta é a configuração solicitada pelo proprietário do repositório.

O script `scripts/sync_github_issues.py` usa o `GITHUB_TOKEN` temporário do Actions com leitura de issues e conteúdo. Ele busca todas as páginas da API, utiliza o Markdown renderizado pelo GitHub, sanitiza o HTML e copia as imagens para `dist/issue-media/`. O navegador recebe apenas arquivos estáticos, sem token ou chamadas autenticadas.

A sincronização aceita imagens PNG, JPEG, GIF e WebP hospedadas no GitHub, inclusive arquivos do próprio repositório e anexos de issues. As imagens são baixadas novamente em cada publicação; erros de sincronização interrompem a nova publicação e preservam a versão anterior do site. Remover um projeto também retira suas imagens do artefato publicado.

A seleção PT/EN troca os títulos, os resumos, os textos completos, as legendas e os diagramas dos projetos. Os seis projetos existentes têm versões editoriais em primeira pessoa. Capturas reais mantêm a interface original, com legendas no idioma selecionado.

Cada issue bilíngue usa o formato abaixo. O script aproveita o Markdown renderizado pelo GitHub, separa os idiomas e sanitiza cada versão antes de publicar. Os arquivos de referência ficam em `docs/portfolio/<número>.pt.md` e `.en.md`.

```md
<!-- portfolio:pt -->
<details open>
<summary>Português</summary>

# Título em português

## Visão geral

Descrevo aqui o que construí.

</details>
<!-- portfolio:en -->
<details>
<summary>English</summary>

# English title

## Overview

I explain what I built here.

</details>
<!-- /portfolio -->
```

Novos projetos precisam das duas versões para aparecerem traduzidos em EN. Uma issue antiga sem esses blocos continua disponível em PT; em EN, o site mostra um aviso em inglês e o link da documentação original. Blocos bilíngues incompletos interrompem a publicação em vez de misturar idiomas.

Os arquivos `dist/issue-projects.js` e `dist/issue-media/` mantêm uma cópia inicial para a prévia local. No Coolify e no Actions, são regenerados antes da publicação, sem criar um commit automático na `main`.

Para sincronizar localmente, forneça um token com leitura do repositório em `GITHUB_TOKEN` e execute:

```sh
python3 scripts/sync_github_issues.py
```

Para verificar a seleção, a paginação e a sanitização:

```sh
python3 -m unittest discover -s tests
```

## Autoria

Thalyson Emanuel · [LinkedIn](https://www.linkedin.com/in/thalysonemanuel/) · [GitHub](https://github.com/ThalysonPin)
