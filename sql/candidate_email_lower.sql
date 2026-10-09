-- Consulta Q09 original: função LOWER aplicada à coluna indexada.
-- O comparador solicitará somente EXPLAIN com ANALYZE FALSE.
SELECT id, nome, email, cidade, estado
FROM public.clientes
WHERE LOWER(email) = 'cliente123@example.com';
