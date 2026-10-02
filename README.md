# TEDSP — Currículo e portfólio

Site pessoal de **Thalyson Emanuel**, com foco em IA, automação e desenvolvimento. Apresenta experiência profissional, estudos de caso, competências, formação e contato para recrutadores.

## Recursos

- Conteúdo em português e inglês, com seletor de idioma.
- Layout editorial claro e responsivo para computador e celular.
- Estudos de caso com detalhes em diálogos acessíveis.
- Currículos em PDF de uma página nos dois idiomas.
- Navegação por teclado e respeito à preferência por movimento reduzido.

## Tecnologias

HTML, CSS e JavaScript puro. O site não exige instalação de dependências nem compilação.

## Executar localmente

Com Python 3 instalado, execute na pasta do projeto:

```sh
python3 -m http.server 4173 --directory dist
```

Abra <http://localhost:4173> no navegador. Qualquer servidor de arquivos estáticos também pode servir a pasta `dist/`.

## Estrutura e edição

| Arquivo | Conteúdo |
| --- | --- |
| `dist/index.html` | Estrutura da página, metadados e apresentação inicial |
| `dist/styles.css` | Cores, tipografia, layout e adaptação para celular |
| `dist/app.js` | Textos PT/EN, experiências, estudos de caso e interações |
| `dist/portrait.jpg` | Foto de perfil |
| `dist/curriculo-thalyson-pt.pdf` | Currículo em português |
| `dist/curriculo-thalyson-en.pdf` | Currículo em inglês |

Ao atualizar experiências ou contato, revise os textos nos dois idiomas em `app.js` e os metadados de `index.html`. Os PDFs são arquivos independentes e devem ser substituídos quando o currículo mudar. Os diagramas dos estudos de caso representam os fluxos descritos; não são demonstrações executáveis.

## Hospedagem

O site é hospedado no GitHub Pages e está disponível em:

<https://tedsptech.com/>

O workflow `.github/workflows/pages.yml` publica o conteúdo de `dist/` automaticamente após cada push para `main`. Também é possível iniciar a publicação manualmente pela aba Actions, no workflow “Publish portfolio to GitHub Pages”.

O domínio personalizado é configurado em Settings → Pages. Os registros DNS são gerenciados na Hostinger.

## Projetos sincronizados das issues

A seção “Projetos no GitHub”, dentro de Projetos, publica **todas as issues deste repositório**, abertas ou fechadas. O visitante lê a documentação e vê as imagens no próprio site, sem precisar acessar o repositório privado.

Para incluir um projeto:

1. Crie uma issue com título, descrição e imagens.
2. Aguarde o workflow “Publish portfolio to GitHub Pages” concluir. Abrir ou editar a issue, adicionar ou remover uma etiqueta, fechar, reabrir, transferir ou excluir a issue inicia uma nova publicação.

Issues fechadas continuam visíveis. Excluir ou transferir uma issue para outro repositório a retira do site. Pull requests e comentários não entram na sincronização. O título, corpo, etiquetas, data de atualização e imagens de todas as issues são publicados no site público. Esta é a configuração solicitada pelo proprietário do repositório.

O script `scripts/sync_github_issues.py` usa o `GITHUB_TOKEN` temporário do Actions com leitura de issues e conteúdo. Ele busca todas as páginas da API, utiliza o Markdown renderizado pelo GitHub, sanitiza o HTML e copia as imagens para `dist/issue-media/`. O navegador recebe apenas arquivos estáticos, sem token ou chamadas autenticadas.

A sincronização aceita imagens PNG, JPEG, GIF e WebP hospedadas no GitHub, inclusive arquivos do próprio repositório e anexos de issues. As imagens são baixadas novamente em cada publicação; erros de sincronização interrompem a nova publicação e preservam a versão anterior do site. Remover um projeto também retira suas imagens do artefato publicado.

O corpo da documentação permanece no idioma em que a issue foi escrita. Os títulos e controles da interface acompanham a seleção PT/EN.

Os arquivos `dist/issue-projects.js` e `dist/issue-media/` mantêm uma cópia inicial para a prévia local. No Actions, são regenerados antes da publicação; editar uma issue atualiza o site sem criar um commit automático na `main`.

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
