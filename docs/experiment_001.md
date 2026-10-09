# Primeiro experimento — registro dos resultados informados pelo autor

Este registro foi elaborado a partir das saídas de terminal e da contagem
no DBeaver enviadas pelo autor. O assistente não executou o experimento.
Os tempos abaixo são os valores arredondados exibidos no terminal; não
substituem os arquivos CSV/JSON com a precisão da coleta.

## Ambiente e execução

- PostgreSQL 18.1, Windows 64 bits; pg_stat_statements 1.12.
- Python 3.14.3 e Psycopg 3.3.6.
- Banco `tcc_sql_optimizer`, usuário `postgres`.
- Carga padrão: 100.000 clientes, 50.000 produtos, 1.000.000 pedidos,
  2.498.714 itens e 1.000.000 pagamentos.
- Gerador e workload usados com seus parâmetros padrão, semente 2026.
- Teste funcional: 12 consultas sem erro, em 14,3 segundos no cliente.
- Workload completo: 730 execuções sem erro, em 103,2 segundos no cliente.
- Coleta apresentada: `2026-09-29T17:48:14+00:00` (UTC).
- Coletor: 12 consultas selecionadas, 730 chamadas e 13 entradas excluídas.

O horário do reset não foi enviado. As consultas detalhadas de consistência
e distribuição da Etapa 2 ainda não tiveram resultados confirmados pelo autor.
A exportação é uma etapa posterior à saída de terminal registrada aqui.

## Principais resultados do servidor

| Critério | Consulta local | Query ID | Chamadas | Tempo total (ms) | Tempo médio (ms) |
| --- | --- | --- | ---: | ---: | ---: |
| Maior tempo total | Q05 — JOIN com EXTRACT sobre data | -4437562662800320218 | 15 | 42.472,08 | 2.831,47 |
| Maior tempo médio | Q12 — leitura de todos os itens | -8969517312704176576 | 1 | 6.795,63 | 6.795,63 |
| Maior frequência | Q01 — cliente por chave primária | -2748476724609182739 | 500 | 9,25 | 0,02 |

A correspondência Q01/Q05/Q12 foi identificada pelo SQL exibido nos rankings.
Os nomes locais não fazem parte do query ID calculado pelo PostgreSQL.

Q05 retornou 7.495.140 linhas acumuladas em 15 execuções; Q12 retornou
2.498.714 linhas em uma execução; Q01 retornou 500 linhas em 500 execuções.

## Interpretação inicial e limites

Os três critérios destacam comportamentos diferentes: a consulta de maior
custo acumulado não foi a de maior tempo por execução nem a mais frequente.
Q01 teve muitas chamadas, mas pequeno tempo total de execução no servidor.

Q12 foi medida uma única vez nesta rodada. Seu tempo médio corresponde a
essa observação, não a uma estimativa robusta obtida com repetições.

Os resultados descrevem uma rodada, com valores de filtros fixos e caches
influenciados pela sequência de consultas. O volume retornado e a transferência
também influenciam a execução; não foram analisados planos nem identificadas
causas específicas de lentidão. Não se conclui, somente com estes rankings,
que uma consulta precise de um índice ou de reescrita.

`impact_score = mean_exec_time * calls` reproduz aproximadamente o tempo total.
O indicador ainda não oferece uma dimensão independente de impacto.

Ao exportar novamente sem repetir o workload ou resetar estatísticas,
`collected_at` será o horário da nova leitura. Os valores devem permanecer
compatíveis se nenhuma nova execução das consultas selecionadas ocorrer.
