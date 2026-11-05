# TCC — Análise e otimização de consultas a partir de logs

Esta é a nova versão, em `Desktop/TCC-Logs`. A pasta original `Desktop/TCC` foi preservada. O arquivo `BACKUP.json` identifica a cópia de segurança dos arquivos. Existe também um backup PostgreSQL em `Desktop/TCC-Banco-Backup-20261031.dump`.

## Abrir

Dê dois cliques em **Abrir interface.cmd** nesta pasta. A nova interface abre em **http://127.0.0.1:8767**. A versão anterior utiliza a porta 8765.

Esta cópia já possui ambiente Python e configuração local, apontando exclusivamente para **tcc_sql_optimizer_logs**. Esse banco foi criado a partir de um backup do original, com as cinco tabelas e seus dados. Não é necessário recriar ou popular as tabelas.

## Atualizar consultas executadas no DBeaver

1. No DBeaver, conecte ao banco **tcc_sql_optimizer_logs**, na mesma instância configurada no `.env` desta pasta.
2. Execute SELECTs nas tabelas da aplicação, com ou sem `public.`: filtros, JOINs, agregações e CTEs somente de leitura são reconhecidos.
3. Na interface, clique em **Atualizar consultas**. A primeira leitura traz o acumulado disponível; as seguintes comparam snapshots.
4. A listagem **PostgreSQL** indica consultas novas, atualizadas ou sem alteração. **Investigar** abre tempos, chamadas, linhas, leituras, alertas e plano estimado quando disponível.
5. SQL normalizado com `$1`, `$2` etc. pode receber um plano genérico. Para analisar valores específicos e obter propostas dependentes deles, informe a lista JSON dos parâmetros na própria tela. Esses valores não são recuperáveis a partir do pg_stat_statements e não são inventados pelo sistema.
6. Baixe a análise em JSON ou siga para comparação e medição. As regras de otimização continuam com o escopo descrito abaixo.

Essa função apenas lê estatísticas: não executa os SELECTs observados nem reseta o pg_stat_statements. Ela captura consultas de qualquer ferramenta e usuário visível na mesma base; não atribui uma chamada especificamente ao DBeaver. Consultas de teste e outras consultas do sistema nas tabelas também podem aparecer.

Os snapshots são persistidos no SQLite local, separados dos registros individuais importados de log. A alternância **PostgreSQL / Arquivos de log** preserva as duas fontes sem somar a mesma execução duas vezes. Consultas administrativas de catálogo ficam fora da listagem padrão.

Detalhes de configuração, parâmetros e tratamento de resets: [guia de sincronização](docs/sincronizacao_postgresql.md).

## Usar

1. Abra **Consultas SQL → Arquivos de log**. Já há registros reais coletados nos testes de integração.
2. Importe um log ou clique em **Coletar exemplos reais**. A coleta executa os 12 exemplos uma vez cada no banco copiado e lê somente seus registros identificados no log do PostgreSQL.
3. Ordene por tempo acumulado, média ou frequência e clique em **Investigar**.
4. Examine a evidência e, quando houver uma proposta, clique em **Comparar e validar proposta**. O sistema preenche os dois SQLs.
5. Use **Comparar planos** para examinar estimativas ou **Executar e medir** para executar o teste real.
6. Os experimentos concluídos ficam salvos na primeira tela. O relatório JSON inclui SQL, amostras individuais, planos reais e método.

## O que foi implementado

- Importação de arquivos stderr `.log`/`.txt`, `csvlog` e `jsonlog` do PostgreSQL, incluindo JSONL e consultas multilinha. Mensagens de duração em inglês e português são reconhecidas. Só entram registros completos de SELECT com duração; Parse e Bind não são contados como novas execuções.
- Persistência de cada execução (duração, SQL e contexto disponível), agrupamento pela estrutura SQL e banco de origem, rankings e deduplicação de importação idêntica pelo hash do conteúdo.
- Investigação do SQL efetivamente registrado. Quando o grupo contém valores diferentes, a análise e o teste usam a variante com maior duração registrada, não uma média fictícia de SQLs.
- Reescritas automáticas com árvore sintática PostgreSQL, limitadas aos casos descritos abaixo.
- Validação por execução real em transação somente leitura e fotografia consistente dos dados. Todas as linhas das duas versões participam da comparação de assinaturas; não se compara apenas a primeira linha.
- Medição do servidor via EXPLAIN ANALYZE, BUFFERS e TIMING FALSE. Uma execução de aquecimento por versão e de 3 a 50 repetições intercaladas com semente 2026. Mediana, média, extremos, desvio padrão, amostras e planos ficam no relatório.
- Resultados mais rápidos e mais lentos são apresentados. A redução é calculada pela mediana da rodada; não é uma conclusão de significância estatística nem uma previsão para outros ambientes.

## Casos de reescrita suportados

1. Predicado isolado `EXTRACT(YEAR FROM coluna) = ano_literal`: substitui por intervalo apenas quando o tipo real da coluna é DATE ou TIMESTAMP sem fuso.
2. Predicado isolado `LOWER(coluna) = valor`: remove LOWER somente depois de verificar, no servidor, que todos os valores atuais da coluna já são iguais a LOWER(coluna). Preserva o literal ou parâmetro recebido.
3. Subconsulta escalar simples com `COUNT(*)` correlacionado por igualdade: agrega a tabela uma vez e usa LEFT JOIN e COALESCE para manter as contagens zero. Preserva o alias da coluna, filtros externos e ordenação.

As regras aceitam uma consulta SELECT e reescrevem apenas os padrões descritos. A regra de contagem exige uma subconsulta escalar sem filtros extras, agrupamentos ou limites e não reescreve SELECT *. Não fazem substituição de texto dentro de strings. Expressões não suportadas continuam disponíveis para investigação e comparação manual. A proposta não promete ganho: o teste determina o resultado observado.

## Logs e escopo

A captura automática foi verificada com o PostgreSQL local, coletor de logs ligado e saída stderr em `.log`. Usa `log_min_duration_statement=0` e idioma C somente na sessão de coleta, sem mudar a configuração global do servidor. A conta configurada precisa de permissão para esses ajustes de sessão e leitura do log.

Logs importados precisam conter o SQL e sua duração. Parâmetros `$1` etc. não são automaticamente substituídos a partir de linhas DETAIL. Consultas com parâmetros precisam ser materializadas para reproduzir a execução. O banco de origem é preservado quando informado; a investigação está restrita ao banco desta cópia. Logs stderr sem esse metadado usam a conexão configurada para análise, então devem corresponder ao mesmo esquema.

A ferramenta usa PostgreSQL e regras explícitas; não utiliza IA nem se apresenta como otimizador universal. Não cria índices automaticamente. Os testes são limitados a SELECTs de tabelas public e funções aceitas, têm tempo máximo e não alteram registros. As medições acrescentam atividade ao histórico do banco copiado. Não existe monitoramento contínuo em segundo plano: a coleta é iniciada pelo usuário, pela importação de arquivos ou pela sincronização manual de estatísticas.

## Evidências locais

- `results/log_sources/`: conteúdo original dos lotes importados, identificado por SHA-256.
- `results/logs.sqlite3`: execuções individuais, lotes e experimentos salvos.
- Relatório completo: botão de download em cada experimento.
- `results/integration-validation.json`: registro da verificação desta versão.

O backup é local: ele preserva arquivos e banco, mas não é uma cópia em outro dispositivo. As pastas de vídeo, caches, temporários, ambiente virtual antigo e histórico Git permaneceram na pasta original e não fazem parte do ZIP do projeto SQL. O código atual, arquivos não versionados, interface, configuração, documentação e resultados foram incluídos e conferidos.

## Desenvolvimento

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -X utf8 -m src.webapp --open
```

As descrições da versão anterior foram preservadas em `docs/README-versao-anterior.md` e nos demais documentos históricos. Elas não descrevem o escopo atual.

Referências de implementação: [logs PostgreSQL 18](https://www.postgresql.org/docs/18/runtime-config-logging.html) e [pglast](https://pglast.readthedocs.io/en/latest/api.html).

## Código sugerido e projeção

O popup Investigar mostra o SQL alternativo completo quando uma regra se aplica. A comparação automática mostra custo estimado, operações de acesso e remoção de subplanos. Planos com parâmetros desconhecidos são identificados como genéricos.

A projeção não transforma custo em milissegundos. **Medir ganho** executa três repetições por versão, após aquecimento, confere as assinaturas dos resultados e mostra as medianas e a variação observada. Se houver parâmetros, o usuário informa os valores antes de medir. Os testes e relatórios são salvos e exportáveis em JSON. Uma rodada não é uma garantia para outras entradas ou condições do banco.
