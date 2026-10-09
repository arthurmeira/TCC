# Comparação preventiva 002 — função LOWER e índice de e-mail

## Objetivo

Verificar se o analisador preventivo identifica o efeito de aplicar uma função
à coluna `clientes.email` e se uma comparação direta permite ao PostgreSQL
considerar o índice único já existente nessa coluna.

## Consultas

A consulta original corresponde à Q09 do workload:

```sql
SELECT id, nome, email, cidade, estado
FROM public.clientes
WHERE LOWER(email) = 'cliente123@example.com';
```

A alternativa utiliza a regra conhecida do conjunto sintético, no qual todos os
e-mails são armazenados em letras minúsculas:

```sql
SELECT id, nome, email, cidade, estado
FROM public.clientes
WHERE email = 'cliente123@example.com';
```

## Resultados preventivos

| Métrica | Consulta original | Comparação direta |
| --- | ---: | ---: |
| Query ID | 4202338916568540003 | -8998468401231755824 |
| Nó principal | Seq Scan | Index Scan |
| Nós no plano | 1 | 1 |
| Custo estimado | 2.868,00 | 8,44 |
| Linhas estimadas | 500 | 1 |
| Tempo de planejamento observado | 2,31 ms | 0,08 ms |
| Nível heurístico | Alto, 8/10 | Baixo, 0/10 |

O histórico da consulta original registrava uma linha por execução. Seu plano
estimou 500 linhas, resultando em erro relativo de 49.900%. A alternativa
estimou exatamente uma linha, com erro relativo zero em relação a essa
referência. O custo estimado diminuiu 99,71%.

## Interpretação

O plano original não conseguiu utilizar diretamente o índice único de e-mail
porque a expressão avaliada era `LOWER(email)`, e não a coluna indexada. Na
alternativa, o plano mudou de `Seq Scan` para `Index Scan`. Esse é um indício
preventivo forte de que a comparação direta pode reduzir o trabalho necessário.

O resultado ainda não mede o tempo real da alternativa. O custo do planejador
não é expresso em milissegundos, e o tempo de planejamento de uma única chamada
pode variar por cache e ordem de execução. A próxima avaliação deve executar as
duas formas com a mesma frequência e comparar os deltas de tempo registrados
no `pg_stat_statements`.

A equivalência semântica depende da normalização dos e-mails em minúsculas. Em
um sistema que permita letras maiúsculas, remover `LOWER` pode alterar os
resultados. Outras soluções, como normalização na gravação ou índice de
expressão, exigem análise de requisitos e custo de manutenção.

## Validação posterior

A hipótese foi medida posteriormente com 100 execuções de cada versão. Os
resultados foram equivalentes e o tempo médio no servidor caiu de 26,3300 ms
para 0,0303 ms, redução de 99,88%. O procedimento completo está documentado em
`docs/recommendation_validation_001.md`.
