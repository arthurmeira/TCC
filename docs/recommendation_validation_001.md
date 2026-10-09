# Validação de recomendação 001 — consulta por e-mail

## Objetivo

Medir, depois da análise preventiva, se a substituição de `LOWER(email)` por uma
comparação direta preserva o resultado e reduz o tempo de execução no conjunto
de dados experimental.

## Método

Antes deste teste, a rodada original de 730 chamadas foi preservada nos arquivos
`results/rodada_001/query_metrics.csv` e
`results/rodada_001/query_metrics.json`.

O autor executou manualmente 100 chamadas de cada versão. As 200 chamadas foram
intercaladas em ordem pseudoaleatória com semente 2026. O programa capturou as
métricas acumuladas antes e depois, calculando somente os deltas da rodada. Não
houve reset do `pg_stat_statements`.

```powershell
.\.venv\Scripts\python.exe -m scripts.validate_recommendation `
    --original sql/candidate_email_lower.sql `
    --alternative sql/candidate_email_direct.sql `
    --calls 100
```

## Resultado

Os primeiros resultados retornados pelas duas versões foram iguais. Cada
consulta retornou uma linha em cada chamada.

### Métricas do PostgreSQL

| Versão | Chamadas | Linhas | Tempo total | Tempo médio |
| --- | ---: | ---: | ---: | ---: |
| Original com `LOWER` | 100 | 100 | 2.633,00 ms | 26,3300 ms |
| Alternativa direta | 100 | 100 | 3,03 ms | 0,0303 ms |

A redução observada no tempo médio registrado pelo servidor foi de **99,88%**.
A razão entre as médias foi de aproximadamente 869 vezes.

### Tempos observados pelo cliente Python

| Versão | Chamadas | Linhas | Tempo total | Tempo médio |
| --- | ---: | ---: | ---: | ---: |
| Original com `LOWER` | 100 | 100 | 2.671,49 ms | 26,7149 ms |
| Alternativa direta | 100 | 100 | 39,64 ms | 0,3964 ms |

No cliente, a redução aproximada foi de 98,52%, ou cerca de 67 vezes. A diferença
entre o tempo do servidor e o tempo do cliente é esperada para uma consulta muito
rápida, pois o segundo também inclui comunicação, driver, criação dos objetos de
resultado e controle do laço Python.

## Relação com a análise preventiva

Antes da execução, o analisador havia identificado:

- varredura sequencial na versão com `LOWER`;
- estimativa de 500 linhas para um resultado histórico de uma linha;
- mudança preventiva para `Index Scan` na comparação direta;
- custo estimado de 2.868,00 na original e 8,44 na alternativa;
- estimativa de uma linha na alternativa.

A medição posterior confirmou a direção da recomendação: a consulta direta foi
mais rápida neste ambiente e neste conjunto de dados. Portanto, o protótipo
conseguiu produzir uma sugestão antes da execução e validá-la depois com dados
reais.

## Limitações

O teste representa uma máquina, uma distribuição de dados e uma rodada. Cache,
concorrência e configuração do PostgreSQL podem alterar os tempos. A comparação
direta só é semanticamente válida porque o gerador grava os e-mails em letras
minúsculas. Em bancos que aceitam capitalização variável, a mesma alteração pode
produzir resultados diferentes e não deve ser aplicada automaticamente.
