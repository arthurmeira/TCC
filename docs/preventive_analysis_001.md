# Análise preventiva 001 — consulta Q05

## Objetivo

Validar a primeira versão do analisador preventivo, verificando se é possível
examinar uma consulta antes de sua execução, obter o plano estimado do
PostgreSQL e relacioná-lo ao histórico já coletado pelo `pg_stat_statements`.

## Consulta analisada

```sql
SELECT *
FROM public.pedidos AS p
JOIN public.clientes AS c ON c.id = p.cliente_id
WHERE EXTRACT(YEAR FROM p.data_pedido) = 2026;
```

A consulta corresponde à Q05 da carga experimental. Ela havia sido executada
15 vezes durante o workload completo.

## Método

O autor executou manualmente, em 8 de outubro de 2026:

```powershell
.\.venv\Scripts\python.exe -m src.analyzer --sql-file sql/candidate_query.sql
```

O programa utilizou `EXPLAIN` em formato JSON com `ANALYZE FALSE`. Portanto, a
consulta candidata não foi executada nessa análise. O programa também consultou
metadados das relações e procurou o Query ID no histórico do
`pg_stat_statements`.

## Resultado do plano estimado

| Métrica | Resultado |
| --- | ---: |
| Query ID | -4437562662800320218 |
| Nó principal | Gather |
| Nós no plano | 5 |
| Custo total estimado | 19.003,00 unidades do planejador |
| Linhas de saída estimadas | 5.000 |
| Tempo de planejamento | 10,68 ms |

As relações reconhecidas foram `public.clientes`, com aproximadamente 100 mil
linhas e 21,0 MB, e `public.pedidos`, com aproximadamente 1 milhão de linhas e
88,3 MB.

## Histórico real relacionado

O Query ID foi encontrado no `pg_stat_statements`:

| Métrica histórica | Resultado |
| --- | ---: |
| Execuções | 15 |
| Tempo total | 42.472,08 ms |
| Tempo médio | 2.831,47 ms |
| Linhas acumuladas | 7.495.140 |
| Média de linhas por execução | 499.676 |

O plano estimou 5 mil linhas, enquanto o histórico mostrou média de 499.676
linhas por execução. Assim, a estimativa foi aproximadamente 99,9 vezes menor
que o resultado histórico médio.

## Alertas produzidos

A primeira execução classificou a consulta com nível de atenção médio, 6 de 10,
e apresentou três indícios:

1. uso de `SELECT *`;
2. varredura sequencial com filtro sobre `public.pedidos`;
3. aplicação de `EXTRACT` à coluna `data_pedido` no filtro.

Depois dessa validação, o protótipo recebeu uma quarta regra: quando o Query ID
possui histórico, ele compara as linhas estimadas do plano com a média real de
linhas por execução. Uma diferença de pelo menos dez vezes passa a gerar um
alerta de alta severidade.

## Interpretação

O experimento comprovou que o protótipo consegue analisar o plano sem executar
o `SELECT` e relacionar a consulta candidata com medições anteriores. Neste caso,
o histórico reforçou que a consulta merece atenção: além do tempo médio próximo
de 2,8 segundos, o planejador subestimou fortemente o volume retornado.

Essa divergência pode influenciar a escolha das operações do plano. A função
aplicada sobre a data também dificulta uma estimativa seletiva e sugere comparar,
em uma etapa posterior, o filtro atual com um intervalo direto de datas. Ainda
assim, esta execução isolada não prova causalidade nem comprova que uma
reescrita ou um índice produzirá melhoria. Essas hipóteses precisam ser
avaliadas por um experimento controlado.
