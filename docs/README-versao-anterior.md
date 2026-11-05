# TCC — Análise de desempenho de consultas SQL

> **Preparação após a formatação em 12/10/2026:** Python, dependências e
> DBeaver instalados; PostgreSQL conectado, banco populado e 12 consultas
> testadas sem erros. Coleta ativa, rodada completa de 730 execuções validada
> e resultados CSV/JSON conferidos em `results/ambiente_2026-10-12`.
> Consulte [o guia do ambiente local](docs/ambiente_local.md) para ver o
> estado verificado e os próximos passos. O roteiro abaixo preserva também
> o histórico dos experimentos anteriores.

Protótipo experimental do Trabalho de Conclusão de Curso de Ciência da
Computação: **Análise e otimização de consultas SQL com base em logs de
execução em bancos de dados relacionais**.

O objetivo inicial é gerar uma carga controlada, coletar estatísticas de
execução e identificar consultas com maior tempo total, tempo médio e
frequência. A continuação preventiva recebe um `SELECT`, solicita seu plano
estimado sem executá-lo e apresenta hipóteses de melhoria baseadas em regras.
O `pg_stat_statements` fornece estatísticas agregadas por consulta, não um log
individual de cada execução.

## Abrir a interface visual

Dê dois cliques em **`Abrir interface.cmd`**, na raiz do projeto. O navegador
abrirá o **Observatório SQL**, em http://127.0.0.1:8765. Mantenha a janela de
inicialização aberta enquanto usar a interface.

Comece pela aba **Entenda o projeto**: ela explica os conceitos e traz um
roteiro de apresentação. As outras abas mostram o histórico real, analisam
uma consulta e comparam duas versões pelo plano estimado. A interface usa
o banco local já configurado, sem novas dependências Python ou Node.js.

Consulte [o guia da interface](docs/interface.md) para aprender o fluxo e
[o ambiente local](docs/ambiente_local.md) para os resultados da reinstalação.

## Histórico das etapas anteriores à reinstalação

Os registros abaixo descrevem a validação original. O estado atualizado do
ambiente está no guia acima, incluindo a coleta e a exportação já verificadas.

Etapa 1 validada pelo autor: as cinco tabelas foram listadas no DBeaver e
o diagnóstico Python conectou ao banco `tcc_sql_optimizer` com sucesso.

Etapa 2: carga executada pelo autor e contagens confirmadas no DBeaver:
100.000 clientes, 50.000 produtos, 1.000.000 pedidos, 2.498.714 itens e
1.000.000 pagamentos. A validação de consistência e distribuição das
consultas 2, 3 e 4 de `validate_population.sql` ainda não foi confirmada.

Etapa 3: prévia de 730 execuções validada pelo autor e teste funcional
concluído com 12 consultas sem erro, uma execução de cada, em 14,3 segundos.
O teste mostrou uma linha em Q01, 30 em Q11 e 2.498.714 em Q12.

Etapa 4: pg_stat_statements 1.12 instalado e coleta ativa validada pelo autor.

Etapa 5 validada: workload completo com 730 execuções sem erro, em 103,2
segundos no cliente. Coletor confirmou 12 consultas, 730 chamadas e 13 entradas
excluídas, com três rankings. Saída informada em 2026-09-29T17:48:14+00:00.
O registro dessa rodada está em `docs/experiment_001.md`.

Etapa 6 preparada: exportação CSV/JSON e documentação disponíveis, ainda
aguardando execução e validação dos arquivos pelo autor.

Etapa 7 validada inicialmente: o analisador produziu o plano estimado sem
executar a consulta Q05, relacionou seu Query ID a 15 execuções históricas e
identificou uma subestimação de aproximadamente 100 vezes na quantidade de
linhas. Uma segunda comparação previu a mudança de `Seq Scan` para `Index Scan`
na consulta por e-mail. A validação posterior mediu redução de 99,88% no tempo
médio do servidor, com resultados equivalentes. Os registros estão em
`docs/preventive_analysis_001.md`, `docs/preventive_comparison_002.md` e
`docs/recommendation_validation_001.md`.

A interface local foi acrescentada em outubro de 2026. Ela reaproveita o
coletor e o analisador Python, sem executar as consultas candidatas, criar
índices ou aplicar otimizações automaticamente.

## Tecnologias

- PostgreSQL e `pg_stat_statements`.
- Python 3.12 ou superior e Psycopg 3 (o gerador usa `itertools.batched`).
- `python-dotenv` para carregar a configuração local.
- DBeaver para administração manual do banco.
- Git para versionamento.

Versões informadas pelo autor durante a validação:

| Componente | Versão |
| --- | --- |
| Python | 3.14.3 |
| PostgreSQL | 18.1, Windows 64 bits |
| pg_stat_statements | 1.12 |
| Psycopg / psycopg-binary | 3.3.6 |
| python-dotenv | 1.2.3 |
| tzdata | 2026.4 |

`requirements.txt` declara as faixas de dependências. `requirements-lock.txt`
registra as versões exatas informadas na instalação validada pelo autor;
não foi gerado por uma execução de pip pelo assistente. Para reproduzir os
dados, registre também a revisão do código, a versão Python, a semente e
os argumentos utilizados. Tempos dependem do hardware, da configuração do
servidor e das condições de cada execução, mesmo com os mesmos dados.

## Estrutura atual

```text
TCC/
├── README.md
├── requirements.txt
├── requirements-lock.txt
├── .env.example
├── .gitignore
├── docs/
│   ├── experiment_001.md
│   ├── preventive_analysis_001.md
│   ├── preventive_comparison_001.md
│   ├── preventive_comparison_002.md
│   └── recommendation_validation_001.md
├── sql/
│   ├── schema.sql
│   ├── queries.sql
│   ├── candidate_query.sql
│   ├── candidate_query_range.sql
│   ├── candidate_email_lower.sql
│   ├── candidate_email_direct.sql
│   ├── pg_stat_statements_setup.sql
│   └── validate_population.sql
├── scripts/
│   ├── .gitkeep
│   ├── __init__.py
│   ├── generate_workload.py
│   ├── validate_recommendation.py
│   └── populate_database.py
├── src/
│   ├── __init__.py
│   ├── config.py
│   ├── collector.py
│   ├── ranking.py
│   ├── exporter.py
│   ├── plan_analyzer.py
│   ├── analyzer.py
│   ├── compare_plans.py
│   └── database.py
└── results/
    └── .gitkeep
```

A pasta TCC é a raiz do projeto e já contém o repositório Git. Os arquivos
`.gitkeep` apenas permitem versionar as pastas inicialmente vazias.

## Configuração e conexão

### Requisitos e instalação em um novo ambiente

O ambiente atual já foi instalado e validado. Os passos abaixo documentam
como preparar outra instalação; não reinstale nem recrie o banco atual.

1. Instale Python (3.14.3 foi a versão utilizada), Git e DBeaver.
2. Obtenha o instalador do PostgreSQL pela
   [página oficial para Windows](https://www.postgresql.org/download/windows/).
   O experimento foi realizado com a versão 18.1. Instale o servidor,
   configure uma senha para o usuário `postgres` e anote a porta escolhida.
3. Configure uma conexão PostgreSQL no DBeaver com host, porta, banco inicial
   `postgres`, usuário e senha. O DBeaver é o cliente; o serviço PostgreSQL
   precisa estar instalado e em execução.
4. Abra o PowerShell na pasta que contém os arquivos do projeto e prepare
   o ambiente virtual e as dependências:

```powershell
python --version
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
```

Não é necessário ativar a `.venv`, pois os comandos usam seu executável
diretamente. O arquivo de versões fixas corresponde ao ambiente Windows
validado; alterações de plataforma ou versões devem ser registradas.

5. Crie a configuração local somente se ela ainda não existir:

```powershell
if (-not (Test-Path -LiteralPath '.env')) {
    Copy-Item -LiteralPath '.env.example' -Destination '.env'
}
```

Preencha no editor a senha e os dados corretos da conexão no `.env`.
Não coloque credenciais em scripts nem em comandos destinados ao histórico.

6. No DBeaver, conectado ao banco inicial `postgres`, com auto-commit ativado,
   execute isoladamente, fora de um bloco BEGIN:

```sql
CREATE DATABASE tcc_sql_optimizer;
```

Esse comando cria um banco vazio. Se ele já existir, não o exclua: confira
se é o ambiente experimental correto. Configure então uma conexão com o
campo Database igual a `tcc_sql_optimizer` e abra um novo editor SQL nela.
Selecionar um item na árvore não altera necessariamente um editor já aberto.

```sql
SELECT current_database(), current_user, version();
```

Confirme `tcc_sql_optimizer` antes de executar `sql/schema.sql` inteiro.
O esquema cria as cinco tabelas e suas restrições. Depois, execute o diagnóstico
Python abaixo; a saída deve confirmar banco, usuário e versão do servidor.

### Variáveis e diagnóstico

`.env.example` é o modelo de configuração, sem senha. Na preparação manual
do ambiente, uma cópia chamada `.env` receberá as credenciais locais.
Não versione essa cópia nem compartilhe sua senha.

As variáveis são `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD` e
`DB_CONNECT_TIMEOUT`. Variáveis já definidas no ambiente têm prioridade
sobre o `.env`. O banco configurado deve ser `tcc_sql_optimizer`.

`src/config.py` carrega e valida a configuração. `src/database.py` fornece
a conexão reutilizável e um diagnóstico que consulta banco, usuário e
versão do servidor. As conexões e os cursores usam blocos `with` para
garantir fechamento correto.

Somente após instalar as dependências, criar o banco e preencher o `.env`,
o autor executará este diagnóstico na raiz do projeto:

```powershell
.\.venv\Scripts\python.exe -m src.database
```

Esse comando abre uma conexão e executa uma consulta de leitura. Não cria
o banco nem as tabelas. A saída esperada contém a confirmação da conexão,
o banco `tcc_sql_optimizer`, o usuário e a versão do PostgreSQL.

## Modelo de dados

O arquivo `sql/schema.sql` define:

- `clientes`: cadastro, localização e situação dos clientes.
- `produtos`: catálogo, preço e estoque.
- `pedidos`: cliente, data, situação e valor total.
- `itens_pedido`: produtos, quantidades e preços praticados nos pedidos.
- `pagamentos`: tentativas ou pagamentos vinculados a pedidos.

O modelo utiliza PKs e FKs em `BIGINT`, valores monetários em `NUMERIC`,
status validados com `CHECK` e e-mail único. As datas sintéticas usarão
um horário local convencionado, armazenado sem fuso horário.

O esquema contém apenas os índices associados às PKs e à unicidade do
e-mail. Não há índices adicionais de otimização nesta etapa.

O gerador calcula o total de cada pedido a partir de seus itens, usando
centavos inteiros e `Decimal`. Ele utiliza IDs explícitos e ajusta as
sequências de identidade ao final do carregamento.

**Impacto da futura execução manual:** o script cria cinco tabelas, suas
sequências, restrições e índices associados. A criação está agrupada em
uma transação. O script verifica o nome do banco antes de criar as tabelas.
Essa verificação não substitui a conferência do servidor e da porta.

O script não exclui dados e não ignora tabelas existentes: se um nome já
existir, a execução falhará para que a situação seja analisada. Em caso de
erro, interrompa a execução e compartilhe a mensagem antes de tentar
novamente.

## Execução do experimento

Todos os comandos são executados manualmente pelo autor. Em caso de erro,
interrompa a sequência e analise a mensagem antes de continuar. O roteiro
abaixo organiza a execução completa; as seções por etapa explicam cada decisão.

### Preparação inicial, somente em um banco novo

1. Instale as ferramentas e dependências, configure `.env` e crie o banco
   conforme a seção anterior. Execute `sql/schema.sql` no DBeaver.
2. Confira a conexão e popule as tabelas vazias, no PowerShell:

```powershell
.\.venv\Scripts\python.exe -m src.database
.\.venv\Scripts\python.exe -m scripts.populate_database
```

3. Aguarde o COMMIT confirmado e execute `sql/validate_population.sql` no
   DBeaver. Compare contagens, totais, datas e distribuições com a Etapa 2.
4. Configure `shared_preload_libraries`, reinicie o serviço e execute
   `sql/pg_stat_statements_setup.sql`, conforme a Etapa 4.
5. Confira as consultas e faça o teste funcional no PowerShell:

```powershell
.\.venv\Scripts\python.exe -m scripts.generate_workload --preview
.\.venv\Scripts\python.exe -m scripts.generate_workload --smoke
```

O teste deve concluir as 12 consultas sem erro. Não repopule tabelas já
carregadas para iniciar uma nova rodada de medições.

### Rodada de medição com o banco já preparado

1. Preserve resultados de rodadas anteriores que queira manter. No DBeaver,
   resete somente as estatísticas do banco experimental. Esse reset descarta
   métricas anteriores; não exclui dados das tabelas nem limpa caches:

```sql
SELECT public.pg_stat_statements_reset(
    dbid => (SELECT oid FROM pg_database WHERE datname = 'tcc_sql_optimizer')
);
```

2. Registre o horário retornado. No PowerShell, execute a carga completa:

```powershell
.\.venv\Scripts\python.exe -m scripts.generate_workload
```

3. Somente após `Workload concluído: 730 execuções sem erro.`, colete, exiba
   os rankings e exporte as métricas da mesma coleta:

```powershell
.\.venv\Scripts\python.exe -m src.collector --top 5
```

4. Confira 12 consultas selecionadas e 730 chamadas. Os arquivos são gravados
   em `results/query_metrics.csv` e `results/query_metrics.json` por padrão.
   Valide os arquivos conforme a Etapa 6.

Para exportar uma carga já medida, execute apenas o coletor. Não resete nem
repita o workload. Uma nova coleta terá novo `collected_at`; as métricas
permanecerão compatíveis se não houver novas execuções das consultas filtradas.

## Etapa 2 — Geração dos dados

### Volume e distribuição

O comando padrão carrega:

| Tabela | Registros |
| --- | ---: |
| clientes | 100.000 |
| produtos | 50.000 |
| pedidos | 1.000.000 |
| itens_pedido | 2 a 3 milhões, aproximadamente 2,5 milhões |
| pagamentos | 1.000.000 |

- Semente padrão: `2026`; não são utilizadas datas baseadas no relógio atual.
- Cadastros de clientes entre janeiro de 2022 e dezembro de 2023.
- Pedidos entre janeiro de 2024 e agosto de 2026: aproximadamente 20% em
  2024, 30% em 2025 e 50% em 2026.
- Cerca de 80% dos pedidos pertencem aos primeiros 20% dos clientes.
- Cerca de 70% das linhas de itens usam os primeiros 10% dos produtos.
- Cada pedido contém duas ou três linhas de itens, com uma a cinco unidades
  por linha. Um produto pode aparecer em mais de uma linha do mesmo pedido.
- Preços variam por categoria, com descontos em parte dos itens.
- Pedidos: 12% pendentes, 13% pagos, 20% enviados, 48% entregues e 7% cancelados.
- Uma tentativa de pagamento por pedido. Pedidos pagos, enviados e entregues
  têm pagamento aprovado; pendentes têm tentativa pendente ou recusada;
  cancelados têm tentativa recusada ou pagamento estornado.
- Pagamentos aprovados/estornados têm a data do pagamento original entre
  um minuto e dois dias após o pedido. Não há uma coluna para a data do estorno.
- Valores dos pagamentos correspondem ao valor total do pedido, inclusive
  quando representam uma tentativa recusada ou pendente.

Essas distribuições são hipóteses sintéticas do experimento, não dados de
uma empresa real. Nomes são identificadores fictícios e e-mails usam
`example.com`. Estoque e indicadores de atividade representam um estado
cadastral independente; o gerador não simula a movimentação de estoque ou
o ciclo de vida completo de um sistema comercial.

### Funcionamento e impacto

O programa usa `COPY FROM STDIN`, transmitindo linhas com `write_row()`.
Não há um comando `INSERT` separado por registro. Catálogos e pedidos são
enviados em lotes; o lote padrão contém 10.000 registros de catálogo ou
10.000 pedidos com seus respectivos itens e pagamentos. A memória não
precisa comportar o conjunto completo; mantém os preços dos produtos e
os lotes em processamento.

**Ao executar, você autoriza a inserção de aproximadamente 4,65 milhões de
registros**, o ajuste das cinco sequências de IDs e um `ANALYZE` em cada
tabela. O carregamento pode consumir tempo, espaço em disco e arquivos de
WAL. `ANALYZE` atualiza as estatísticas usadas pelo planejador; não é
`EXPLAIN ANALYZE` e não realiza análise de planos pelo protótipo.

O gerador verifica o nome do banco e exige as cinco tabelas vazias.
Não há `DELETE`, `TRUNCATE` ou `DROP`. Uma segunda execução em tabelas
populadas é recusada, sem limpeza automática. Ele não implementa retomada
de uma carga parcial.

Uma transação envolve toda a carga; os lotes não são commits separados.
O programa solicita bloqueios que impedem outras escritas nas cinco tabelas
até o término e falha imediatamente se houver bloqueio incompatível.
Consultas comuns continuam possíveis, mas outra conexão só verá os dados
após o COMMIT. Evite editar as tabelas durante a carga.

Uma falha antes do COMMIT causa a tentativa de rollback pelo contexto da
conexão. Alterações de sequência por `setval` não são revertidas como as
linhas. Em caso de falha de comunicação durante o COMMIT, o resultado pode
ser incerto: confira as tabelas antes de tentar novamente. O programa só
anuncia sucesso depois da confirmação do COMMIT.

### Execução manual

Pré-requisitos: Etapa 1 validada, `.env` preenchido e cinco tabelas vazias.
Na raiz do projeto, execute no PowerShell:

```powershell
.\.venv\Scripts\python.exe -m scripts.populate_database
```

O programa informa versões, volumes, semente, lotes enviados, atualização
das estatísticas e confirmação da transação. Ao terminar, apresenta a
quantidade exata gerada em cada tabela e o tempo total. A porcentagem de
pedidos enviados não significa que o COMMIT já terminou.

Os parâmetros opcionais são `--clientes`, `--produtos`, `--pedidos`,
`--lote` e `--seed`. Para este experimento, utilize os valores padrão.
Um teste com volume menor ocuparia as tabelas e impediria a carga padrão
subsequente; não faça as duas execuções no mesmo conjunto de tabelas.

### Validação manual

Após a mensagem `Carga concluída e COMMIT confirmado.`, execute as consultas
de `sql/validate_population.sql` no DBeaver, no banco experimental:

1. Contagens: devem corresponder ao resumo do gerador.
2. Integridade dos totais, datas e status: todos os indicadores devem ser zero.
3. Concentração de pedidos: aproximadamente 80%, para os volumes padrão.
4. Distribuição por ano e status: pedidos nos três anos e nos cinco status.

As consultas de contagem e consistência percorrem os dados e podem levar
tempo. Não foram executadas pelo assistente. As estatísticas de execução
da preparação serão separadas do experimento quando configurarmos o reset
do `pg_stat_statements` na Etapa 4.

## Etapa 3 — Consultas e geração de carga

### Consultas disponíveis

`sql/queries.sql` contém a única definição do SQL e das frequências. O gerador
lê os comentários no formato `-- name: Q01 | calls: 500 | title: ...`.
Cada bloco deve conter um SELECT e um único ponto e vírgula final. Esse
formato controlado não é um parser SQL genérico; por exemplo, não admite
ponto e vírgula dentro de uma string SQL.

| Consulta | Característica | Execuções padrão |
| --- | --- | ---: |
| Q01 | Busca de cliente pela chave primária | 500 |
| Q02 | Produtos por categoria, preço e situação, com ordenação | 100 |
| Q03 | Histórico de pedidos de um cliente | 60 |
| Q04 | SELECT * de pedidos cancelados | 20 |
| Q05 | JOIN e EXTRACT sobre data, com muitas linhas | 15 |
| Q06 | Cinco tabelas, GROUP BY, SUM e ORDER BY | 10 |
| Q07 | Período de 2025 com agregação mensal | 8 |
| Q08 | Ordenação dos mil maiores pedidos | 6 |
| Q09 | LOWER aplicado ao e-mail | 5 |
| Q10 | Subquery com média e muitas linhas de saída | 3 |
| Q11 | Subquery correlacionada para 30 clientes | 2 |
| Q12 | SELECT * de todos os itens | 1 |
| **Total** | **12 consultas diferentes** | **730** |

Q01 foi escolhida como candidata a consulta rápida e frequente. Q05, Q09,
Q11 e Q12 apresentam características potencialmente custosas. O desempenho
real depende das medições; não se presume que uma consulta seja lenta apenas
por conter JOIN, subquery, função ou SELECT *. A subquery correlacionada foi
limitada a 30 clientes para não multiplicar varreduras por todo o cadastro.

Q06 considera o pagamento aprovado para somar itens: neste conjunto há uma
tentativa de pagamento por pedido. Se o gerador futuramente produzir vários
pagamentos aprovados por pedido, essa consulta precisará ser revisada para
não multiplicar os itens no JOIN.

### Comportamento do gerador

- Uma conexão, sem concorrência, com consultas em ordem embaralhada pela
  semente padrão `2026`. Os valores dos filtros são fixos em `queries.sql`.
- Todas as linhas são consumidas com `Cursor.stream()` e descartadas após
  a contagem; o resultado completo não fica armazenado em uma lista Python.
- Não usa cursores SQL nomeados (`DECLARE`/`FETCH`), que mudariam os comandos
  observados. O fluxo transmite os SELECTs definidos no arquivo.
- A preparação automática de statements é desabilitada nesta conexão para
  manter essa escolha explícita no protocolo experimental.
- A sessão utiliza transações somente de leitura e autocommit, sem uma
  transação longa envolvendo todo o workload.
- Antes da carga, verifica o banco e a existência de ao menos uma linha em
  cada tabela. Isso não substitui a validação de consistência da Etapa 2.
- Configura apenas nesta conexão o nome da aplicação, o modo de leitura e
  `statement_timeout` (120 segundos por consulta por padrão).
- Para no primeiro erro ou timeout, mostra o resumo das execuções concluídas
  e retorna código de saída diferente de zero. Não repete falhas automaticamente.
- Mostra consulta atual, progresso, linhas consumidas e tempo no cliente.
  A contagem de linhas no resumo é acumulada por consulta nas repetições.

Os tempos locais incluem comunicação, conversão dos valores e consumo das
linhas no Python. Não equivalem a `total_exec_time` e `mean_exec_time` do
`pg_stat_statements`, nem constituem o coletor ou os rankings da Etapa 5.
Mesmo os tempos do servidor podem ser afetados pelo ritmo de consumo de
resultados volumosos. Não há limites artificiais adicionados às consultas.

Uma consulta em timeout pode ter retornado parte das linhas; ela não entra
como execução concluída no resumo. Estatísticas de execuções anteriores
podem permanecer no servidor. Uma execução interrompida não deve ser
considerada um experimento completo nem misturada silenciosamente a outra.

### Prévia manual, sem banco

Na raiz do projeto, execute:

```powershell
.\.venv\Scripts\python.exe -m scripts.generate_workload --preview
```

Esse modo lê e valida o formato de `queries.sql`, lista as frequências e
termina sem chamar a função de conexão. Deve informar:

```text
Total: 12 consultas diferentes | 730 execuções
Prévia concluída. Nenhuma conexão com o banco foi aberta.
```

### Teste funcional manual, com banco

Após revisar o código e validar a consistência da carga, este comando
executa cada consulta uma vez, incluindo a leitura de todos os itens:

```powershell
.\.venv\Scripts\python.exe -m scripts.generate_workload --smoke
```

Espera-se `Workload concluído: 12 execuções sem erro.` e `calls=1` em cada
uma das 12 linhas do resumo. Q01 deve retornar uma linha; Q11, 30 linhas;
Q12, 2.498.714 linhas no conjunto confirmado pelo autor. As consultas podem
consumir CPU, I/O, memória do servidor e espaço temporário, embora não
alterem os dados das tabelas. O modo de teste também aquece caches e,
se a extensão estiver ativa, gera estatísticas.

### Carga completa manual — após a Etapa 4

Primeiro configure e valide `pg_stat_statements`, conclua a validação da
carga e prepare o reset das estatísticas. Depois, execute:

```powershell
.\.venv\Scripts\python.exe -m scripts.generate_workload
```

O resultado esperado é `Workload concluído: 730 execuções sem erro.`. O
campo `calls` de cada consulta no resumo deve coincidir com a tabela acima.
Se for necessário alterar o limite, utilize `--timeout-seconds`, registrando
o valor adotado; o limite é do servidor, não um cronômetro do processo Python.

O gerador não instala a extensão, não reseta estatísticas e não verifica se
ela está habilitada. Ele pode executar sem ela, mas isso não valida a coleta.
O coletor está disponível na Etapa 5, com exportações CSV/JSON documentadas
na Etapa 6.

O reset de estatísticas não limpa caches. Registre testes prévios e evite
consultas manuais concorrentes durante a medição. Os comandos de preparação
da sessão também podem aparecer nas estatísticas; não confunda o total de
730 SELECTs do workload com a contagem global de comandos do servidor.
Os nomes Q01–Q12 são identificadores locais, não os `queryid` do PostgreSQL.

## Etapa 4 — pg_stat_statements

### Diagnóstico confirmado

O servidor informou o arquivo de configuração:

```text
C:/Program Files/PostgreSQL/18/data/postgresql.conf
```

`shared_preload_libraries` está vazio, `compute_query_id` está em `auto` e
`pg_stat_statements` está disponível na versão 1.12, ainda sem versão instalada
no banco consultado. Esses valores foram enviados pelo autor, não obtidos
por acesso do assistente ao servidor.

### Edição manual da configuração

Abra um editor de texto como administrador e abra o arquivo indicado pelo
servidor. Localize `shared_preload_libraries`. Se a linha começar com `#`,
remova esse caractere para ativá-la. Deixe o parâmetro assim:

```conf
shared_preload_libraries = 'pg_stat_statements'
```

Não duplique uma linha ativa do mesmo parâmetro. Se o arquivo já tiver
outras bibliotecas configuradas, preserve-as e acrescente `pg_stat_statements`
à lista separada por vírgulas. Isso deve ser verificado no arquivo mesmo que
o valor ativo informado anteriormente estivesse vazio.

Mantenha `compute_query_id = auto`, que já foi confirmado no diagnóstico.
Esse valor permite a identificação das consultas quando o módulo é carregado.
Não é necessário ativar coleta de planos ou `track_io_timing` nesta etapa.

### Reinicialização manual no Windows

Salve o arquivo. A reinicialização interrompe conexões de todos os bancos
servidos por esse serviço PostgreSQL, incluindo as sessões do DBeaver.
Conclua qualquer trabalho aberto antes de reiniciar.

Abra `services.msc` pelo menu Iniciar ou pela janela Executar do Windows.
Identifique o serviço correspondente à instalação PostgreSQL 18 e escolha
Reiniciar. Apenas recarregar a configuração não ativa esta biblioteca.
Se o serviço não iniciar, envie a mensagem do serviço ou do log antes de
continuar; não tente executar os passos SQL sem o servidor funcionando.

### Instalação e validação manuais no banco experimental

Reconecte o DBeaver a `tcc_sql_optimizer`. Execute o arquivo
`sql/pg_stat_statements_setup.sql` inteiro. O arquivo:

1. Confere o banco e os pré-requisitos da configuração ativa.
2. Executa `CREATE EXTENSION IF NOT EXISTS pg_stat_statements WITH SCHEMA public`.
3. Exibe configurações e versão instalada.
4. Consulta um cliente e procura sua entrada em `public.pg_stat_statements`.

A instalação cria funções e views da extensão no banco. O módulo carregado
no servidor acompanha consultas de todos os bancos; o coletor deverá filtrar
o banco experimental. A consulta de validação já utiliza esse filtro.

Espera-se biblioteca ativa `pg_stat_statements`, identificação `auto` ou `on`,
rastreamento `top`, versão instalada `1.12` e a consulta do cliente com
`calls >= 1`, `queryid` e tempos de execução. Os valores literais podem
aparecer normalizados como `$1`. O SQL executado usa privilégios do usuário
`postgres`, já utilizado e validado pelo autor.

Se o arquivo falhar antes do COMMIT, interrompa o script e execute `ROLLBACK`
no mesmo editor para liberar a transação, depois envie o primeiro erro.
Se o comando de instalação retornar que a extensão já existe, a cláusula
`IF NOT EXISTS` apenas emite um aviso; confira a versão e o resultado da view.

### Reset antes de um novo experimento

O reset está documentado, mas comentado no arquivo de instalação. Ele não
deve acontecer automaticamente ao repetir a validação da extensão.

**Impacto:** o comando abaixo descarta métricas anteriores de todos os
usuários no banco `tcc_sql_optimizer`. Não apaga registros das cinco tabelas,
não limpa caches e não é desfeito por rollback. Salve resultados de um
experimento anterior antes de resetar. O filtro `dbid` preserva as métricas
dos demais bancos da instância.

Somente após validar a extensão, imediatamente antes da carga experimental,
o autor executará manualmente:

```sql
SELECT public.pg_stat_statements_reset(
    dbid => (SELECT oid FROM pg_database WHERE datname = 'tcc_sql_optimizer')
);
```

Registre o horário retornado. Não execute novamente as consultas de teste da
instalação após o reset, pois elas acrescentariam chamadas à carga medida.
O campo `pg_stat_statements_info.stats_reset` descreve o reset global, portanto
não deve ser usado como comprovação do horário deste reset restrito ao banco.
Consultas administrativas do DBeaver e de preparação da sessão também podem
aparecer nas estatísticas.

A ordem é: validar extensão, finalizar testes prévios, resetar, executar
o workload completo e coletar métricas. O reset, a carga completa e a coleta
ainda aguardam validação do autor; os comandos estão na Etapa 5 abaixo.

## Etapa 5 — Coletor e rankings

### Arquivos e métricas

`src/collector.py` lê as estatísticas e prepara os registros; `src/ranking.py`
gera três rankings sobre a mesma coleta: maior tempo total, maior tempo médio
e maior quantidade de execuções. O padrão exibe cinco posições em cada ranking.

Cada registro contém:

| Campo | Significado |
| --- | --- |
| query_id | `queryid` retornado pelo PostgreSQL; valores negativos são válidos |
| query | SQL representativo, normalmente com constantes substituídas por parâmetros |
| calls | Quantidade acumulada de execuções concluídas |
| total_exec_time | Tempo total de execução, em milissegundos |
| mean_exec_time | Tempo médio de execução, em milissegundos |
| rows | Total acumulado de linhas retornadas, não linhas por execução |
| impact_score | `mean_exec_time * calls`, em milissegundos |
| collected_at | Horário UTC do término da leitura, igual para os registros da coleta |

O indicador de impacto é provisório. Pela definição da média, ele equivale
aproximadamente a `total_exec_time`, salvo diferenças de ponto flutuante.
Assim, não representa um critério independente nesta versão. A frequência
usada aqui é a contagem `calls`, não execuções por segundo; compare rodadas
com protocolos de carga e janelas de coleta definidos.

A ordenação é numérica e decrescente. Empates são resolvidos pelo query ID,
para manter uma ordem determinística dentro do mesmo banco e conjunto de dados.
Não há inferência sobre causas de lentidão ou propostas de otimização.

### Escopo e tratamento de ruído

O coletor abre uma conexão com transação somente de leitura e não executa
reset, workload ou alterações nas tabelas. Descobre o esquema da extensão
pelo catálogo e lê a view uma vez para produzir todos os rankings.

O filtro padrão mantém apenas:

1. Entradas do banco atual, que deve ser `tcc_sql_optimizer`.
2. Entradas do usuário configurado no `.env`, que deve ser o mesmo do workload.
3. Comandos de nível superior com chamadas concluídas.
4. SQL iniciado por SELECT, admitindo comentários iniciais simples.
5. Referências `FROM public.<tabela>` ou `JOIN public.<tabela>` às cinco tabelas.

As verificações de existência de dados do gerador
(`SELECT EXISTS (SELECT 1 FROM ... LIMIT 1)`) são excluídas por seu formato,
inclusive quando as constantes aparecem como `$1`/`$2` nas estatísticas.
Consultas de catálogos do DBeaver, instalação da extensão e consultas do
próprio coletor ficam fora do filtro padrão.

Esse filtro foi desenhado para o SQL deste projeto; não é um parser geral,
não cobre CTEs iniciadas por WITH nem todos os formatos de comentários. Uma
consulta manual às tabelas experimentais ainda pode entrar no resultado.
Uma futura consulta de workload idêntica às verificações de existência
também exigiria revisão do filtro. Por isso, execute o reset antes da carga
e evite consultas manuais às tabelas até concluir a coleta.

`--all-selects` remove o filtro de tabelas e a exclusão das verificações de
preparação, mantendo banco, usuário e nível superior. Essa opção serve para
diagnóstico e inclui SELECTs administrativos, inclusive coletas anteriores.
O nome da aplicação não é um campo de filtragem do `pg_stat_statements`.

### Versões e interpretação

O ambiente validado usa PostgreSQL 18.1. O coletor confere se a view contém
`total_exec_time` e `mean_exec_time`, usados pelas versões modernas da extensão.
Versões antigas com somente `total_time` e `mean_time` são recusadas com uma
mensagem explicativa; esses campos antigos não são renomeados silenciosamente,
pois a separação de planejamento e execução mudou entre versões.

As entradas de estatísticas são diferenciadas por banco, usuário, query ID
e nível de execução. O coletor fixa banco e usuário e seleciona apenas nível
superior, sem misturar essas dimensões. Quando a coluna `toplevel` não existe,
exige `pg_stat_statements.track = top`. Compatibilidade com servidores antigos
não foi testada neste projeto.

Os tempos não incluem o tempo de planejamento registrado separadamente.
As estatísticas são acumuladas desde resets ou criação/recriação das entradas.
Entradas podem ser descartadas quando o limite da extensão é atingido. O
horário `collected_at` não representa o início do experimento, e uma leitura
enquanto o workload está em execução não representa sua rodada completa.

### Execução manual do experimento

Pré-requisitos: extensão funcionando, carga populada e teste funcional
aprovado. A consistência detalhada da Etapa 2 permanece pendente de
confirmação do autor. Finalize essa conferência antes da rodada definitiva.

1. No DBeaver, conectado ao banco experimental, execute o reset abaixo.
   **Ele descarta as métricas anteriores desse banco, sem apagar seus dados.**
   Salve qualquer resultado anterior que queira preservar e registre o horário.

```sql
SELECT public.pg_stat_statements_reset(
    dbid => (SELECT oid FROM pg_database WHERE datname = 'tcc_sql_optimizer')
);
```

2. Na raiz do projeto, no PowerShell, execute a carga completa e aguarde
   `Workload concluído: 730 execuções sem erro.`:

```powershell
.\.venv\Scripts\python.exe -m scripts.generate_workload
```

3. Somente se a carga concluir sem erro, execute o coletor:

```powershell
.\.venv\Scripts\python.exe -m src.collector --top 5
```

O comando exibe banco, usuário, versões, horário UTC, número de consultas
selecionadas e soma de chamadas, seguidos dos três rankings. O código de saída
é 0 em uma coleta com resultados e saídas solicitadas gravadas, 2 se o filtro
não encontrar registros e 1 para erros de configuração, banco ou exportação.

Com o reset restrito ao banco, o workload padrão completo e nenhuma consulta
manual adicional às tabelas, esperamos 12 consultas selecionadas e 730 chamadas.
No ranking de frequência, a consulta de cliente por chave primária deve ter
500 chamadas. Os valores de tempo e as demais posições serão obtidos pela
medição, não são fixados pelo código. Divergências de contagem exigem análise
antes de considerar a rodada válida.

Se houver erro no workload, envie a mensagem e não prossiga como se a rodada
tivesse concluído. O coletor pode mostrar uma carga parcial, mas isso deve ser
identificado como tal. A exportação foi adicionada na Etapa 6: o comando
padrão agora salva CSV e JSON. Use `--no-export` para apenas exibir os rankings.

### Diagnóstico opcional

Para exibir mais posições:

```powershell
.\.venv\Scripts\python.exe -m src.collector --top 12 --no-export
```

Para investigar SELECTs administrativos junto com os do experimento:

```powershell
.\.venv\Scripts\python.exe -m src.collector --all-selects --top 10 --no-export
```

Não repita reset ou workload para trocar apenas a quantidade de posições.
O coletor consulta as estatísticas existentes e não executa novamente o SQL
armazenado na coluna `query`.

## Etapa 6 — Exportação e preservação dos resultados

`src/exporter.py` utiliza somente os módulos padrão `csv`, `json`, `io`,
`pathlib` e `tempfile`; não é necessário instalar dependências adicionais.
O coletor exporta os mesmos registros usados nos três rankings, sem realizar
uma segunda consulta ao banco para cada formato.

### Formatos e localização

O comando padrão grava CSV e JSON:

```powershell
.\.venv\Scripts\python.exe -m src.collector --top 5
```

O caminho padrão é `results` na raiz do projeto, independentemente do diretório
de saída escolhido em comandos anteriores. Cada arquivo contém **todas** as
consultas selecionadas, não apenas as cinco posições exibidas em cada ranking.

Campos, nesta ordem:

```text
query_id,query,calls,total_exec_time,mean_exec_time,rows,impact_score,collected_at
```

- CSV: `results/query_metrics.csv`, separador vírgula, UTF-8 com BOM e cabeçalho.
  Aspas e quebras de linha do SQL são tratadas pelo módulo `csv`.
- JSON: `results/query_metrics.json`, lista de objetos, UTF-8, acentos
  preservados e indentação para leitura.
- Ambos são ordenados por tempo total decrescente, com desempate pelo ID.
- Os tempos são exportados sem o arredondamento de duas casas usado no terminal.
- O query ID é representado como texto na exportação. Isso preserva seus
  dígitos em leitores JSON/JavaScript; no Python, ele continua inteiro para
  classificação. Os campos de contagem e tempo são números no JSON.
- Para abrir o CSV no Excel, importe a coluna `query_id` como **Texto**.
  O arquivo CSV não carrega tipos de coluna, e conversão automática para
  número pode alterar IDs longos. Os decimais usam ponto.

Como o SQL pode ocupar várias linhas entre aspas, conte registros com um
leitor CSV, não pelo número de linhas físicas do arquivo.

### Opções de execução

Somente CSV:

```powershell
.\.venv\Scripts\python.exe -m src.collector --format csv
```

Somente JSON:

```powershell
.\.venv\Scripts\python.exe -m src.collector --format json
```

Somente rankings, sem criar nem substituir arquivos:

```powershell
.\.venv\Scripts\python.exe -m src.collector --no-export
```

Para preservar uma rodada em sua própria pasta:

```powershell
.\.venv\Scripts\python.exe -m src.collector --output-dir results/rodada_001
```

**Impacto local:** cada execução de exportação substitui os arquivos do
formato solicitado na pasta de destino. Para manter rodadas diferentes,
use uma pasta diferente em cada uma. Não há alteração de dados comerciais
nem reset pelo coletor. Conteúdo de `results` fica ignorado pelo Git.

Cada arquivo é escrito primeiro em um temporário no mesmo diretório e depois
substituído. Os dois arquivos não formam uma transação conjunta: se a gravação
do segundo falhar, o primeiro pode ter sido atualizado. O programa retorna
erro e orienta conferir os horários. Feche arquivos abertos em outros programas
antes de exportar novamente. Não repita o workload para corrigir erro de arquivo.

Uma coleta vazia retorna código 2 e não cria nem substitui resultados.
Arquivos antigos, caso existam, continuam representando a coleta anterior.

### Validação manual dos arquivos

Após a mensagem `Exportação concluída: 12 consultas em cada arquivo.`,
execute no PowerShell, na raiz do projeto:

```powershell
$tccCsv = @(Import-Csv -LiteralPath '.\results\query_metrics.csv' -Encoding UTF8)
$tccJsonDocument = Get-Content -LiteralPath '.\results\query_metrics.json' -Raw -Encoding UTF8 | ConvertFrom-Json
$tccJson = @(foreach ($item in $tccJsonDocument) { $item })

[PSCustomObject]@{
    ConsultasCSV = $tccCsv.Count
    ConsultasJSON = $tccJson.Count
    ChamadasCSV = ($tccCsv | Measure-Object -Property calls -Sum).Sum
    ChamadasJSON = ($tccJson | Measure-Object -Property calls -Sum).Sum
    ColetaCSV = $tccCsv[0].collected_at
    ColetaJSON = $tccJson[0].collected_at
}
```

Esperamos 12 registros em cada formato, 730 chamadas em cada um e horários
iguais. As colunas do CSV e os campos do JSON devem corresponder aos oito
campos apresentados acima. Confirme também que os IDs são preservados:

```powershell
Compare-Object -ReferenceObject @($tccCsv.query_id | Sort-Object) -DifferenceObject @($tccJson.query_id | Sort-Object)
```

O último comando não deve produzir diferenças. Esses comandos apenas leem
os arquivos locais, sem conexão com o PostgreSQL. Se utilizou `--output-dir`,
ajuste os caminhos para a pasta correspondente.

### Versionamento e registro do experimento

O repositório Git já existe na pasta do projeto. Depois de validar os arquivos,
o autor poderá registrar o código com os comandos abaixo. Eles não foram
executados pelo assistente:

```powershell
git status --short
git add README.md requirements.txt requirements-lock.txt .gitignore .env.example src scripts sql docs
git commit -m "Implementa prototipo inicial de coleta de metricas SQL"
git rev-parse HEAD
```

Registre o hash da revisão junto dos resultados, parâmetros, versões,
horário do reset e condições da máquina. O `.env` e os arquivos locais de
resultados não entram nesses comandos. Para preservar os resultados, use
pastas por rodada e uma cópia de segurança escolhida pelo autor.

O arquivo `docs/experiment_001.md` registra os resultados recebidos da primeira
rodada. Não contém uma exportação inventada das métricas que não apareceram
no terminal. A validação de consistência detalhada dos dados permanece pendente
até o autor enviar os resultados de `sql/validate_population.sql`.

## Etapa 7 — Análise preventiva antes da execução

### Objetivo e funcionamento

`src/analyzer.py` recebe um arquivo com exatamente um `SELECT` e solicita ao
PostgreSQL:

```sql
EXPLAIN (
    ANALYZE FALSE,
    VERBOSE TRUE,
    COSTS TRUE,
    SETTINGS TRUE,
    SUMMARY TRUE,
    FORMAT JSON
) ...
```

`ANALYZE FALSE` significa que a consulta candidata não é executada. O servidor
analisa sua sintaxe e produz um plano estimado em JSON. O analisador percorre a
árvore desse plano, consulta apenas metadados dos catálogos e, quando o Query ID
estiver disponível, procura métricas históricas correspondentes no
`pg_stat_statements`.

A conexão é aberta em modo somente leitura. Esta versão aceita apenas uma
instrução iniciada por `SELECT`, recusa `SELECT INTO` e recusa mais de uma
instrução no arquivo. CTEs iniciadas por `WITH` serão tratadas em uma evolução
posterior.

O planejamento ainda exige uma conexão com o PostgreSQL e pode aguardar
bloqueios de catálogo. Por isso, o programa limita o planejamento a 30 segundos
e a espera por bloqueios a 5 segundos. Ele não executa o `SELECT`, não usa
`EXPLAIN ANALYZE`, não cria índices e não reescreve o SQL.

### Regras iniciais

`src/plan_analyzer.py` produz alertas quando identifica:

- `SELECT *`;
- varredura sequencial com filtro em uma tabela estimada com pelo menos 50 mil
  linhas;
- função como `EXTRACT`, `LOWER` ou `DATE_TRUNC` aplicada em um filtro;
- ordenação estimada de pelo menos 10 mil linhas;
- `Nested Loop` com grande combinação estimada entre os ramos;
- resultado principal estimado em pelo menos 100 mil linhas;
- diferença de pelo menos dez vezes entre as linhas estimadas e a média histórica
  de linhas por execução, quando houver correspondência no histórico;
- presença de subplano.

Cada alerta mostra a evidência encontrada e uma sugestão de investigação. A
pontuação de 0 a 10 e o nível de atenção são heurísticos. Eles não representam
tempo previsto, probabilidade estatística nem garantia de lentidão. O custo do
PostgreSQL usa unidades internas do planejador e não deve ser interpretado como
milissegundos.

O plano estimado pode divergir da execução real por causa da distribuição dos
dados, estatísticas desatualizadas, parâmetros, cache, concorrência e recursos
da máquina. As recomendações devem ser validadas posteriormente por um
experimento controlado. Essa separação preserva a proposta do TCC: sugerir antes
da execução e medir depois, sem apresentar a estimativa como medição real.

### Primeira validação manual

`sql/candidate_query.sql` contém a consulta Q05, escolhida porque o experimento
anterior já mostrou custo real relevante. Na raiz do projeto, o autor executará:

```powershell
.\.venv\Scripts\python.exe -m src.analyzer --sql-file sql/candidate_query.sql
```

O resultado esperado começa com `ANÁLISE PREVENTIVA DA CONSULTA` e confirma
`Consulta executada: não (EXPLAIN com ANALYZE FALSE)`. Para essa consulta,
esperam-se alertas relacionados a `SELECT *`, varredura/filtro sobre a tabela de
pedidos, função sobre `data_pedido` e grande volume estimado. A forma exata do
plano cabe ao otimizador e pode variar.

Se o Query ID estimado corresponder ao workload já registrado, a seção de
histórico mostrará chamadas e tempos reais do `pg_stat_statements`. A ausência
de correspondência não impede a análise preventiva; ela apenas indica que o
histórico não foi relacionado nessa execução.

Como primeira hipótese de melhoria, `sql/candidate_query_range.sql` substitui
`EXTRACT(YEAR FROM p.data_pedido) = 2026` por um intervalo fechado no início e
aberto no fim. Essa forma permite ao planejador utilizar diretamente as
estatísticas da coluna de data. Nesta etapa, a alternativa também será analisada
somente com `EXPLAIN` e `ANALYZE FALSE`; ela não será executada para medir tempo.

```powershell
.\.venv\Scripts\python.exe -m src.analyzer --sql-file sql/candidate_query_range.sql
```

O objetivo imediato é comparar custo, linhas estimadas e alertas. Como ainda não
há índice adicional em `data_pedido` e aproximadamente metade dos pedidos está
em 2026, uma varredura sequencial ainda pode ser a escolha correta. Remover a
função pode melhorar a estimativa sem, por si só, garantir menor tempo real.

Depois de analisar os arquivos individualmente, `src/compare_plans.py` apresenta
os dois planos lado a lado. Ele solicita novamente apenas `EXPLAIN` com
`ANALYZE FALSE` e usa o histórico da original como referência, deixando explícita
a premissa de equivalência semântica:

```powershell
.\.venv\Scripts\python.exe -m src.compare_plans `
    --original sql/candidate_query.sql `
    --alternative sql/candidate_query_range.sql
```

O registro da primeira comparação está em
`docs/preventive_comparison_001.md`.

O segundo caso de validação utiliza a Q09. A forma original aplica `LOWER` à
coluna `clientes.email`; a alternativa faz comparação direta com o e-mail em
minúsculas, formato utilizado pelo gerador de dados. Como `email` possui uma
restrição `UNIQUE`, essa comparação verifica preventivamente se o plano passa de
varredura sequencial para acesso pelo índice existente:

```powershell
.\.venv\Scripts\python.exe -m src.compare_plans `
    --original sql/candidate_email_lower.sql `
    --alternative sql/candidate_email_direct.sql
```

Essa equivalência depende da regra de que os e-mails são armazenados de forma
normalizada em minúsculas. Em outro sistema, remover `LOWER` sem garantir essa
regra poderia alterar o resultado da consulta.

Depois da avaliação preventiva, a hipótese pode ser medida de forma controlada:

```powershell
.\.venv\Scripts\python.exe -m scripts.validate_recommendation `
    --original sql/candidate_email_lower.sql `
    --alternative sql/candidate_email_direct.sql `
    --calls 100
```

Esse comando é diferente dos anteriores: ele **executa cada SELECT 100 vezes**,
em ordem intercalada e pseudoaleatória, consome os resultados e acrescenta 200
chamadas ao `pg_stat_statements`. Ele não altera linhas, tabelas, índices ou
configurações e não reseta as estatísticas. O programa captura as métricas antes
e depois para calcular apenas os deltas dessa rodada, além dos tempos percebidos
pelo cliente Python. Evite executar as mesmas consultas em outra sessão durante
o teste.

O programa também compara os primeiros resultados das duas formas. Essa
verificação é adequada ao caso de uma linha da Q09, mas não constitui um
verificador geral de equivalência SQL.

Para analisar outra consulta, copie somente um `SELECT` para um arquivo SQL e
informe seu caminho em `--sql-file`. Use `--no-history` para ignorar o histórico
e `--timeout-seconds N` para mudar o limite de planejamento entre 1 e 600
segundos. Não inclua dados sensíveis no arquivo de teste.

## Limites desta entrega

O protótipo identifica e ordena consultas com base em estatísticas agregadas e
agora interpreta um conjunto pequeno de características do plano estimado. Não
lê logs individuais, não prevê o tempo real, não calcula causalidade e não
aplica otimizações. `EXPLAIN ANALYZE`, criação automática de índices, reescrita
automática, IA, integração com DBeaver/pgAdmin, API pública e Docker
permanecem fora do escopo. A interface gráfica usa um servidor HTTP Python
restrito a este computador; não é um serviço preparado para publicação.

A exportação CSV/JSON foi executada e conferida na reinstalação de 12/10/2026.
A interface também permite baixar histórico, análises e comparações em JSON.

## Referências

- [Instalação do Psycopg 3](https://www.psycopg.org/psycopg3/docs/basic/install.html)
- [Conexões e cursores do Psycopg 3](https://www.psycopg.org/psycopg3/docs/basic/usage.html)
- [Restrições no PostgreSQL](https://www.postgresql.org/docs/16/ddl-constraints.html)
- [COPY no Psycopg 3](https://www.psycopg.org/psycopg3/docs/basic/copy.html)
- [ANALYZE no PostgreSQL 18](https://www.postgresql.org/docs/18/sql-analyze.html)
- [Cursor.stream no Psycopg 3](https://www.psycopg.org/psycopg3/docs/api/cursors.html#psycopg.Cursor.stream)
- [pg_stat_statements no PostgreSQL 18](https://www.postgresql.org/docs/18/pgstatstatements.html)
- [EXPLAIN no PostgreSQL 18](https://www.postgresql.org/docs/18/sql-explain.html)
- [Leitura de planos com EXPLAIN](https://www.postgresql.org/docs/18/using-explain.html)
- [Instalador PostgreSQL para Windows](https://www.postgresql.org/download/windows/)
- [Módulo csv do Python](https://docs.python.org/3/library/csv.html)
- [Módulo json do Python](https://docs.python.org/3/library/json.html)
