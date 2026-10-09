-- Consultas do experimento. Execute a carga pelo generate_workload.py.
-- Cada bloco contém um único SELECT e termina com ponto e vírgula.
-- Os campos name, calls e title são lidos pelo gerador.
-- Frequências padrão: 730 execuções ao todo. Não representam medições reais.

-- name: Q01 | calls: 500 | title: Cliente por chave primaria
SELECT id, nome, email
FROM public.clientes
WHERE id = 123;

-- name: Q02 | calls: 100 | title: Produtos por categoria e preco
SELECT id, nome, preco
FROM public.produtos
WHERE categoria = 'Informática'
  AND preco BETWEEN 100.00 AND 1500.00
  AND ativo = TRUE
ORDER BY preco, id
LIMIT 100;

-- name: Q03 | calls: 60 | title: Historico de pedidos de um cliente
SELECT id, data_pedido, status, valor_total
FROM public.pedidos
WHERE cliente_id = 42
ORDER BY data_pedido DESC, id;

-- name: Q04 | calls: 20 | title: SELECT amplo de pedidos cancelados
SELECT *
FROM public.pedidos
WHERE status = 'cancelado';

-- name: Q05 | calls: 15 | title: JOIN com funcao sobre a data e muitas linhas
SELECT *
FROM public.pedidos p
JOIN public.clientes c ON c.id = p.cliente_id
WHERE EXTRACT(YEAR FROM p.data_pedido) = 2026;

-- name: Q06 | calls: 10 | title: Multiplos JOINs e agregacao por estado e categoria
SELECT c.estado, pr.categoria,
       SUM(i.quantidade) AS unidades,
       SUM(i.quantidade * i.valor_unitario) AS valor_itens
FROM public.clientes c
JOIN public.pedidos p ON p.cliente_id = c.id
JOIN public.itens_pedido i ON i.pedido_id = p.id
JOIN public.produtos pr ON pr.id = i.produto_id
JOIN public.pagamentos pg ON pg.pedido_id = p.id
WHERE pg.status = 'aprovado'
GROUP BY c.estado, pr.categoria
ORDER BY valor_itens DESC, c.estado, pr.categoria;

-- name: Q07 | calls: 8 | title: Agregacao mensal de pedidos por periodo
SELECT DATE_TRUNC('month', data_pedido) AS mes,
       status, COUNT(*) AS pedidos, SUM(valor_total) AS valor_pedidos
FROM public.pedidos
WHERE data_pedido >= TIMESTAMP '2025-01-01 00:00:00'
  AND data_pedido < TIMESTAMP '2026-01-01 00:00:00'
GROUP BY DATE_TRUNC('month', data_pedido), status
ORDER BY mes, status;

-- name: Q08 | calls: 6 | title: Ordenacao dos maiores pedidos
SELECT id, cliente_id, data_pedido, valor_total
FROM public.pedidos
ORDER BY valor_total DESC, id
LIMIT 1000;

-- name: Q09 | calls: 5 | title: Filtro com LOWER sobre email
SELECT id, nome, email, cidade, estado
FROM public.clientes
WHERE LOWER(email) = 'cliente123@example.com';

-- name: Q10 | calls: 3 | title: Subquery com media e retorno volumoso
SELECT id, cliente_id, data_pedido, valor_total
FROM public.pedidos
WHERE valor_total > (
    SELECT AVG(valor_total)
    FROM public.pedidos
);

-- name: Q11 | calls: 2 | title: Subquery correlacionada para contar pedidos
SELECT c.id, c.nome,
       (
           SELECT COUNT(*)
           FROM public.pedidos p
           WHERE p.cliente_id = c.id
       ) AS quantidade_pedidos
FROM public.clientes c
WHERE c.id BETWEEN 1 AND 30
ORDER BY c.id;

-- name: Q12 | calls: 1 | title: Leitura completa dos itens sem filtro
SELECT *
FROM public.itens_pedido;
