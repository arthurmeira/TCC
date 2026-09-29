# TCC — Análise de desempenho de consultas SQL

Protótipo experimental do Trabalho de Conclusão de Curso de Ciência da
Computação: **Análise e otimização de consultas SQL com base em logs de
execução em bancos de dados relacionais**.

O objetivo inicial é gerar uma carga controlada, coletar estatísticas de
execução e identificar consultas com maior tempo total, tempo médio e
frequência. O `pg_stat_statements` fornece estatísticas agregadas por consulta,
não um log individual de cada execução.

## Estado atual

Etapa 1 validada pelo autor: as cinco tabelas foram listadas no DBeaver e
o diagnóstico Python conectou ao banco `tcc_sql_optimizer` com sucesso.

Etapa 2 preparada: gerador de dados e consultas de validação disponíveis.
A carga ainda não foi executada nem validada. O assistente apenas criou
e revisou os arquivos; toda execução Python/SQL fica a cargo do autor.

Nenhuma funcionalidade de otimização automática, análise de planos,
criação de índices adicionais, IA, API ou interface gráfica está incluída.

## Tecnologias

- PostgreSQL e, em etapa posterior, `pg_stat_statements`.
- Python 3.12 ou superior e Psycopg 3 (o gerador usa `itertools.batched`).
- `python-dotenv` para carregar a configuração local.
- DBeaver para administração manual do banco.
- Git para versionamento.

Versões informadas pelo autor durante a validação:

| Componente | Versão |
| --- | --- |
| Python | 3.14.3 |
| PostgreSQL | 18.1, Windows 64 bits |
| Psycopg / psycopg-binary | 3.3.6 |
| python-dotenv | 1.2.3 |
| tzdata | 2026.4 |

Os intervalos em `requirements.txt` ainda não fixam versões exatas. Para
reproduzir os dados, registre também a revisão do código, a versão Python,
a semente e os argumentos utilizados. O tempo de execução depende do
hardware, da configuração do servidor e das condições de cada execução.

## Estrutura atual

```text
TCC/
├── README.md
├── requirements.txt
├── .env.example
├── .gitignore
├── sql/
│   ├── schema.sql
│   └── validate_population.sql
├── scripts/
│   ├── .gitkeep
│   ├── __init__.py
│   └── populate_database.py
├── src/
│   ├── __init__.py
│   ├── config.py
│   └── database.py
└── results/
    └── .gitkeep
```

A pasta TCC é a raiz do projeto e já contém o repositório Git. Os arquivos
`.gitkeep` apenas permitem versionar as pastas inicialmente vazias.

## Configuração e conexão

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

Este é o roteiro previsto, ainda não executável de ponta a ponta. Cada
passo receberá instruções e será validado manualmente antes do seguinte:

1. Conferir as instalações de Python, PostgreSQL e DBeaver.
2. Preparar o ambiente virtual, instalar dependências e configurar o `.env`.
3. Criar o banco experimental e validar a conexão.
4. Executar e validar `sql/schema.sql`.
5. Gerar e validar os dados fictícios (Etapa 2).
6. Preparar as consultas e o gerador de carga (Etapa 3).
7. Habilitar e validar `pg_stat_statements` (Etapa 4).
8. Implementar a coleta e os rankings (Etapa 5).
9. Implementar as exportações e completar a documentação (Etapa 6).
10. Resetar as estatísticas do experimento, executar a carga e coletar os resultados.

Os comandos completos serão adicionados conforme as etapas forem
preparadas e validadas. Nenhum comando de banco é executado automaticamente.

Os arquivos de saída previstos são `results/query_metrics.csv` e
`results/query_metrics.json`; eles ainda não são gerados nesta etapa.

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

## Referências

- [Instalação do Psycopg 3](https://www.psycopg.org/psycopg3/docs/basic/install.html)
- [Conexões e cursores do Psycopg 3](https://www.psycopg.org/psycopg3/docs/basic/usage.html)
- [Restrições no PostgreSQL](https://www.postgresql.org/docs/16/ddl-constraints.html)
- [COPY no Psycopg 3](https://www.psycopg.org/psycopg3/docs/basic/copy.html)
- [ANALYZE no PostgreSQL 18](https://www.postgresql.org/docs/18/sql-analyze.html)
