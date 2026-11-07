# Fluxo dos logs até o experimento — 06/11/2026

Escopo desta entrega: item 1 da revisão de aderência à proposta aprovada.
Não inclui a campanha experimental nem a correção HTTP pendente.

## Usar

1. Em Consultas SQL, escolha Logs de execução (fonte inicial).
2. Use Coletar exemplos reais para executar os 12 exemplos e importar os registros
   identificados da sessão. Ou importe um .log/.txt/.csv/.json/.jsonl em UTF-8,
   até 20 MB, confirmando que corresponde ao banco tcc_sql_optimizer_logs.
3. Confira arquivos/lotes, quantidade aceita/ignorada e métricas dos eventos.
   Reimportar o mesmo conteúdo não duplica eventos, mesmo com outro nome.
4. Ordene por tempo acumulado, média ou frequência e examine os sinais de revisão.
5. Abra Investigar. A consulta usada é a execução de maior duração do grupo, com
   desempate pelo ID. A origem mostra arquivo, banco associado, horário, duração,
   lote (SHA-256 do conteúdo) e ID do evento.
6. Informe o motivo da seleção e encaminhe uma proposta para Comparar e validar.
   É possível abrir a análise completa ou preparar uma alternativa manual.
7. Execute a medição. O relatório apresenta Do log ao experimento e salva a origem
   no JSON, junto dos SQLs, resultados e medições já existentes.

## Separação das fontes

Estatísticas do PostgreSQL mantém a sincronização manual de pg_stat_statements.
Seus contadores não são somados aos eventos de log. Coletar exemplos não troca
mais a lista para estatísticas. Logs completos preservam os valores presentes
no SQL registrado; não há reconstrução de parâmetros ausentes.

O banco explicitamente informado em JSON/CSV é preservado; registros de outro
banco não podem ser investigados/medidos nessa conexão. Para registros sem banco,
a importação usa a confirmação do usuário. Essa confirmação não altera o conteúdo
original arquivado. A coleta automática obtém o banco da própria conexão.

## Origem salva no experimento

`origin.kind=execution_log` contém o evento selecionado, SQL registrado, duração,
horário, banco, lote, nome do arquivo, hash do conteúdo, grupo, motivo informado,
triagem e métricas do grupo no momento da medição. O servidor resolve o evento
no SQLite; não aceita metadados de origem inventados pelo navegador.

Se a original for editada, o vínculo permanece como referência, mas
`original_matches_event=false` impede apresentá-la como reprodução exata.
Consultas manuais/exemplos e estatísticas recebem tipos de origem distintos.
Relatórios antigos continuam acessíveis, sem atribuição retroativa de procedência.

## Validação desta entrega

- Quatro testes novos verificam arquivo/evento, variante de maior duração,
  motivo obrigatório, alterações no SQL, evento inválido, banco estrangeiro,
  múltiplos lotes e deduplicação.
- Suíte completa: 52 passaram de 53; permanece a falha HTTP intermitente já
  conhecida no teste de corpo acima do limite (WinError 10054).
- JavaScript validado sintaticamente.
- Chrome: alternância das fontes, importação duplicada, motivo obrigatório,
  investigação, benchmark e reabertura do relatório com origem preservada.
- Benchmark de integração: relatório ba265fb8b8dd47a2912cb7f33ce3fe93 vinculado
  ao evento real :8 do lote 6b60f6a025a3b4a24335add9cf73e68fa095cff2c4df3bb253cdb7b87b1f932c.
  Resultados equivalentes (uma linha), com três repetições por versão.
- Coletar exemplos reais executou e importou mais 12 eventos; a interface
  permaneceu na fonte Logs. A importação duplicada não acrescentou eventos.
- Visualização móvel 390px sem transbordamento horizontal da página.

Os dados gerados nesta validação são evidência funcional, não uma nova campanha
experimental consolidada. Um experimento e um lote reais foram adicionados ao histórico.
