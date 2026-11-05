# Propostas na tela Analisar consulta — 05/11/2026

Funcionalidade transferida para TCC-Logs por integração incremental. Foram
preservados logs, sincronização, recomendações anteriores e medição existente.

Abra Abrir interface.cmd nesta pasta. O atalho e o servidor usam a porta 8767,
para evitar a instância antiga que permanece na porta 8766.

## Uso

- Analisar e propor melhorias mostra propostas junto do diagnóstico.
- Q03: aviso Nenhuma reescrita recomendada e índice para filtro e ordenação,
  quando não há índice compatível e o plano inclui ordenação explícita.
- Q05: alternativa com intervalo de datas e botão Comparar planos, integrado
  à comparação existente. Não dispara medição automaticamente.
- Copiar SQL e exportação da análise incluem a proposta.

## Regras novas nesta tela

EXTRACT(YEAR FROM coluna) = ano literal: DATE/TIMESTAMP sem fuso, anos 1 a 9998,
igualdade isolada ou em AND, inclusive invertida. Não transforma OR, parâmetros,
colunas ambíguas ou SELECTs aninhados. Preserva o SQL original.

Índice para filtro e ordenação: uma tabela comum, igualdades com literais,
ORDER BY de colunas, até quatro chaves e plano com Sort/Incremental Sort. Confere
índices B-tree completos válidos, ordem direta/inversa, collation e opclasses.
Índices parciais ou de expressão exigem avaliação adicional. Não cria índices.

O módulo src/recommendations.py usa SQLGlot 30.29.0. O motor anterior
src/optimization.py, usado na investigação dos logs, foi preservado. As regras
novas não abrangem todo SQL; ausência de proposta não significa desempenho ótimo.

## Validação

38 testes automatizados passaram. As 12 consultas do projeto foram analisadas no
banco tcc_sql_optimizer_logs. Q03 produziu índice e Q05 produziu reescrita.
Nenhum benchmark de desempenho foi executado na transferência.

Cópias dos seis arquivos existentes alterados:
output/backup-antes-transferencia-melhorias/.
Não foram copiados .env, bancos, históricos ou resultados da pasta TCC.
