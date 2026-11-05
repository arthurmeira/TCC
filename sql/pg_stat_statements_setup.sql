-- ETAPA 4: executar manualmente no DBeaver, em tcc_sql_optimizer_logs.
-- Pré-requisito: configurar shared_preload_libraries e reiniciar o serviço.
-- Este arquivo não altera postgresql.conf nem reinicia o PostgreSQL.
-- A instalação cria os objetos da extensão no banco; não altera os dados comerciais.
-- O reset está comentado no final e não faz parte da instalação.

BEGIN;

DO $$
BEGIN
    IF current_database() <> 'tcc_sql_optimizer_logs' THEN
        RAISE EXCEPTION 'Banco incorreto: %. Conecte a tcc_sql_optimizer_logs.', current_database();
    END IF;

    IF NOT (
        'pg_stat_statements' = ANY (
            regexp_split_to_array(current_setting('shared_preload_libraries'), '\s*,\s*')
        )
    ) THEN
        RAISE EXCEPTION 'Configure shared_preload_libraries e reinicie o PostgreSQL antes de continuar.';
    END IF;

    IF current_setting('compute_query_id') NOT IN ('auto', 'on') THEN
        RAISE EXCEPTION 'compute_query_id deve estar em auto ou on para este experimento.';
    END IF;
END;
$$;

CREATE EXTENSION IF NOT EXISTS pg_stat_statements WITH SCHEMA public;

COMMIT;

-- Configurações ativas: bibliotecas deve incluir pg_stat_statements,
-- identificacao deve ser auto/on e rastreamento deve ser top.
SELECT
    current_database() AS banco,
    current_setting('shared_preload_libraries') AS bibliotecas,
    current_setting('compute_query_id') AS identificacao,
    current_setting('pg_stat_statements.track') AS rastreamento;

SELECT extname, extversion
FROM pg_extension
WHERE extname = 'pg_stat_statements';

-- Consulta de leitura para gerar uma entrada de teste nas estatísticas.
SELECT id, nome, email
FROM public.clientes
WHERE id = 123;

-- Deve retornar a consulta acima com calls >= 1 e tempos em milissegundos.
SELECT queryid, calls, total_exec_time, mean_exec_time, rows, query
FROM public.pg_stat_statements
WHERE dbid = (SELECT oid FROM pg_database WHERE datname = current_database())
  AND query LIKE '%FROM public.clientes%'
  AND query LIKE '%WHERE id =%'
ORDER BY calls DESC;

-- RESET FUTURO: somente imediatamente antes de um novo experimento.
-- Descarta as métricas anteriores de TODOS os usuários do banco do TCC.
-- Não exclui dados comerciais e não limpa caches. Não é desfeito por ROLLBACK.
-- O dbid limita o reset ao banco experimental. Sem parâmetros, a função
-- resetaria estatísticas de todos os bancos da instância: não use esse formato.
-- Registre o horário retornado e execute o workload após o reset.
-- Não execute novamente este arquivo de instalação entre o reset e o workload.
/*
SELECT public.pg_stat_statements_reset(
    dbid => (SELECT oid FROM pg_database WHERE datname = 'tcc_sql_optimizer_logs')
);
*/
