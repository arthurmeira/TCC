# Interface da nova versão

Abra `Abrir interface.cmd` na pasta `TCC-Logs`. Endereço: http://127.0.0.1:8767.

Use **Consultas SQL → Atualizar consultas → Investigar** para observar consultas executadas por ferramentas externas no banco **tcc_sql_optimizer_logs**.

Para arquivos de log, selecione a fonte **Arquivos de log**. As propostas podem seguir por **Comparar e validar proposta → Executar e medir**.

Consulte `sincronizacao_postgresql.md` para os detalhes dos snapshots e parâmetros.

Os dados usados ficam no banco separado `tcc_sql_optimizer_logs`. A primeira tela também permite importar logs reais e reabrir os experimentos salvos. As telas de análise manual e comparação continuam disponíveis.

O README da raiz descreve o método, o escopo das regras e os formatos aceitos. O experimento de pedidos por ano também foi medido nesta versão, incluindo quando o resultado foi mais lento.
