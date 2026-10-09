-- Alternativa preventiva para comparação com candidate_query.sql.
-- A consulta não será executada pelo analisador: somente EXPLAIN ANALYZE FALSE.
SELECT *
FROM public.pedidos AS p
JOIN public.clientes AS c ON c.id = p.cliente_id
WHERE p.data_pedido >= TIMESTAMP '2026-01-01 00:00:00'
  AND p.data_pedido < TIMESTAMP '2027-01-01 00:00:00';
