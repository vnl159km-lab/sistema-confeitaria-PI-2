# Publicação no Render

## Configuração incluída

O arquivo `render.yaml` cria um serviço web Python no plano gratuito do Render, instalado a partir do GitHub e iniciado com:

```bash
gunicorn wsgi:app
```

O Render acompanha a branch `main`: cada atualização enviada ao GitHub gera uma nova publicação.

## Publicar pelo painel

1. Acesse [dashboard.render.com](https://dashboard.render.com/) e entre com sua conta GitHub.
2. Abra **New** → **Blueprint** e selecione o repositório `sistema-confeitaria-PI-2`.
3. Confirme a criação usando o arquivo `render.yaml`.
4. Informe uma senha forte para `ADMIN_PASSWORD` e outra para `RESET_PASSWORD`.
5. Clique em **Apply** e aguarde a publicação terminar.

O Render fornecerá um endereço com final `.onrender.com`. Teste-o acessando `/health` ao final do endereço.

## Banco de dados SQLite temporário

Esta configuração foi criada para usar SQLite sem disco persistente, conforme escolhido. Isso permite testar e publicar gratuitamente, mas produtos, vendas, estoque e financeiro podem ser apagados quando o Render reiniciar ou publicar uma atualização.

Não configure `DATABASE_PATH` no Render enquanto estiver usando esta modalidade temporária.

## Domínio próprio

Depois que o endereço `.onrender.com` estiver funcionando:

1. Abra o serviço no Render e acesse **Settings** → **Custom Domains**.
2. Clique em **Add Custom Domain** e informe seu domínio.
3. Copie para o provedor do domínio os registros DNS mostrados pelo Render.
4. Volte ao Render e aguarde a verificação.

O certificado HTTPS é criado automaticamente após a verificação do domínio.

## Voz neural Azure

Para ativar a voz neural no Render, adicione manualmente no menu **Environment** as variáveis `AZURE_SPEECH_KEY` e `AZURE_SPEECH_REGION`. Nunca coloque essas chaves no GitHub.
