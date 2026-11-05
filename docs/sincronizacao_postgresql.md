# Sincronização manual das consultas observadas no PostgreSQL

## Usar com o DBeaver

Abra a conexão do DBeaver para **tcc_sql_optimizer_logs**, usando a mesma instância (host/porta) configurada no `.env` de **TCC-Logs**. Essa é a base copiada utilizada pela nova versão; a pasta TCC e o banco tcc_sql_optimizer da versão anterior continuam separados.

Execute consultas nas tabelas do banco. Depois, abra http://127.0.0.1:8766 e clique em **Atualizar consultas**. Nenhum cadastro de SQL é necessário. A interface informa o banco e o horário da última leitura.

Na primeira sincronização, todos os SELECTs elegíveis já presentes nas estatísticas são cadastrados como novos. Isso inclui execuções anteriores ao primeiro clique. As próximas leituras classificam cada entrada como nova, atualizada ou sem alteração.

SQLs de estrutura equivalente podem corresponder à mesma entrada. Portanto, executar cinco textos com valores diferentes pode produzir menos de cinco linhas. A origem não é atribuída especificamente ao DBeaver: o pg_stat_statements não guarda o nome da ferramenta por chamada. Também podem aparecer consultas de testes e do próprio sistema que leem as tabelas.

## Pré-requisitos

O ambiente local foi verificado com PostgreSQL 18.6, pg_stat_statements instalado, carregado e rastreamento ativo. Não foi necessário mudar a configuração global do servidor para implementar a sincronização.

Em outra instalação, o módulo deve estar em shared_preload_libraries, a extensão deve existir no banco e o rastreamento deve estar ativo. Para enxergar textos e identificadores de consultas feitas por outros usuários, a conta de coleta precisa das permissões correspondentes, como pg_read_all_stats. Sem isso, a interface informa a visibilidade limitada. O sistema não concede privilégios automaticamente.

O rastreamento por estatísticas não depende de habilitar o registro de todos os comandos nos arquivos de log. **Importar log**, **Coletar exemplos reais** e **Atualizar consultas** são operações distintas.

## O que é coletado

- Banco, usuário, Query ID e nível superior da consulta.
- SQL representativo normalizado pelo PostgreSQL.
- Chamadas, tempo total e médio, linhas retornadas.
- Blocos compartilhados encontrados em cache, lidos, sujos e escritos, quando disponíveis.
- Blocos locais e temporários, tempos de I/O quando disponíveis.
- Tempos extremos e desvio padrão, quando disponíveis.
- stats_since, minmax_stats_since e reinício global das estatísticas, quando disponíveis.

A listagem aceita SELECTs e CTEs somente de leitura sobre tabelas e views de usuário. Nomes sem schema, como `FROM clientes`, são reconhecidos. Consultas administrativas restritas aos catálogos, comandos de alteração e leituras da própria extensão não entram no escopo padrão. A tabela mostra a última observação disponível; não são logs individuais.

## Snapshots e diferenças

O arquivo `results/logs.sqlite3` guarda três estruturas adicionais:

- `sync_runs`: contexto e resumo de cada sincronização bem-sucedida.
- `observed_statements`: última observação de cada identidade estável.
- `statement_snapshots`: cópia das métricas de cada consulta em cada leitura.

A identidade inclui fonte/instância, banco, usuário, Query ID e nível da consulta. Atualizações fazem upsert nessa identidade e não inserem uma nova consulta por execução. Query IDs e OIDs são transmitidos como texto para evitar perda de precisão no navegador.

Diferenças são calculadas sobre contadores acumulados. Por exemplo: se calls passa de 10 para 13 e o tempo total passa de 20 para 29 ms, o intervalo observado contém 3 chamadas e 9 ms, com média de 3 ms. A média do intervalo é calculada pela diferença dos totais dividida pela diferença das chamadas; médias acumuladas não são subtraídas.

Na primeira observação de uma entrada, não existe um delta conhecido. Quando o reinício global muda, stats_since muda, contadores diminuem ou uma entrada reaparece após ausência, o sistema inicia uma nova base. Não cria diferenças negativas nem soma períodos desconectados como se fossem contínuos. A ausência de uma entrada pode resultar de reset, remoção pelo limite da extensão ou mudança de visibilidade; o sistema preserva sua última observação e a sinaliza como ausente.

Uma falha de conexão ou de leitura não substitui o snapshot anterior. Uma leitura mais antiga não pode sobrescrever uma leitura mais recente. Recarregar o navegador apenas lê os dados locais; sincronizar com o PostgreSQL depende do botão.

## Análise e valores dos parâmetros

**Investigar** sempre apresenta as métricas do snapshot selecionado, incluindo chamadas, tempo, linhas e leituras disponíveis. Os alertas de métricas destacam tempo médio, participação no tempo acumulado, volume de linhas e uso de blocos temporários/leituras, conforme os limiares explícitos das regras.

Quando o SQL contém `$1`, `$2` etc., o sistema tenta `EXPLAIN (GENERIC_PLAN TRUE, ANALYZE FALSE)`. Esse plano é genérico, não depende dos valores utilizados nas execuções anteriores e não executa a consulta candidata. A inferência de tipos pode falhar para alguns SQLs; nesse caso, as métricas continuam acessíveis e exportáveis.

Para obter um plano com valores concretos, preencha a lista JSON, por exemplo `["cliente123@example.com"]` para um SQL com um parâmetro. Os valores são vinculados pela árvore SQL, sem substituir texto dentro de strings. Eles não são recuperados nem adivinhados a partir das estatísticas.

Com um plano disponível, as regras podem oferecer uma proposta, inclusive parametrizada quando o padrão permite. Os valores precisam ser informados antes de medir o ganho. A comparação de planos e o teste de execuções permanecem disponíveis. As regras automáticas atuais cobrem igualdade por ano, LOWER sobre coluna normalizada e COUNT(*) escalar correlacionado simples; a sincronização não amplia automaticamente esse conjunto de regras.

O plano é produzido na conexão do sistema, com suas permissões e resolução de nomes. Ele não reconstrói o plano histórico de outra sessão. O tempo médio das estatísticas é medido; custo do plano e linhas estimadas continuam sendo estimativas. Blocos compartilhados lidos não equivalem necessariamente a acesso físico ao disco. Tempos de I/O desabilitados não são apresentados como medições de zero.

## Exportação e verificação

**Baixar análise em JSON** inclui a entrada observada, identidade, métricas, contexto do snapshot, delta, alertas, plano disponível e propostas. O SQL com os valores fornecidos também faz parte do resultado da análise correspondente.

Os testes desta implementação estão documentados em `results/sync-integration-validation.json` e `results/sync-browser-validation.json`. A validação real usou conexões PostgreSQL externas ao servidor HTTP do sistema, não automação da interface do DBeaver: cinco estruturas novas foram identificadas, três repetições atualizaram a mesma identidade e uma leitura seguinte sem execuções não gerou alterações. Também foram testados plano genérico, vinculação de parâmetros, JSON, comparação, medição e preservação da fonte de arquivos de log.

Referências: [pg_stat_statements PostgreSQL 18](https://www.postgresql.org/docs/18/pgstatstatements.html) e [EXPLAIN / GENERIC_PLAN](https://www.postgresql.org/docs/18/sql-explain.html).

## Ordenação por data e resumo da análise

A listagem abre em **Mais recentes**, com a opção **Mais antigas** no seletor. Na fonte PostgreSQL, **Atividade detectada** é a sincronização em que uma entrada foi descoberta, atualizada ou reiniciada. Ler novamente uma entrada sem mudanças não altera essa data. Datas anteriores à implementação são recuperadas dos snapshots salvos. Isso não representa o horário exato da execução, que não é fornecido por pg_stat_statements.

Na fonte de arquivos de log, a ordenação utiliza o último horário registrado no grupo. Registros sem data ficam ao final. As opções de tempo acumulado, tempo médio e frequência continuam disponíveis.

A análise exibe SQL, resumo de desempenho e ações principais. Alertas, plano, parâmetros e informações técnicas ficam recolhidos e podem ser abertos individualmente; a exportação JSON mantém as evidências completas.
