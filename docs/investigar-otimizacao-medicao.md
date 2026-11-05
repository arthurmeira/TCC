# Otimização e medição dentro de Investigar

Em Consultas SQL, clique em Investigar. O painel apresenta o SQL e o histórico,
com duas ações principais:

1. Propor otimização: apresenta as alternativas das regras existentes e incorpora
   as propostas de reescrita/índice do novo analisador. Evita repetir a regra de ano.
2. Medir desempenho: mede original e alternativa selecionada dentro do painel,
   sem navegar para outra tela. Requer uma alternativa executável.

Quando o SQL contém parâmetros, preencha os campos com valores JSON simples:
42, "texto", true, null. Cada campo corresponde à posição mostrada no SQL.
A aplicação não conhece os valores originais removidos pelo pg_stat_statements.
Alterar valores desabilita a medição até gerar a proposta novamente.

A medição existente é reaproveitada: assinaturas de todos os resultados, uma
fotografia transacional, aquecimento e três repetições intercaladas por versão.
São tempos do servidor com EXPLAIN ANALYZE, não tempo de transferência ao DBeaver.
O resultado fica no painel e nos experimentos salvos. Não há teste estatístico
inferencial; as conclusões se referem apenas à rodada observada. Índices sugeridos
não são criados nem medidos por esse botão.

Os controles ficam bloqueados durante a medição para não misturar valores ou
alternativas. As outras telas permanecem no menu lateral. Atualize a página (F5)
para carregar a alteração; a porta e o servidor não foram trocados.

Verificação em 05/11/2026: 38 testes Python passaram, JavaScript sem erro de sintaxe,
fluxo completo verificado no navegador com a contagem correlacionada (clientes 1–3),
validação de parâmetros ausentes e retorno dos controles após execução. Na rodada
8a454f5c7dc24b19b64d7f96df368d48: original 113,427 ms, alternativa 140,675 ms de mediana,
três linhas com assinaturas equivalentes, aumento de 24,02%. O painel orientou manter
a original, sem apresentar a redução de custo estimado como ganho de velocidade.

## Histórico da consulta no painel

O painel Investigar mostra as estatísticas da consulta selecionada armazenadas
pelo PostgreSQL: chamadas, tempo total e médio no servidor, mínimo, máximo,
linhas retornadas e média de linhas por execução. Se a última sincronização
capturou novas chamadas, mostra também a diferença daquela atualização.
Os detalhes exibem banco, usuário, Query ID, início do período estatístico,
período de mínimo/máximo, atividade detectada, variação dos tempos e contadores
de blocos. Datas de atividade representam a atualização em que houve mudança,
não o instante exato de uma execução. `pg_stat_statements` agrupa execuções por
estrutura e pode ter seus contadores reiniciados; os valores dos parâmetros
originais não estão disponíveis. As métricas históricas não são a medição nova
feita pelo botão Medir desempenho.

Validação: consulta com 14 chamadas no snapshot apresentou 26,64 s totais,
1,9 s de média, 87,79 ms de mínimo, 7,52 s de máximo e 651 linhas acumuladas.
O painel foi conferido visualmente; 38 testes existentes e checagem de sintaxe
JavaScript passaram.
