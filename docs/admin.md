# Painel do portfólio

O painel fica em `https://tedsptech.com/secret-admin`. O endereço não é a proteção de acesso: o servidor exige uma sessão autenticada para ler ou alterar o conteúdo administrativo.

## Primeira instalação no Coolify

1. Nas variáveis da aplicação, configure `PUBLIC_ORIGIN=https://tedsptech.com` (sem barra final) e `ADMIN_SETUP_TOKEN` com um código aleatório de pelo menos 32 caracteres. É um código de instalação temporário, diferente da senha de login.
2. Faça o deploy manual da `main`. O Compose mantém a rede `coolify-edge`, o alias `tedsp-portfolio` e a porta interna 80. Ele cria o volume persistente `portfolio-data` em `/data`.
3. Abra `/secret-admin`, informe o código de instalação e defina uma senha de pelo menos 12 caracteres para `thalysonemanuels.p@gmail.com`.
4. Depois do primeiro cadastro, o código de instalação deixa de criar contas. Você pode remover a variável `ADMIN_SETUP_TOKEN` na próxima publicação. A senha fica armazenada como hash no banco e não aparece no código ou na API pública.

Para gerar um código no seu próprio terminal, se precisar:

```sh
python3 -c 'import secrets; print(secrets.token_urlsafe(32))'
```

O e-mail de login é definido por `ADMIN_EMAIL`; o Compose já configura o endereço solicitado. Alterar o e-mail de contato do portfólio não muda as credenciais de administrador.

## Edição

- Textos: todos os campos da interface, em PT e EN. Os textos de apresentação aceitam apenas as marcações simples `br`, `em` e `strong`.
- Experiências: criar, editar, ordenar e remover registros, com cargo, empresa, período, descrição, complemento e tecnologias.
- Projetos: gerenciar estudos de caso e documentação. Projetos sincronizados das issues podem receber uma versão local editada ou ser ocultados. Isso não altera nem exclui a issue original no GitHub. Novos projetos podem ser criados diretamente no painel.
- Perfil e competências: nome, marca, contatos, números de experiência e grupos de ferramentas.
- Arquivos: foto JPEG, PNG ou WebP até 5 MB e currículos PDF em PT e EN até 15 MB. O envio prepara o arquivo; **Salvar e publicar** aplica os novos links ao site. Alterar experiências não reescreve automaticamente os PDFs.
- Aparência: cores dos temas claro e escuro e tema padrão. Uma preferência já salva pelo visitante continua prevalecendo sobre o padrão.

**Salvar e publicar** disponibiliza o conteúdo na próxima abertura ou atualização da página pública. As alterações permanecem na tela enquanto você edita. O servidor rejeita uma publicação quando outra aba já salvou uma versão mais recente, para evitar sobrescrita silenciosa.

## Dados e deploys

O SQLite e os arquivos enviados ficam no volume `/data`, fora do repositório. Reinícios e novos deploys reutilizam esse volume. Não remova o volume para atualizar o site. Guarde uma cópia do volume no seu processo de backup da VPS; a exportação JSON do painel preserva o conteúdo, mas não inclui os arquivos binários enviados.

O primeiro início copia `dist/content.json` para o banco. Depois disso, novos deploys não apagam as edições do painel. As issues continuam sendo sincronizadas durante o build e recebem as edições locais na renderização. A cópia do GitHub Pages usa os arquivos estáticos do repositório e não recebe as mudanças salvas na VPS.

## Teste local completo

Execute com Python 3.13 ou superior. Use um diretório de dados de teste fora de `dist` e configure um código somente para essa instalação local:

```sh
export PORT=4173
export DATA_DIR=/tmp/tedsp-admin-local
export PUBLIC_ORIGIN=http://127.0.0.1:4173
read -s ADMIN_SETUP_TOKEN
export ADMIN_SETUP_TOKEN
python3 server/admin_server.py
```

Abra `http://127.0.0.1:4173/secret-admin`. Em produção, mantenha HTTPS no `PUBLIC_ORIGIN`; o cookie de sessão usa `Secure`, `HttpOnly` e `SameSite=Strict`. As mutações autenticadas também exigem token CSRF e origem correspondente. Há limitação de tentativas de login.

Para executar os testes de autorização, persistência, publicação e sincronização:

```sh
python3 -m unittest discover -s tests -v
```

## Recuperação da senha

No terminal autenticado da aplicação no Coolify, execute:

```sh
python server/admin_server.py reset-password
```

O comando pede e confirma a nova senha sem mostrá-la na tela, preserva o conteúdo e encerra as sessões existentes. A recuperação não é exposta por uma rota pública.
