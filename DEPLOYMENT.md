# Guia de hospedagem

## Antes de publicar

Este sistema usa SQLite. Em hospedagem, o banco deve estar em um disco persistente; caso contrário, produtos, vendas e caixa podem ser apagados durante reinicializações ou novas publicações.

Defina no painel da hospedagem:

```text
SECRET_KEY=uma-chave-longa-e-secreta
ADMIN_PASSWORD=uma-senha-administrativa-forte
RESET_PASSWORD=uma-senha-de-reset-forte
DATABASE_PATH=/caminho-persistente/confeitaria.db
```

## Comando de inicialização

```bash
gunicorn wsgi:app
```

## Teste de saúde

Após publicar, acesse:

```text
https://seu-dominio/health
```

A resposta esperada é:

```json
{"status":"ok"}
```

## Recomendação para produção

Para vários usuários simultâneos ou maior segurança, migre de SQLite para PostgreSQL antes de disponibilizar o sistema comercialmente na internet.
