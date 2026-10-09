-- Consulta candidata para a primeira validação do analisador preventivo.
-- O script src.analyzer solicitará somente EXPLAIN com ANALYZE FALSE.
SELECT *
FROM public.pedidos AS p
JOIN public.clientes AS c ON c.id = p.cliente_id
WHERE EXTRACT(YEAR FROM p.data_pedido) = 2026;
