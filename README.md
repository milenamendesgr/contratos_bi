# Contratos BI — dados fictícios

Dashboard em Python, Streamlit, Pandas e Plotly para analisar contratos, vigências, fornecedores, execução, medições, adiantamentos e fluxo financeiro.

**Todos os dados do modo padrão são sintéticos.** Não são amostras nem anonimizações de informações empresariais. A demonstração funciona sem senha ou API.

## Origem dos dados e segurança

**Na versão revisada, o modo `demo` não consulta fontes externas de dados de negócio.** A integração existe no código, mas somente é utilizada quando o processo é iniciado explicitamente em modo `api`. Não foi configurada nem acessada uma API real nesta revisão.

| Recurso | Modo `demo` (padrão) | Modo `api` (opcional) |
|---|---|---|
| Contratos, fornecedores, medições e indicadores | Gerados em `utils/demo_data.py` | Endpoint informado pelo administrador |
| `config/local_settings.py` | Não é importado | Importado se existir; é código Python confiável |
| Consultas SQL remotas | Bloqueadas por `run_sql()` | Enviadas ao endpoint configurado |
| Comentários | SQLite local `data/demo_comentarios.db` | SQLite configurável, padrão `data/contratos_comentarios.db` |
| Credenciais privadas | Não são necessárias | Configuração local ou variáveis de ambiente |

A pasta recebida não continha `config/local_settings.py`, `.env`, `.streamlit/secrets.toml`, bancos de dados ou histórico `.git`. Não foi encontrado endpoint empresarial fixo no código. Os SQLs preservam nomes de tabelas e regras da integração Protheus; eles não contêm os registros de um banco e não abrem uma conexão sozinhos.

O servidor escuta `127.0.0.1:8516`, com CORS e proteção XSRF habilitados. A coleta de estatísticas do Streamlit está desativada em `.streamlit/config.toml`. A instalação das dependências usa a rede e o índice configurado no pip. Os testes bloqueiam HTTP via Requests durante a navegação; não equivalem a uma captura de todo o tráfego do navegador, das dependências e do sistema operacional.

**Esta versão não tem autenticação nem autorização por usuário.** Use a demonstração localmente. Antes de disponibilizar dados reais para várias pessoas, implemente controle de acesso, permissões por filial/contrato e isolamento dos caches. O cache de dados é compartilhado pelo processo; filtros visuais não são controles de segurança. Veja o [relatório de revisão](docs/analise.md) para evidências e riscos restantes.

## Executar

Requer Python 3.10 ou superior.

```bash
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m streamlit run main.py
```

Os comandos acima são para Windows. Em Linux/macOS, use `.venv/bin/python` no lugar de `.venv\Scripts\python.exe`. Execute a partir da raiz do projeto para carregar `.streamlit/config.toml`. Não é necessário ativar o ambiente virtual.

Abra http://localhost:8516. No Windows, também é possível executar `instalar.bat` e depois `iniciar_contratos.bat`. Se a pasta veio de outra máquina, execute o instalador novamente para reparar o ambiente virtual.

`main.py` oferece o visual completo e dez módulos. `app.py` mantém uma interface alternativa simplificada.

## Dados demonstrativos

- 48 contratos, 12 fornecedores e quatro unidades fictícias.
- Contratos vigentes, vencidos, próximos do vencimento, paralisados e finalizados.
- Medições com itens, adiantamentos e parcelas vencidas e futuras.
- Filtros, gráficos, indicadores, detalhes e exportação de tabelas.
- Comentários versionados em SQLite separado da base privada.

O gerador `utils/demo_data.py` relaciona contratos, medições e itens. Valores e identificadores são reproduzíveis; datas acompanham o dia da execução. Documentos `DEMO-...` são identificadores fictícios, sem validade fiscal. O cache das consultas dura até 15 minutos.

## Organização

| Pasta | Responsabilidade |
|---|---|
| `modules/` | Telas e interação |
| `components/` | Filtros, tabelas, gráficos e cartões |
| `utils/` | Repositórios, cálculos e geração sintética |
| `config/` | Configuração e exemplo sem credenciais |
| `queries/` | Consultas para integração opcional e SQLite |
| `tests/` | Integridade, isolamento, navegação e comentários |

## Publicar no GitHub

Execute `python scripts/empacotar_publico.py`. Extraia `contratos_bi_publico.zip` em uma pasta nova para criar seu repositório público. O pacote seleciona os arquivos de código e documentação e exclui configurações privadas, bancos, ambientes virtuais, caches e histórico Git.

Não envie a pasta local inteira: ela pode conter `config/local_settings.py` e `data/contratos_comentarios.db`. O `.gitignore` não remove arquivos já presentes em um histórico Git. O pacote não inclui esse histórico. Gere novamente o ZIP após modificar o projeto.

Para apresentar no LinkedIn, mantenha o aviso de demonstração visível nos prints. Há um texto sugerido em `docs/linkedin.md`.

## Voltar a usar a API

O padrão é `CONTRATOS_DATA_MODE=demo`. Esse modo não importa `local_settings.py` e bloqueia SQL externo. Para conectar a aplicação ao ambiente privado:

1. Se `config/local_settings.py` já existe, edite esse arquivo. Caso contrário, copie `config/local_settings.example.py` para `config/local_settings.py`.

   No PowerShell, este comando copia somente se o arquivo ainda não existir:

   ```powershell
   if (-not (Test-Path config/local_settings.py)) {
       Copy-Item config/local_settings.example.py config/local_settings.py
   }
   ```
2. Configure o endpoint, as credenciais e as filiais reais:

```python
API_CONFIG = {
    "url": "https://api.example.invalid/consulta-sql",  # Substitua pelo endpoint autorizado.
    "user": "SEU_USUARIO",
    "password": "SUA_SENHA",
    "timeout": 120,
    "verify": True,
}

FILIAIS = {
    "0101": "Nome da matriz",
    "0102": "Nome da filial",
    # Complete com os códigos usados na sua empresa.
}
```

O mapa público contém apenas unidades fictícias. O mapeamento real deve ficar no arquivo privado. Mantenha `config/local_settings.py` fora do repositório público.

3. Encerre o dashboard, caso esteja rodando, com `Ctrl+C` no terminal que o iniciou.
4. No PowerShell, dentro da pasta do projeto, execute:

```powershell
$env:CONTRATOS_DATA_MODE = "api"
.venv\Scripts\python.exe -m streamlit run main.py
```

A variável vale para esse terminal e os processos iniciados por ele. Ao abrir outro terminal, defina-a novamente. Reinicie o processo sempre que trocar de modo para descartar os dados em cache e na sessão.

### Voltar aos dados fictícios

Encerre o aplicativo e execute no PowerShell:

```powershell
$env:CONTRATOS_DATA_MODE = "demo"
.venv\Scripts\python.exe -m streamlit run main.py
```

Não é necessário alterar o código das telas para trocar de modo.

### Compatibilidade da API e configurações

Esta integração espera um endpoint REST que receba consultas SQL e devolva os resultados. **Não basta informar o endereço de qualquer API TOTVS.** O endpoint, a autenticação, o formato da resposta e o esquema do banco precisam ser compatíveis. Para outros endpoints, pode ser necessário adaptar `utils/contratos_repository.py`, as consultas em `queries/` e o mapeamento dos campos recebidos. A integração real não foi validada com dados reais nesta versão demonstrativa.

As variáveis `CONTRATOS_API_URL`, `CONTRATOS_API_USER`, `CONTRATOS_API_PASSWORD`, `CONTRATOS_API_TIMEOUT` e `CONTRATOS_API_VERIFY` têm prioridade sobre o arquivo local. Se alterar o arquivo e o aplicativo continuar usando outra configuração, confira essas variáveis no terminal sem imprimir senhas. O projeto não carrega `.env` automaticamente. `CONTRATOS_API_TIMEOUT` é um inteiro em segundos, padrão `120`.

HTTPS e `verify=True` são obrigatórios. URLs com usuário/senha embutidos, parâmetros de consulta ou fragmento são recusadas. Redirecionamentos não são seguidos: informe o endereço final. A sessão HTTP não herda proxies, `.netrc` nem ajustes de certificados do ambiente (`trust_env=False`). Se sua infraestrutura exige proxy ou autoridade certificadora privada, adapte a sessão explicitamente com a equipe responsável, mantendo a validação TLS; não use `verify=False`.

### Contrato técnico da integração atual

O transporte fica em `utils/contratos_repository.py`, função `run_sql()`:

| Item | Formato implementado |
|---|---|
| Método HTTP | `GET` com corpo contendo SQL em UTF-8 |
| Cabeçalhos | `Content-Type: text/plain`, `Accept: application/json` |
| Autenticação | HTTP Basic quando usuário e senha estão preenchidos |
| Resposta de sucesso | Status `200`, JSON com lista de objetos |
| Envelopes reconhecidos | `rows`, `data`, `result`, `results`, `items`, `records` |
| Codificação | `charset` do servidor; legado sem charset usa `cp1252` |
| Erros | DataFrame vazio e mensagem resumida em `LAST_ERROR`, sem corpo da resposta |

Exemplo apenas estrutural de resposta (não é um contrato completo):

```json
{"rows": [{"FILIAL": "D001", "CONTRATO": "DEMO-0001", "VALOR_ATUAL": 1000.0}]}
```

`GET` com corpo é uma convenção desta integração, não um formato universal de API REST. O cliente não implementa paginação automática. Confirme método, autenticação, limites, paginação e codificação antes de usar dados reais. Configure o serviço remoto com acesso somente de leitura às tabelas autorizadas; `run_sql()` não é um mecanismo de autorização SQL.

### Como adaptar o código para outra API

1. **Obtenha o contrato da API:** endpoint, método, autenticação, exemplo de JSON, campos e paginação. Use homologação com registros de teste.
2. **Adapte o transporte:** se o serviço recebe SQL via `POST`, altere `session.get(...)` em `run_sql()` para o método e o corpo exigidos. Por exemplo, uma API que espera `{"sql": "..."}` exige `json={"sql": sql}` no lugar de `data=...` e `Content-Type: application/json`. Só faça essa mudança se estiver documentada pelo servidor.
3. **Para API de recursos (`/contratos`, `/medicoes`, etc.):** crie funções de consulta por recurso em `utils/contratos_repository.py`. Substitua, no ramo API dos métodos `get_*`, a leitura/execução de SQL pelas novas funções. Preserve o retorno de demonstração antes de qualquer chamada HTTP. Implemente a paginação da API e não aceite URLs arbitrárias de próxima página sem validar o destino.
4. **Mapeie os campos:** transforme o JSON em `pd.DataFrame`, renomeie as colunas para os nomes usados pelos serviços em `utils/*_service.py` e preserve identificadores como texto, inclusive zeros à esquerda. Ajuste datas, moeda, status e chaves compostas. Os aliases de `queries/*.sql` e as bases de `utils/demo_data.py` mostram os campos esperados.
5. **Revise todos os caminhos:** além dos métodos `get_*`, `modules/alertas.py` e `modules/itens_planilhas.py` chamam `run_sql()` diretamente no modo API. Adapte esses caminhos também. Medições consultam cabeçalho e itens separadamente e relacionam `FILIAL`, `CONTRATO`, `REVISAO_CONTRATO` e `NUMERO_MEDICAO`.
6. **Valide antes da produção:** teste respostas vazias, campos ausentes, erros de autenticação, paginação e certificados. Compare totais com a fonte autorizada. Use respostas simuladas nos testes e não grave dados reais em fixtures, logs ou no Git. Reinicie o processo após mudar configuração ou modo.

As telas podem continuar consumindo os mesmos DataFrames. Se mudar os nomes internos das colunas, será necessário ajustar os serviços e os módulos que os utilizam.

### Diagnóstico rápido

| Sintoma | O que conferir |
|---|---|
| Continua mostrando dados fictícios | Defina `CONTRATOS_DATA_MODE=api` no mesmo terminal que inicia o processo e reinicie |
| URL não configurada | Preencha o arquivo privado ou `CONTRATOS_API_URL` |
| Configuração HTTPS recusada | Use URL final HTTPS, sem credenciais/parâmetros/fragmento, e `verify=True` |
| HTTP 301/302 | Configure diretamente o endereço final, pois redirects são bloqueados |
| HTTP 401/403 | Confira credenciais e permissões no servidor, sem publicar os segredos |
| Falha de conexão/certificado | Confira disponibilidade, cadeia de certificados e necessidades de proxy |
| Consulta vazia | Verifique o JSON e os aliases; erro de integração também retorna tabela vazia |
| Caracteres incorretos | Faça a API declarar `charset=utf-8` ou adapte a decodificação ao contrato real |

### Banco de comentários

No modo demo, comentários usam exclusivamente `data/demo_comentarios.db`, ignorando `CONTRATOS_SQLITE_PATH`. No modo API, o padrão é `data/contratos_comentarios.db`; `CONTRATOS_SQLITE_PATH` permite configurar outro caminho. Os comentários não são transferidos automaticamente entre os bancos. Comentários digitados na demonstração são persistidos localmente; não inclua informações reais.

## Testes

```bash
.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Os testes da demonstração exigem modo `demo`, verificam vínculos e totais, bloqueiam HTTP e percorrem os menus de ambas as entradas usando Streamlit AppTest. Veja `docs/analise.md` para o escopo e as limitações da revisão.

No PowerShell, defina `$env:CONTRATOS_DATA_MODE = "demo"` antes dos testes. `tests/test_security.py` também verifica o bloqueio de configurações HTTP/TLS inseguras, redirects desativados, ausência de detalhes sensíveis nos erros e isolamento de configuração privada. Nenhum teste exige acesso a uma API empresarial.
