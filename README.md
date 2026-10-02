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

Publique o conteúdo de `dist/` em uma hospedagem estática. O endereço atual do site é:

<https://tedsp-thalyson-emanuel.thalysonemanuels-p.chatgpt.site/>

O acesso ao site depende das configurações da hospedagem. Este repositório mantém uma cópia do código; alterações aqui precisam ser publicadas na hospedagem para aparecerem no site.

## Autoria

Thalyson Emanuel · [LinkedIn](https://www.linkedin.com/in/thalysonemanuel/) · [GitHub](https://github.com/ThalysonPin)

