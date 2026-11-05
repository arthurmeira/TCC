-- Executar manualmente no DBeaver, conectado a tcc_sql_optimizer_logs,
-- somente após a confirmação do COMMIT do gerador.
-- Todas as instruções deste arquivo são consultas de leitura.

-- 1. Contagens esperadas com os parâmetros padrão:
-- clientes=100000, produtos=50000, pedidos=1000000,
-- itens_pedido entre 2000000 e 3000000, pagamentos=1000000.
SELECT 'clientes' AS tabela, COUNT(*) AS registros FROM public.clientes
UNION ALL
SELECT 'produtos', COUNT(*) FROM public.produtos
UNION ALL
SELECT 'pedidos', COUNT(*) FROM public.pedidos
UNION ALL
SELECT 'itens_pedido', COUNT(*) FROM public.itens_pedido
UNION ALL
SELECT 'pagamentos', COUNT(*) FROM public.pagamentos;

-- 2. Todos os indicadores devem ser zero. Pode levar mais tempo,
-- pois agrega todos os itens e percorre pedidos e pagamentos.
WITH totais_itens AS (
    SELECT pedido_id, COUNT(*) AS quantidade_itens,
           SUM(quantidade * valor_unitario) AS total
    FROM public.itens_pedido
    GROUP BY pedido_id
)
SELECT
    COUNT(*) FILTER (
        WHERE t.pedido_id IS NULL
           OR t.quantidade_itens NOT BETWEEN 2 AND 3
    ) AS pedidos_com_itens_invalidos,
    COUNT(*) FILTER (
        WHERE t.total IS DISTINCT FROM p.valor_total
    ) AS pedidos_com_total_incorreto,
    COUNT(*) FILTER (
        WHERE pg.id IS NULL
           OR pg.valor IS DISTINCT FROM p.valor_total
    ) AS pagamentos_ausentes_ou_valor_incorreto,
    COUNT(*) FILTER (
        WHERE p.data_pedido < c.data_cadastro
           OR pg.data_pagamento < p.data_pedido
    ) AS datas_incoerentes,
    COUNT(*) FILTER (
        WHERE NOT (
            (p.status = 'pendente' AND pg.status IN ('pendente', 'recusado'))
            OR (p.status = 'cancelado' AND pg.status IN ('estornado', 'recusado'))
            OR (p.status IN ('pago', 'enviado', 'entregue') AND pg.status = 'aprovado')
        )
    ) AS status_incoerentes
FROM public.pedidos p
JOIN public.clientes c ON c.id = p.cliente_id
LEFT JOIN totais_itens t ON t.pedido_id = p.id
LEFT JOIN public.pagamentos pg ON pg.pedido_id = p.id;

-- 3. Aproximadamente 80% dos pedidos devem estar associados aos
-- primeiros 20% dos clientes (com o volume padrão).
SELECT
    ROUND(
        100.0 * COUNT(*) FILTER (WHERE cliente_id <= 20000)
        / NULLIF(COUNT(*), 0), 2
    ) AS percentual_pedidos_clientes_frequentes
FROM public.pedidos;

-- 4. Datas e status: devem existir pedidos nos três anos e cinco status.
SELECT EXTRACT(YEAR FROM data_pedido) AS ano, status, COUNT(*) AS pedidos
FROM public.pedidos
GROUP BY EXTRACT(YEAR FROM data_pedido), status
ORDER BY ano, status;
