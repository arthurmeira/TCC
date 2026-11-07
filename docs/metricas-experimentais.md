# Métricas experimentais

Cada repetição medida registra o tempo de execução informado pelo PostgreSQL e
as métricas disponíveis no plano `EXPLAIN ANALYZE`.

- **Tempo de execução:** `Execution Time` do PostgreSQL, incluindo a
  instrumentação do `EXPLAIN`. O relatório compara mediana, média, mínimo e
  máximo entre as repetições de cada versão.
- **Linhas retornadas:** saída da raiz do plano. Linhas internas são mostradas
  por operação, com `Actual Rows` e `Actual Loops`; o produto indica linhas
  produzidas naquela operação, não linhas únicas da consulta.
- **Blocos:** `shared hit/read` e `temp read/write` da raiz por repetição. Os
  filhos não são somados porque os contadores dos ancestrais já incluem seus
  acessos. `Shared hit` indica atendimento pelo cache do PostgreSQL. `Shared
  read` pode vir do cache do sistema operacional e não comprova leitura física
  do disco.
- **Estimativas do plano:** custo estimado e quantidade de linhas estimadas pelo
  otimizador. Custo não representa milissegundos.

Os tempos e os recursos do plano são apresentados em áreas separadas. CPU não é
coletada nem exibida pelo sistema. Relatórios antigos continuam legíveis; os
novos relatórios não incluem amostras de CPU.
