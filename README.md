# Observatório SQL

**Análise e otimização de consultas SQL com estatísticas de execução.**

Projeto de TCC de Arthur Meira, do curso de Ciência da Computação da Unesc,
sob orientação de Marcel Campos Inocencio.

O protótipo permite investigar consultas PostgreSQL, gerar sugestões por regras
e comparar os resultados e os tempos das versões original e alternativa.
A interface web funciona localmente em **http://127.0.0.1:8767**.

## Conteúdo

- [Instalação e configuração](#instalação-e-configuração)
- [Bancos de dados e backups](#bancos-de-dados-e-backups)
- [Utilização, testes e experimentos](#utilização-testes-e-experimentos)

## Funcionalidades

- Coleta manual de estatísticas do PostgreSQL: chamadas, tempos, linhas e blocos.
- Organização das consultas por tempo, frequência e data.
- Investigação de planos de execução e identificação de possíveis gargalos.
- Sugestões de reescrita SQL e recomendações de índices, com condições explícitas.
- Verificação dos resultados antes de comparar o desempenho das versões.
- Medições reais, com aquecimento, repetições, média, mediana e dispersão.
- Histórico persistente e exportação de avaliações em JSON e resumos em CSV.

As alternativas são construídas a partir da estrutura do SQL recebido.
O sistema não cria índices automaticamente.
Uma sugestão pode não melhorar o desempenho; a medição determina o resultado.

## Tecnologias e pré-requisitos

| Tecnologia | Uso / requisito |
|---|---|
| Python | Preferencialmente 3.14, 64 bits; o gerador requer pelo menos 3.12. |
| PostgreSQL 18 | Banco experimental; ambiente validado com a versão 18.6. |
| `pg_stat_statements` | Estatísticas agregadas das consultas. |
| SQLite | Histórico local; incluído no Python, sem servidor separado. |
| Psycopg, python-dotenv | Conexão PostgreSQL e configuração. |
| pglast, sqlglot | Análise sintática e regras de transformação SQL. |
| HTML, CSS e JavaScript | Interface servida pelo próprio Python. |
| Git e navegador | Clone do projeto e acesso à interface. |

Reserve pelo menos **2 GiB livres** para o pacote, banco restaurado e temporários.
DBeaver é opcional. Não são necessários Node.js, npm, Flask ou Django.

As versões verificadas estão em [requirements-reproduction.txt](requirements-reproduction.txt).
Os requisitos, permissões e detalhes por sistema estão no [guia de instalação](#instalação-e-configuração).

## Instalação e configuração

Siga este guia primeiro; depois restaure os bancos e inicie a interface. Todos os caminhos de comandos são relativos à raiz do clone.

### 1. Preparar a máquina

| Pré-requisito | Orientação |
|---|---|
| Python | Preferencialmente 3.14 de 64 bits (ambiente validado: 3.14.7). O gerador exige pelo menos 3.12 por utilizar `itertools.batched`. |
| PostgreSQL | Versão 18, preferencialmente 18.6, incluindo `psql`, `pg_dump`, `pg_restore` e `pg_stat_statements`. |
| Git | Para clonar o repositório. |
| Navegador | Navegador atual com JavaScript. |
| Espaço | Reserve pelo menos 2 GiB livres para pacote, restauração e temporários; mais para múltiplas cópias. |
| DBeaver | Opcional; `psql` também atende ao roteiro. |
| SQLite | Incluído no Python; não precisa de servidor separado. |

Dependências Python: Psycopg 3, python-dotenv, pglast e sqlglot. O servidor HTTP utiliza a biblioteca padrão e o frontend é HTML/CSS/JavaScript. **Não é necessário instalar Node.js, npm, Flask ou Django.**

`requirements.txt` é a lista principal. `requirements-reproduction.txt` fixa as versões efetivamente instaladas na validação de 08/11/2026. Os comandos Linux não foram validados em outra máquina.

Instale o Git antes de clonar: no Windows, use o [instalador oficial do Git](https://git-scm.com/downloads/win) e reabra o terminal; no Debian/Ubuntu, execute `sudo apt update` e `sudo apt install git`. Confira com `git --version`. Para o roteiro Linux, use uma distribuição com Python 3.12+ disponível, como Ubuntu 24.04+ ou Debian 13.

### 2. Clonar e preparar Python

Execute os comandos na raiz do repositório. Se o GitHub exigir autenticação, o avaliador precisa ter acesso ao projeto.

```sh
git clone https://github.com/arthurmeira/TCC.git
cd TCC
```

#### Windows — PowerShell

Instale Python 3.14 pelo [site oficial](https://www.python.org/downloads/windows/), incluindo o launcher `py`.

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements-reproduction.txt
.\.venv\Scripts\python.exe -m pip check
```

Esses comandos não exigem ativar o ambiente nem mudar a política de execução do PowerShell.

#### Linux — Debian/Ubuntu

Instale Python 3.12 ou superior e o pacote de `venv` da mesma versão. Em uma distribuição cujo Python padrão já atende ao requisito:

```bash
sudo apt update
sudo apt install git python3 python3-venv unzip
python3 --version
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements-reproduction.txt
.venv/bin/python -m pip check
```

Se o Python padrão for anterior a 3.12, instale uma versão compatível antes de criar o ambiente. Prefira arquitetura de 64 bits com wheels disponíveis para as dependências. Para instalar pelas faixas de versões do projeto, substitua o arquivo de reprodução por `requirements.txt`.

Nas próximas seções, `python` significa o Python da `.venv`. No Windows, substitua por `.\.venv\Scripts\python.exe`; no Linux, por `.venv/bin/python`, ou ative com `source .venv/bin/activate`.

### 3. Instalar e configurar PostgreSQL

#### Windows

Use o [instalador indicado pelo PostgreSQL](https://www.postgresql.org/download/windows/), versão 18, incluindo as ferramentas de linha de comando. Defina uma senha local para `postgres` e anote a porta (normalmente 5432).

No PowerShell:

```powershell
$env:Path = "C:\Program Files\PostgreSQL\18\bin;" + $env:Path
psql --version
pg_dump --version
pg_restore --version
psql -h localhost -p 5432 -U postgres -d postgres -W
```

#### Linux — Debian/Ubuntu

Em uma versão suportada de Debian/Ubuntu, configure o repositório PGDG com o procedimento oficial abaixo. O segundo comando solicita confirmação para adicionar a fonte de pacotes; leia e confirme as instruções exibidas. Fontes: [Ubuntu](https://www.postgresql.org/download/linux/ubuntu/) e [Debian](https://www.postgresql.org/download/linux/debian/).

```bash
sudo apt update
sudo apt install postgresql-common ca-certificates
sudo /usr/share/postgresql-common/pgdg/apt.postgresql.org.sh
sudo apt update
sudo apt install postgresql-18 postgresql-client-18
sudo systemctl enable --now postgresql
sudo -u postgres psql -d postgres
```

No `psql`, defina a senha interativamente, sem registrá-la em scripts:

```text
\password postgres
```

#### Habilitar pg_stat_statements — ambos os sistemas

No `psql`, conectado ao banco administrativo `postgres`:

```sql
SHOW config_file;
SHOW shared_preload_libraries;
SELECT name, default_version FROM pg_available_extensions WHERE name='pg_stat_statements';
```

Se a extensão não estiver disponível, instale os módulos adicionais/contrib da versão 18 segundo a distribuição. Edite o `postgresql.conf` indicado por `SHOW config_file`:

```ini
shared_preload_libraries = 'pg_stat_statements'
compute_query_id = auto
pg_stat_statements.track = top
```

Se já houver bibliotecas em `shared_preload_libraries`, acrescente `pg_stat_statements` à lista, preservando as outras. **Reinicie o serviço**: recarregar a configuração não basta para carregar o módulo.

- Windows: abra **Serviços**, localize o serviço da instalação PostgreSQL e reinicie-o.
- Linux: `sudo systemctl restart postgresql`, ou o serviço/cluster específico da instalação.

O roteiro usa `postgres` em uma instalação local de avaliação, com permissão para criar banco/extensão e acessar as métricas. Não exponha o banco ou a aplicação à Internet. Uma conta não administrativa precisa das permissões de leitura correspondentes; para observar textos de SQL de outros usuários, o administrador pode conceder `pg_read_all_stats`. O sistema não concede permissões automaticamente.

O roteiro principal **não requer logging_collector**. Os módulos opcionais de captura de log exigem `logging_collector=on`, saída `stderr`, nome terminado em `.log`, reinício do serviço e autorização para ler logs e ajustar parâmetros da sessão. A captura utiliza `log_min_duration_statement=0` somente na própria sessão. Ela não é necessária para restaurar ou consultar os experimentos existentes.

Referência: [pg_stat_statements — PostgreSQL 18](https://www.postgresql.org/docs/18/pgstatstatements.html).

### 4. Configurar a conexão

Crie `.env` apenas se ainda não existir.

Windows:

```powershell
if (-not (Test-Path -LiteralPath .env)) { Copy-Item -LiteralPath .env.example -Destination .env }
```

Linux:

```bash
test -e .env || cp .env.example .env
chmod 600 .env
```

Edite localmente:

```dotenv
DB_HOST=localhost
DB_PORT=5432
DB_NAME=tcc_sql_optimizer_logs
DB_USER=postgres
DB_PASSWORD=preencha_com_sua_senha
DB_CONNECT_TIMEOUT=10
```

Use a senha da **sua instalação**. Não existe senha do autor no pacote. Utilize aspas conforme a sintaxe dotenv se houver espaços/caracteres especiais. `.env` é ignorado pelo Git e não integra os backups distribuídos.

**O código exige o nome `tcc_sql_optimizer_logs`.** Alterar apenas o `.env` para outro nome não funciona. Se esse banco já existir, use outra instância/porta PostgreSQL e ajuste `DB_PORT`; não apague nem sobrescreva o banco existente. Variáveis já definidas no ambiente do terminal têm prioridade sobre `.env`.

### 5. Conferir e prosseguir

Saia do `psql` com `\q` para voltar ao terminal. Para editar `postgresql.conf`, abra o caminho retornado por `SHOW config_file` em um editor com permissão administrativa. No Linux, por exemplo, use `sudo nano` seguido desse caminho. Salve antes de reiniciar.

Confirme que `psql --version` e `pg_restore --version` apontam para a versão 18. Não inicie a aplicação antes de restaurar o SQLite, pois a aplicação pode criar um histórico vazio que o restaurador se recusará a sobrescrever.

**Próxima etapa:** [restaurar PostgreSQL e SQLite](#bancos-de-dados-e-backups). O restaurador cria o banco e restaura os objetos da extensão; não execute `CREATE DATABASE` nem `schema.sql` no caminho recomendado.

### Problemas de instalação

| Sintoma | Solução |
|---|---|
| `No module named ...` | Execute na raiz com o Python da `.venv` e instale as dependências. |
| Falha em `itertools.batched` | Atualize para Python 3.12+ e recrie a `.venv`. |
| Binários PostgreSQL ausentes | Informe `--pg-bin` ou configure PATH para a versão 18. |
| Conexão recusada | Confira serviço, host e porta; execute `python -m src.database`. |
| Autenticação falha | Confira senha local e regras TCP de `pg_hba.conf`; o pacote não contém credenciais. |
| Configurações ausentes | Preencha `.env`; confira variáveis antigas no ambiente do terminal. |
| Nome do banco inválido | Use `tcc_sql_optimizer_logs`; para evitar conflito, mude instância/porta. |
| Extensão não carregada | Configure `shared_preload_libraries`, reinicie e confirme a extensão no banco. |

## Bancos de dados e backups

**Antes de começar:** conclua [a instalação e o arquivo `.env`](#instalação-e-configuração). Execute os comandos na raiz do clone. `python` significa o executável da `.venv`: `.\.venv\Scripts\python.exe` no Windows ou `.venv/bin/python` no Linux.

O PostgreSQL guarda os dados comerciais sintéticos e a extensão de estatísticas. O SQLite ativo é `results/logs.sqlite3` e guarda as avaliações e snapshots. Restaure ambos para consultar o experimento completo. A configuração de host, porta e credenciais está no [guia de instalação](#instalação-e-configuração).

### 1. Restaurar dados e histórico — recomendado

#### Arquivos do pacote

| Arquivo | Conteúdo |
|---|---|
| `postgresql.dump` | Dump custom do banco inteiro: cinco tabelas, dados, índices, constraints, sequências e objetos de extensão. |
| `logs.sqlite3` | Histórico das avaliações e snapshots das estatísticas. |
| `rodada_12_consultas_20261107.json` | Amostras e métricas dos 12 casos do artigo. |
| `manifest.json` | Tamanhos, SHA-256, contagens e inventário das estruturas. |
| `postgresql.toc.txt` | Conteúdo listado por `pg_restore --list`. |
| `verification_*.json` | Registro da restauração integral testada. |

O dump gerado em 08/11/2026 tem 62.598.050 bytes (59,70 MiB); o SQLite tem 10.948.608 bytes (10,44 MiB). O banco PostgreSQL de origem ocupa aproximadamente 434 MiB. O espaço após restauração pode variar.

#### Download e integridade

Obtenha `tcc-dados-2026-11-08.zip` e coloque-o na raiz do clone. Compare seu SHA-256 com [backups/SHA256SUMS.txt](backups/SHA256SUMS.txt).

Windows:

```powershell
Get-FileHash -Algorithm SHA256 -LiteralPath .\tcc-dados-2026-11-08.zip
## Compare o hash antes de extrair.
if (Test-Path -LiteralPath .\backups\2026-11-08) { throw 'Destino já existe; use um clone novo.' }
Expand-Archive -LiteralPath .\tcc-dados-2026-11-08.zip -DestinationPath .\backups
```

Linux:

```bash
sha256sum tcc-dados-2026-11-08.zip
## Compare o hash. O ZIP contém a pasta 2026-11-08/.
test ! -e backups/2026-11-08 && unzip -n tcc-dados-2026-11-08.zip -d backups
```

#### Restauração protegida dos dois bancos

Encerre a aplicação. **Não crie o banco nem execute `sql/schema.sql` antes deste comando.** O restaurador cria um banco novo e recusa banco ou histórico que seriam sobrescritos.

Windows:

```powershell
.\.venv\Scripts\python.exe -m scripts.backup_databases restore --bundle backups/2026-11-08 --pg-bin "C:\Program Files\PostgreSQL\18\bin"
if ($LASTEXITCODE -ne 0) { throw 'Restauração não concluída; consulte a mensagem antes de continuar.' }
.\.venv\Scripts\python.exe -m src.database
```

Linux:

```bash
.venv/bin/python -m scripts.backup_databases restore --bundle backups/2026-11-08 --pg-bin /usr/lib/postgresql/18/bin
## Continue somente se o comando anterior terminar sem erro.
.venv/bin/python -m src.database
```

O utilitário verifica hashes, cria o banco UTF-8 a partir de `template0`, chama `pg_restore --exit-on-error --single-transaction --no-owner --no-privileges`, compara os dados/estruturas, executa `ANALYZE` e instala o SQLite em `results/logs.sqlite3`. A senha é passada ao processo pelo ambiente, não pelos argumentos ou por arquivo publicado. Em falha posterior à criação, o banco novo permanece para diagnóstico; o script não o apaga nem restaura novamente sobre ele.

O backup não inclui contas/senhas do servidor, `postgresql.conf`, `pg_hba.conf` ou contadores ativos de `pg_stat_statements`. Os objetos passam a pertencer à conta restauradora; ACLs específicas da origem não são transportadas. A extensão deve estar disponível no servidor de destino, e a verificação estrita também compara sua versão com a do manifesto.

A origem utiliza locale Windows `Portuguese_Brazil.1252`, não portátil para Linux. O restaurador utiliza o locale padrão do cluster de destino. Os dados são preservados, mas ordenações textuais, comparações, planos e tempos podem mudar entre ambientes.

#### Validar a restauração

```sh
psql -h localhost -p 5432 -U postgres -d tcc_sql_optimizer_logs -W -v ON_ERROR_STOP=1 -f sql/validate_population.sql
```

| Tabela | Registros |
|---|---:|
| clientes | 100.000 |
| produtos | 50.000 |
| pedidos | 1.000.000 |
| itens_pedido | 2.498.714 |
| pagamentos | 1.000.000 |
| **Total** | **4.648.714** |

Os cinco indicadores de inconsistência da segunda consulta devem ser zero. O SQLite do pacote contém **14 avaliações, 9 sincronizações, 66 consultas observadas e 568 snapshots**. As tabelas `imports` e `events` estão vazias neste pacote; não há lotes de arquivos de log a recuperar.

Na conexão restaurada, confira:

```sql
SHOW shared_preload_libraries;
SHOW compute_query_id;
SHOW pg_stat_statements.track;
SELECT extname,extversion FROM pg_extension WHERE extname='pg_stat_statements';
SELECT count(*) FROM public.pg_stat_statements;
```

#### Alternativa manual com pg_restore

Em uma instância sem o banco de destino, execute `createdb -h localhost -p 5432 -U postgres -W -T template0 -E UTF8 tcc_sql_optimizer_logs`. **Somente se a criação terminar com sucesso**, execute:

```sh
pg_restore -h localhost -p 5432 -U postgres -W --exit-on-error --single-transaction --no-owner --no-privileges -d tcc_sql_optimizer_logs backups/2026-11-08/postgresql.dump
```

Não use `--clean`. Conecte-se com `psql -h localhost -p 5432 -U postgres -d tcc_sql_optimizer_logs -W`, execute `ANALYZE;` e saia com `\q`. Depois, valide com `sql/validate_population.sql` e copie `logs.sqlite3` e o JSON para `results/`, com a aplicação parada e **somente se os destinos não existirem**. O restaurador protegido é preferível porque verifica essas condições. [Documentação pg_restore](https://www.postgresql.org/docs/18/app-pgrestore.html).

### 2. Gerar uma base do zero — alternativa sem histórico

Use apenas em banco novo. Essa opção gera dados sintéticos, mas não recupera resultados antigos.

1. Crie `tcc_sql_optimizer_logs` com `createdb`, conforme a seção manual. Se já existir, pare.
2. Execute cada comando somente após o anterior terminar sem erro:

```sh
psql -h localhost -p 5432 -U postgres -d tcc_sql_optimizer_logs -W -v ON_ERROR_STOP=1 -f sql/schema.sql
psql -h localhost -p 5432 -U postgres -d tcc_sql_optimizer_logs -W -v ON_ERROR_STOP=1 -f sql/pg_stat_statements_setup.sql
python -m scripts.populate_database
psql -h localhost -p 5432 -U postgres -d tcc_sql_optimizer_logs -W -v ON_ERROR_STOP=1 -f sql/validate_population.sql
```

O gerador utiliza semente 2026, 100 mil clientes, 50 mil produtos, um milhão de pedidos e lotes de dez mil. Gera um pagamento e dois ou três itens por pedido. Recusa tabelas já populadas e confirma a transação ao final. Pode demorar; a reprodução exata exige o mesmo código e parâmetros.

O reset de estatísticas no SQL de configuração está comentado e não faz parte da instalação. A aplicação inicializa o SQLite quando necessário. Depois, execute exemplos para produzir estatísticas e avaliações.

### 3. Criar novos backups

Encerre medições/gravações na aplicação antes de capturar os dois bancos. O PostgreSQL usa snapshot exportado e o SQLite usa sua Backup API; são consistentes individualmente, mas não constituem uma transação distribuída.

```sh
python -m scripts.backup_databases create --bundle backups/minha-nova-copia
python -m scripts.backup_databases verify --bundle backups/minha-nova-copia
```

Acrescente `--pg-bin` quando os binários não estiverem no PATH. `create` recusa pasta existente. `verify` cria um banco de nome aleatório, restaura, compara todas as linhas via SHA-256 de COPY binário ordenado e confere estruturas/sequências/extensões. Remove **somente o banco temporário criado por ele, após sucesso**. Se ocorrer falha, esse banco permanece para diagnóstico. A conta precisa poder criar bancos e extensões.

Inclui o SQLite ativo, JSONs `rodada_*.json` e `results/log_sources/`, se houver. Cópias SQLite antigas não são confundidas com o banco ativo. `.env`, senhas e ambiente virtual não integram o pacote. Os binários em `backups/` são ignorados pelo Git; instruções e comprovantes textuais são versionáveis.

### 4. Distribuição e comprovantes

Confira a integridade do pacote em [SHA256SUMS.txt](backups/SHA256SUMS.txt). O pacote ainda não está disponível para download público. O pacote preserva as 240 amostras da rodada do artigo e permite abrir os resultados sem gerar milhões de registros novamente.

### 5. Verificação dos dados

O pacote de 08/11/2026 foi restaurado em banco novo na instalação local e comparado integralmente com o inventário de origem. O SQLite passou em `integrity_check` e `foreign_key_check`; as 240 amostras foram conferidas. Os comprovantes estão em [manifesto](backups/manifest-2026-11-08.json) e [verificação](backups/verification-2026-11-08.json).

### Problemas de restauração

| Sintoma | Solução |
|---|---|
| Destino já existe | Proteção intencional. Use clone novo e outra instância; não sobrescreva dados. |
| Restauração falhou após criar banco | O banco novo permanece para diagnóstico. Não repita sobre ele. |
| Versão de extensão divergente | Prefira a versão de origem: PostgreSQL 18.6 / `pg_stat_statements` 1.12; não ignore divergências sem verificação. |
| Histórico vazio | Confirme a restauração de `results/logs.sqlite3` antes de iniciar a aplicação. Só o JSON não basta. |

**Próxima etapa:** [iniciar a interface e consultar o histórico](#utilização-testes-e-experimentos).

## Utilização, testes e experimentos

**Antes de começar:** finalize a [instalação](#instalação-e-configuração) e a [restauração dos dois bancos](#bancos-de-dados-e-backups). Os comandos são executados na raiz do clone. `python` significa `.\.venv\Scripts\python.exe` no Windows ou `.venv/bin/python` no Linux.

### 1. Iniciar e utilizar

Windows:

```powershell
.\.venv\Scripts\python.exe -X utf8 -m src.webapp --open
```

Linux:

```bash
.venv/bin/python -m src.webapp --open
```

Abra **http://127.0.0.1:8767** se o navegador não abrir automaticamente. Mantenha o terminal aberto; `Ctrl+C` encerra o servidor. No Windows, `Abrir interface.cmd` é um atalho equivalente. Para outra porta: `python -m src.webapp --port 8770 --open`.

#### Consultar resultados existentes

1. Abra **Histórico de medições** no menu lateral.
2. Filtre por consulta/regra e expanda detalhes e SQLs completos.
3. Baixe relatórios JSON ou utilize **Exportar todos em CSV**.
4. Para conferir a Tabela 4 sem novas medições, siga [Testes e reprodução dos experimentos](#2-testes-e-reprodução-dos-experimentos).

O JSON isolado não é importado pela interface; é o SQLite que fornece os relatórios. Ao abrir a aplicação, os snapshots antigos continuam disponíveis. Ao clicar em **Atualizar consultas** em outra instância, a lista principal passa a mostrar a última fonte sincronizada (host, porta e OID do banco). Os snapshots anteriores continuam no SQLite; o histórico de medições é separado e permanece acessível.

#### Executar e investigar consultas

1. Em **Consultas SQL**, selecione C01–C12 ou uma consulta própria e clique em **Executar consulta**. O SELECT é realmente executado, mas as linhas não são exibidas.
2. Clique em **Atualizar consultas**. Também é possível executar SQL no DBeaver/psql, conectado à mesma instância e banco.
3. Ordene por tempo, frequência ou data e clique em **Investigar**.
4. Examine métricas, plano e alertas. Quando houver `$1`, `$2` etc., informe a lista JSON na ordem mostrada no SQL. Exemplos: `[1, 10]` para o intervalo da C03; `[2025]` para ano; `["cliente123@example.com"]` para e-mail.
5. Leia as condições da proposta. O botão **Medir ganho** realiza uma rodada curta de três medições por versão.
6. Para dez repetições, utilize a comparação completa quando disponibilizada, ou o script de [reprodução experimental](#2-testes-e-reprodução-dos-experimentos). **Comparar planos** estima; **Executar e medir** executa ambas as versões e salva uma nova avaliação.

`Atualizar consultas` não executa os SELECTs observados e não reseta estatísticas. `pg_stat_statements` agrupa chamadas por estrutura e não recupera os valores literais originais nem identifica a ferramenta que executou cada chamada.

#### Regras e limites

- **Ano:** igualdade com `EXTRACT(YEAR ...)`, ano literal e coluna DATE/TIMESTAMP sem fuso; geração de intervalo anual.
- **LOWER:** remoção somente após confirmar que todos os valores atuais da coluna já correspondem a `LOWER(coluna)`; preserva o valor pesquisado.
- **COUNT correlacionado:** subconsulta escalar simples com igualdade; geração de agregação, `LEFT JOIN` e `COALESCE`, sob as restrições do parser.
- **Índice:** sugestão de DDL para certos filtros com ordenação; não é executada automaticamente.
- **Validação:** colunas, tipos, contagem e assinaturas sobre todas as linhas, considerando a ordenação; mesma fotografia de dados em `REPEATABLE READ`.
- **Medição:** 3–50 repetições por versão, um aquecimento explícito, semente 2026, até 30 segundos por consulta e três minutos por experimento. A validação recusa resultados acima de três milhões de linhas.

A equivalência é empírica, limitada aos dados testados. Não há teste de significância estatística. O campo `reduction_pct` usa medianas; a Tabela 4 do artigo utiliza médias. Custo estimado não é tempo em milissegundos, e leituras de blocos não comprovam acesso físico ao disco.

### 2. Testes e reprodução dos experimentos

#### Testes automatizados

```sh
python -m unittest discover -s tests -v
```

Em 08/11/2026, os **62 testes existentes e oito testes novos passaram (70 no total)**. A suíte utiliza conexões simuladas e SQLite temporário; não substitui o teste de restauração real. Os testes dos novos utilitários estão em `tests/test_backup_tools.py`.

#### Conferir as 240 amostras sem executar SQL

```sh
python -m scripts.reproduce_experiment --check-saved results/rodada_12_consultas_20261107.json
```

Verifica C01–C12, dez amostras por versão, indicadores de correspondência e recalcula médias/variações. Não acessa PostgreSQL nem modifica o histórico. As 240 medições não incluem verificações de resultado e aquecimentos.

#### Executar uma nova rodada C01–C12

```sh
python -m scripts.reproduce_experiment --run
```

Usa `src/demo_queries.py`, gera alternativas com `src/optimization.py` e mede com `src/benchmark.py`, dez vezes por versão. Acrescenta avaliações ao SQLite e cria um JSON de nome único em `results/`. Não substitui a rodada original. Em falha, resultados parciais ficam preservados. Executa SELECTs reais e acrescenta atividade às estatísticas, sem alterar registros comerciais nem resetar `pg_stat_statements`.

O protocolo é reproduzido com o código atual; os tempos históricos não são garantidos em outro hardware, cache, configuração ou locale. Use uma instalação exclusiva de avaliação e evite medições concorrentes.

Os exemplos **C01–C12** são os casos do artigo. `sql/queries.sql` e `scripts/generate_workload.py` contêm outra carga, **Q01–Q12**, que não representa as 240 medições. Para inspecioná-la sem executar:

```sh
python -m scripts.generate_workload --preview
```

### 3. Módulos opcionais de logs

O projeto também possui módulos/API para importar logs PostgreSQL stderr, CSV e JSON, separados das estatísticas agregadas. Esses controles não estão expostos na navegação principal atual. Para a banca, utilize a fonte PostgreSQL descrita neste guia; a configuração opcional de captura consta no [guia de instalação](#instalação-e-configuração).

### Problemas durante o uso

| Sintoma | Solução |
|---|---|
| Lista vazia após atualizar | Os contadores da nova instância não são os antigos. Execute exemplo e atualize; medições salvas permanecem. |
| Parâmetros `$1`, `$2` | Informe valores como lista JSON na ordem do SQL. |
| Sem proposta automática | O padrão está fora das regras ou faltam condições; isso não é erro de instalação. |
| Tempo limite/resultados diferentes | Examine o SQL e reduza o recorte. O sistema interrompe medições sem correspondência validada. |
| Porta 8767 ocupada | Use `--port 8770`; não encerre processos desconhecidos. |
| Importação de logs não aparece | O recurso existe nos módulos/API, mas está fora da navegação principal atual. Não é necessário ao roteiro. |

Para erros de conexão, consulte [Instalação](#instalação-e-configuração); para histórico ausente ou restauração, consulte [Bancos de dados](#bancos-de-dados-e-backups).

### Mapa técnico do projeto

```text
TCC/
├── README.md / .env.example / requirements*.txt
├── src/
│   ├── webapp.py                 # servidor HTTP local
│   ├── config.py / database.py   # conexão
│   ├── statement_sync.py         # pg_stat_statements e snapshots
│   ├── execution_logs.py         # SQLite, logs e relatórios
│   ├── analyzer.py / plan_analyzer.py / query_triage.py
│   ├── optimization.py           # três regras do experimento
│   ├── recommendations.py        # recomendações complementares
│   ├── benchmark.py / measurement_resources.py
│   └── demo_queries.py           # C01–C12
├── web/                          # HTML/CSS/JavaScript
├── sql/                          # esquema, validação e Q01–Q12
├── scripts/
│   ├── populate_database.py
│   ├── generate_workload.py
│   ├── backup_databases.py        # create / verify / restore
│   └── reproduce_experiment.py    # conferir ou medir C01–C12
├── tests/
├── results/                      # SQLite e resultados locais
└── backups/                      # pacotes e comprovantes
```
