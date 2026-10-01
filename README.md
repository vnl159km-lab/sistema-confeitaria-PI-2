# Sistema de Vendas — PI 2

Aplicação web local para cadastro de produtos, PDV, fluxo de caixa, relatórios em PDF e controle de estoque.

**Versão atual:** `1.1.0`

Cada melhoria receberá um novo número de versão e será registrada em `CHANGELOG.md` antes de ser enviada ao GitHub.

## Atualização mais recente

### Versão 1.1.0 — Acessibilidade e venda por voz

Esta atualização aprimora a inclusão e a usabilidade do sistema:

- Adicionado botão de acessibilidade ♿ com modo de alto contraste.
- Layout adaptado para manter a organização em diferentes níveis de zoom.
- Navegação por teclado com destaque visual nos campos e botões.
- Inclusão de produtos no PDV por comando de voz, com suporte a quantidade falada ou numérica.

Consulte o [histórico completo de versões](CHANGELOG.md) para acompanhar a evolução do trabalho.

## Acessibilidade

- Botão ♿ com opção de alto contraste, salva para os próximos acessos.
- Layout responsivo para uso com zoom do navegador.
- PDV com reconhecimento de venda por voz em navegadores compatíveis, como o Google Chrome.

## Tecnologias

- Python
- Flask
- SQLite
- Bootstrap

## Executar localmente

```powershell
py -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt
.\venv\Scripts\python.exe app.py
```

Depois, acesse `http://127.0.0.1:5000`.

## Variáveis de ambiente

| Variável | Uso |
| --- | --- |
| `SECRET_KEY` | Chave de segurança da sessão Flask. Obrigatória em produção. |
| `DATABASE_PATH` | Caminho do banco SQLite. Em hospedagem, use um volume persistente. |
| `ADMIN_PASSWORD` | Senha administrativa do sistema. |
| `RESET_PASSWORD` | Senha do reset completo. |

## Hospedagem

O projeto está pronto para servidores Python com o comando:

```bash
gunicorn wsgi:app
```

Leia `DEPLOYMENT.md` antes de publicar: SQLite precisa de armazenamento persistente para não perder dados.
