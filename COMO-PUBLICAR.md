# Como publicar o Corretor de Redações

Siga os passos abaixo uma única vez. Depois o app fica disponível 24h pelo celular.

---

## Pré-requisitos (gratuitos)

- [ ] Conta no GitHub: https://github.com (crie se não tiver)
- [ ] Conta no Render: https://render.com (crie com o mesmo e-mail)
- [ ] Chave de API da Anthropic: https://console.anthropic.com → "API Keys" → "Create Key"

---

## Passo 1 — Criar repositório no GitHub

1. Acesse https://github.com/new
2. Nome do repositório: `corretor-redacao`
3. Deixe como **Privado** (Private)
4. Clique em "Create repository"
5. Na página seguinte, anote a URL do repositório (ex: `https://github.com/seunome/corretor-redacao`)

---

## Passo 2 — Enviar os arquivos para o GitHub

Se você não tem o Git instalado, instale em: https://git-scm.com/download/win

Abra o Prompt de Comando (cmd) e execute:

```
cd C:\Users\daian\corretor-redacao-app
git init
git add .
git commit -m "primeira versão"
git remote add origin https://github.com/SEU-USUARIO/corretor-redacao.git
git push -u origin main
```

(Substitua SEU-USUARIO pelo seu usuário do GitHub)

---

## Passo 3 — Publicar no Render

1. Acesse https://render.com e faça login
2. Clique em "New +" → "Web Service"
3. Conecte sua conta do GitHub quando pedido
4. Selecione o repositório `corretor-redacao`
5. Render vai detectar o arquivo `render.yaml` automaticamente
6. Na tela de configuração, procure a seção **Environment Variables**
7. Adicione:
   - Key: `ANTHROPIC_API_KEY`
   - Value: (cole aqui sua chave que começa com `sk-ant-...`)
8. Clique em "Create Web Service"
9. Aguarde o deploy finalizar (3–5 minutos)
10. Sua URL aparecerá no topo: algo como `https://corretor-redacao.onrender.com`

---

## Usando no celular

1. Abra o navegador do celular (Chrome ou Safari)
2. Acesse a URL do Render
3. **Para adicionar à tela inicial:**
   - Android (Chrome): toque nos 3 pontinhos → "Adicionar à tela inicial"
   - iPhone (Safari): toque no botão de compartilhar → "Adicionar à Tela de Início"
4. O app vai aparecer como um ícone na tela inicial, igual a um app normal

---

## Formato do arquivo CSV de alunas

Crie um arquivo `.csv` com este formato (abra o Bloco de Notas e salve como `.csv`):

```
nome,telefone
Maria Silva,82999998888
João Santos,82988887777
Ana Lima,82977776666
```

- Não use acentos no cabeçalho (nome,telefone)
- O telefone deve ter DDD + número, sem espaços ou traços
- O app adiciona automaticamente o +55 do Brasil

---

## Aviso sobre o plano gratuito do Render

O plano gratuito "adormece" após 15 minutos sem uso.
Na primeira abertura depois de um período parado, o app pode demorar
30–50 segundos para responder — é normal. Depois disso funciona normalmente.

---

## Dúvidas?

Volte ao Claude Code e descreva o problema — posso ajudar a resolver.
