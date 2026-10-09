# Comparação preventiva 001 — função e intervalo de datas

## Objetivo

Comparar dois planos estimados sem executar as consultas: a consulta Q05, que
aplica `EXTRACT` à data, e uma alternativa semanticamente equivalente para os
dados do experimento, usando um intervalo de datas.

## Resultados observados

| Métrica | Consulta original | Alternativa por intervalo |
| --- | ---: | ---: |
| Query ID | -4437562662800320218 | -9204775664590175377 |
| Nó principal | Gather | Hash Join |
| Nós no plano | 5 | 4 |
| Custo estimado | 19.003,00 | 38.633,07 |
| Linhas estimadas | 5.000 | 499.434 |
| Tempo de planejamento | 5,54 ms | 9,48 ms |
| Nível heurístico | Alto, 9/10 | Alto, 7/10 |

O histórico da consulta original registrou média de 499.676 linhas por execução.
A estimativa original apresentou erro relativo de aproximadamente 99,00%. A
alternativa estimou 499.434 linhas, com erro relativo de aproximadamente 0,05%
quando comparada à mesma referência histórica.

## Interpretação

A substituição de `EXTRACT(YEAR FROM data_pedido) = 2026` pelo intervalo
`data_pedido >= '2026-01-01' AND data_pedido < '2027-01-01'` permitiu ao
planejador reconhecer quase exatamente a cardinalidade observada anteriormente.
O alerta de função aplicada no filtro desapareceu.

O custo estimado aumentou porque o plano passou a considerar cerca de 500 mil
linhas, em vez de apenas 5 mil. Esse aumento não representa tempo em
milissegundos e não permite afirmar que a alternativa ficou mais lenta. Ele
mostra que a comparação isolada do custo seria enganosa quando uma das
consultas possui grande erro de cardinalidade.

A alternativa ainda apresentou varredura sequencial e retorno volumoso. Isso é
coerente com a seleção de aproximadamente metade da tabela: mesmo que existisse
um índice simples na data, o planejador poderia concluir que ler grande parte da
tabela sequencialmente é mais econômico. A análise preventiva não deve sugerir
um índice automaticamente sem considerar a seletividade e os custos de escrita.

Nenhuma das duas consultas foi executada durante essas análises. A equivalência
semântica foi definida para o experimento; o protótipo não tenta provar que duas
consultas arbitrárias produzem os mesmos resultados.
