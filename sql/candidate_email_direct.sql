-- Alternativa para os dados do experimento, cujos e-mails são minúsculos.
-- O comparador solicitará somente EXPLAIN com ANALYZE FALSE.
SELECT id, nome, email, cidade, estado
FROM public.clientes
WHERE email = 'cliente123@example.com';
