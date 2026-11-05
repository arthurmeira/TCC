# Validação da aplicação — 20/10/2026

## Diagnóstico

O coletor encontrou zero consultas experimentais antes da validação, embora
o banco estivesse conectado e com as tabelas populadas. O campo stats_reset
indicou 20/10/2026 14:44:34 (America/Sao_Paulo), praticamente no mesmo momento
da inicialização do servidor. pg_stat_statements.save estava ligado.

O log PostgreSQL de inicialização registrou interrupção da execução anterior,
encerramento incorreto e recuperação automática. Isso é compatível com a
perda das estatísticas após interrupção; não foi determinado o evento externo
que causou o encerramento (queda de energia, encerramento forçado etc.).
Não foi feito reset das estatísticas nesta validação.

## Ações e resultados

- Executada a carga de 12 consultas, totalizando 730 chamadas sem erro.
- Resultados desta rodada salvos separadamente dos experimentos do TCC.
- 7 testes HTTP automatizados passaram, incluindo entrada inválida, origem
  externa, acesso a arquivos internos e erros simulados do banco.
- 30 verificações de integração passaram usando PostgreSQL real: 12 análises,
  duas comparações, consulta sem histórico, rejeições de SQL, recursos HTTP,
  associação dos exemplos e integridade da base.
- As ações preventivas mantiveram o histórico em 730 chamadas.
- Contagens: clientes 100.000; produtos 50.000; pedidos 1.000.000;
  itens_pedido 2.498.714; pagamentos 1.000.000.
- Os cinco indicadores de consistência de sql/validate_population.sql foram zero.
- As consultas de diagnóstico de dados usaram rastreamento desativado apenas
  na própria transação para não acrescentar consultas de auditoria ao histórico.
- No navegador: navegação entre as quatro abas, análise Q05 com histórico
  de 15 chamadas, comparação de e-mail Seq Scan → Index Scan e guia didático.
- Conferida a sintaxe de web/app.js com node --check.
- Servidor local reiniciado para carregar a atualização, mantendo 127.0.0.1:8765.

## Correções

- A tela vazia explica que analisar/comparar não geram histórico e orienta
  executar Gerar historico.cmd e depois atualizar a leitura.
- A visão geral informa o último reinício das estatísticas e o escopo da coleta.
- Metadados de coleta agora incluem stats_reset e server_started_at.
- Adicionado limite de 10 segundos às consultas do coletor.
- Guia esclarece quando consultas do DBeaver aparecem no histórico.

## Evidências

Em results/validacao_2026-10-20:
workload.log; query_metrics.csv; query_metrics.json; overview.json;
integration.json; server.log; server-errors.log.
O script de integração está em tmp/validate_app_current.py.

## Limites

Esta validação comprova os cenários executados no ambiente local atual.
Não é auditoria de segurança para publicação na Internet, teste de carga
concorrente ou estudo de usabilidade. O usuário do banco atual é postgres;
publicação futura exige configuração própria, autenticação e permissões restritas.
Não foi reiniciado o PostgreSQL para provocar outra perda de estatísticas.
Os arquivos exportados preservam a rodada, mas a interface continua mostrando
o histórico vivo: ela não importa automaticamente arquivos antigos.
Os testes automatizados de falhas de conexão usam simulação; não foi necessário
derrubar o banco em uso para testar esse tratamento.
