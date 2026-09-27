# Revisão para demonstração pública — histórico

A aplicação separa telas, componentes visuais, regras de negócio e acesso a dados. A maioria das telas utiliza `utils/contratos_repository.py`; Alertas e Itens e Planilhas também possuíam consultas diretas. Esses caminhos receberam suporte à demonstração. O gerador legado foi adaptado para consumir a mesma carteira.

O gerador antigo sozinho não atendia às telas atuais: fornecia colunas de importação e não relacionava contratos a medições, adiantamentos e fornecedores. A nova base gera esses relacionamentos e deriva saldos e execução dos valores medidos. Datas relativas mantêm os cenários de vencimento ao longo do tempo.

Foram removidos dos arquivos públicos o nome empresarial, o endpoint padrão e o mapa de unidades original. Na cópia inspecionada em 27/09/2026 não havia configuração privada nem banco original. O modo demonstrativo não importa configurações privadas e bloqueia SQL externo. Comentários demonstrativos usam outro banco.

A interface principal disponibiliza também Execução Contratual, Financeiro, Fornecedores e Itens e Planilhas, que estavam ocultos no menu. A tabela de detalhes converte seus valores heterogêneos para texto antes da apresentação, evitando erros de serialização Arrow.

## Verificação e limites

- Testes de vínculos, unicidade, conciliação entre carteira, medições e itens, e geração reproduzível.
- Carregamento dos repositórios e navegação dos dez módulos nas duas entradas com HTTP bloqueado.
- Testes existentes de persistência, versionamento e serviço de comentários.
- Integração real e resultados SQL não verificados, pois não há acesso aos dados reais.
- Chamadas `use_container_width` geram avisos de descontinuação na versão instalada; não impediram a navegação testada.
- Não há autenticação de usuários na interface de comentários. Esta versão é uma demonstração, não uma implantação corporativa com controle de acesso.
- O histórico Git não foi auditado. O pacote contém somente arquivos atuais selecionados, sem `.git`.

As consultas originais permanecem como exemplo de integração. Os indicadores são cenários demonstrativos; não representam desempenho de nenhuma empresa.

## Revisão de segurança em 27/09/2026

Escopo: arquivos Python, consultas SQL, configuração Streamlit, instaladores, empacotador e testes disponíveis nesta pasta. Não foi acessado endpoint empresarial nem consultado banco externo.

### Conclusão sobre fontes externas

O modo padrão `demo` gera a carteira de negócio localmente, não importa `config/local_settings.py` e bloqueia `run_sql()`. As telas atuais de `main.py` e `app.py` funcionaram com HTTP via Requests bloqueado. Há código de integração externa opcional: portanto, não seria correto afirmar que o projeto não possui nenhuma capacidade de conexão.

Na inspeção inicial, esta cópia não continha `config/local_settings.py`, `.env`, `.streamlit/secrets.toml`, arquivos de banco ou diretório `.git`. Não foram encontrados endereço empresarial ou credenciais reais embutidos nos arquivos inspecionados.

| Origem/destino | Evidência e alcance |
|---|---|
| Dados fictícios | `utils/demo_data.py` calcula 48 contratos e seus relacionamentos sem ler arquivos de dados nem chamar rede |
| Dados via API | Único transporte HTTP de negócio encontrado: `run_sql()` em `utils/contratos_repository.py`; exige modo API e URL configurada |
| SQLs | Referências a tabelas Protheus, como `CN9010`, `CND010` e `CNE010`, e funções do dialeto Oracle; não são cópias dos registros |
| Comentários | SQLite local separado por modo; os valores são enviados às consultas por parâmetros |
| Importação legada | `utils/data_loader.py` lê Excel/CSV fornecido ao módulo legado `lista_contratos.py`, fora dos menus atuais; não busca arquivos empresariais automaticamente |
| Exportações | CSV e Excel entregues ao usuário pelo dashboard; não há upload externo implementado nesses caminhos |
| Estatísticas | `gatherUsageStats=false` no arquivo Streamlit do projeto |
| Instalação | pip acessa o índice de pacotes configurado no ambiente |

Os comentários podem conter qualquer texto digitado pelo usuário; não se pode chamar esse conteúdo de sintético. O banco demo fica fora do pacote público. A exclusão de comentário é lógica e preserva seu histórico.

### Correções realizadas nesta revisão

- A API agora recusa HTTP e validação TLS desativada antes de enviar SQL ou credenciais.
- URLs com credenciais embutidas, query string ou fragmento são recusadas.
- Redirecionamentos foram desativados para impedir encaminhamento automático das consultas a outro endereço.
- A sessão Requests usa `trust_env=False`: não herda proxy, autenticação `.netrc` ou configuração de certificados do ambiente.
- Mensagens da API não exibem corpo de resposta ou texto bruto de exceções, que poderiam conter dados, endereços ou segredos.
- README ampliado com origem dos dados, configuração por modo, contrato HTTP, pontos de adaptação e diagnóstico.

Essas mudanças podem exigir ajuste em integrações antigas que dependiam de HTTP, redirect, proxy ou certificados configurados por variável de ambiente. HTTPS com certificado válido continua obrigatório; a URL final e o transporte devem ser configurados explicitamente.

### Riscos e limitações restantes

| Prioridade no uso com dados reais | Achado | Tratamento necessário |
|---|---|---|
| Alta | Não há login, autorização por registro ou identidade verificável nos comentários | Implementar autenticação e autorização antes de acesso compartilhado; manter a demonstração em loopback |
| Alta | `st.cache_data` compartilha dados no processo; filtros não restringem permissões | Definir isolamento por usuário/organização e autorização na fonte |
| Alta | Endpoint aceita SQL; cliente não garante operações somente de leitura | Restringir credencial e operações no servidor; revisar consultas e permissões |
| Média | CSV/Excel não neutralizam textos iniciados como fórmulas | Tratar células e cabeçalhos não confiáveis antes de exportar para planilhas |
| Média | Há HTML dinâmico sem escape em caminhos legados, como nome do arquivo em `lista_contratos.py` | Escapar valores externos antes de habilitar esses caminhos com dados não confiáveis; não foi demonstrada execução de script |
| Média | Parser tolerante pode descartar registros inválidos e falhas retornam DataFrame vazio | Validar esquema, paginação e integridade; distinguir falha de integração de ausência de dados |
| Média | SQLite e arquivos privados não têm criptografia implementada pelo projeto | Proteger permissões de arquivos, backups e disco conforme o ambiente |
| A validar | Dependências têm faixas de versão, sem lockfile ou auditoria de vulnerabilidades executada | Fixar ambiente validado e executar auditoria de dependências antes da implantação |

O arquivo `local_settings.py` é código Python executável e só deve ser editado por administradores confiáveis. O modo API permite consultar o destino que esse administrador configurar; não há allowlist corporativa no cliente. O servidor remoto pode, por sua vez, consultar outras fontes, algo que não é verificável nesta pasta.

### Validação executada

Comando: `python -m unittest discover -s tests -v`, com `CONTRATOS_DATA_MODE=demo`.

Resultado: **14 testes aprovados**. Incluem integridade e conciliação dos dados sintéticos, carregamento dos repositórios, navegação dos menus de ambas as entradas com Requests bloqueado, comentários/versionamento e três testes novos de segurança. As chamadas do modo API foram simuladas, inclusive resposta válida, redirect e falha de conexão. Não houve teste contra uma API real.

Ambiente disponível: Python 3.13.0, Streamlit 1.57.0, Requests 2.32.5 e Pandas 3.0.2. **O Pandas instalado está fora de `pandas>=2.2,<3` declarado em `requirements.txt`**; o resultado não substitui uma execução em ambiente virtual instalado com os requisitos declarados. Não alteramos o Python global. A tentativa inicial no sandbox falhou por acesso à pasta temporária do Windows; a execução autorizada fora do sandbox passou. Houve avisos de descontinuação de `use_container_width`.

Não foram feitos pentest, captura de tráfego do navegador, auditoria de dependências/transitivas, inspeção do sistema operacional ou verificação do banco/servidor remoto. Nenhuma revisão estática ou suíte finita garante ausência absoluta de vulnerabilidades. A evidência sustenta o isolamento das fontes de negócio nos caminhos demo revisados, com o código e a configuração atuais.

### Distribuição

`scripts/empacotar_publico.py` seleciona código e documentação, excluindo bancos, configuração privada, ambientes virtuais e histórico Git. Ele não detecta segredos que alguém venha a escrever dentro dos arquivos selecionados. Revise alterações antes de publicar; `.gitignore` também não remove segredos já versionados.
