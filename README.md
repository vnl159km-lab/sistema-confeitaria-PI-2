# Sistema de Vendas — PI 2

Aplicação web local para cadastro de produtos, PDV, fluxo de caixa, relatórios em PDF e controle de estoque.

**Versão atual:** `1.4.0`

Cada melhoria receberá um novo número de versão e será registrada em `CHANGELOG.md` antes de ser enviada ao GitHub.

## Atualização mais recente

### Versão 1.4.0 — Preparação para hospedagem no Render

Esta atualização prepara o sistema para publicação pública pelo Render, integrado ao GitHub:

- Adicionado o arquivo `render.yaml` para criar o serviço web automaticamente.
- Senhas administrativas solicitadas com segurança no painel do Render.
- Publicação automática a cada atualização enviada para a branch `main`.
- Mantido o SQLite temporário, conforme escolhido, para testar no plano gratuito.

Consulte o [histórico completo de versões](CHANGELOG.md) para acompanhar a evolução do trabalho.

## Atualizações do trabalho

O projeto está em evolução contínua e utiliza o GitHub como controle de versão. Cada melhoria é registrada com uma descrição clara e enviada ao repositório, permitindo acompanhar o desenvolvimento do sistema ao longo do tempo.

**Último marco:** preparação para hospedagem no Render com integração ao GitHub.

## Linha do tempo de versões

| Versão | Data | Atualização |
| --- | --- | --- |
| `1.0.0` | 10/09/2026 | Lançamento inicial com produtos, PDV, estoque, fluxo de caixa e relatórios. |
| `1.1.0` | 22/09/2026 | Inclusão de acessibilidade, alto contraste e adaptação ao zoom. |
| `1.2.0` | 30/09/2026 | Leitura em voz alta dos itens, forma de pagamento e valor no fechamento da venda. |
| `1.3.0` | 30/09/2026 | Integração preparada para voz neural natural da Azure, diretamente pelo sistema. |
| `1.4.0` | 20/10/2026 | Configuração para publicação automática no Render via GitHub, usando SQLite temporário. |

As novas versões serão adicionadas ao final desta tabela, mantendo a evolução cronológica do sistema.

## Acessibilidade

- Botão ♿ com opção de alto contraste, salva para os próximos acessos.
- Layout responsivo para uso com zoom do navegador.
- PDV com leitura em voz alta do resumo da venda em navegadores compatíveis.

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
| `AZURE_SPEECH_KEY` | Chave do recurso Azure Speech para a voz neural. |
| `AZURE_SPEECH_REGION` | Região do recurso Azure Speech, por exemplo: `brazilsouth`. |
| `AZURE_SPEECH_VOICE` | Voz neural usada pelo sistema. Padrão: `pt-BR-FranciscaNeural`. |

## Voz neural integrada

Para usar a voz natural diretamente pelo sistema, crie um recurso **Speech** na Azure e configure `AZURE_SPEECH_KEY` e `AZURE_SPEECH_REGION` no computador ou na hospedagem. A chave fica somente no servidor e nunca é enviada ao navegador.

Enquanto a Azure não estiver configurada, o sistema usa automaticamente a voz padrão disponível no navegador.

No PowerShell, após criar o recurso Azure Speech, configure os dados sem enviar a chave para o GitHub:

```powershell
setx AZURE_SPEECH_KEY "SUA_CHAVE_AZURE"
setx AZURE_SPEECH_REGION "brazilsouth"
```

Feche o terminal, abra novamente e reinicie o sistema. A voz padrão é `pt-BR-FranciscaNeural`; para trocar a voz, configure também `AZURE_SPEECH_VOICE`.

## Hospedagem

O projeto está preparado para publicar no Render pelo arquivo `render.yaml`. Leia `DEPLOYMENT.md` antes de criar o serviço: nesta configuração, o SQLite é temporário e pode perder dados em reinicializações ou novas publicações.
