"""Casos didáticos separados da carga histórica do experimento."""

DEMO_QUERIES = [
    dict(id="D01", title="Pedidos por ano", description="Teste a troca de EXTRACT por intervalo de datas. O ganho depende do plano e da quantidade de pedidos selecionados.", sql="""SELECT id, cliente_id, data_pedido, valor_total
FROM public.pedidos
WHERE EXTRACT(YEAR FROM data_pedido) = 2025;"""),
    dict(id="D02", title="Busca por e-mail com LOWER", description="Teste a comparação direta por e-mail. A proposta só é gerada se o banco confirmar que todos os e-mails já estão em minúsculas.", sql="""SELECT id, nome, email, cidade, estado
FROM public.clientes
WHERE LOWER(email) = 'cliente123@example.com';"""),
    dict(id="D03", title="Contagem de pedidos por cliente", description="Compare a subconsulta correlacionada com agregação e LEFT JOIN. O recorte de 10 clientes limita o teste; a alternativa pode ser mais lenta.", sql="""SELECT c.id, c.nome,
       (SELECT COUNT(*) FROM public.pedidos p WHERE p.cliente_id = c.id) AS quantidade_pedidos
FROM public.clientes c
WHERE c.id BETWEEN 1 AND 10
ORDER BY c.id;"""),
    dict(id="D04", title="Ranking anual de compras", description="Junção, agregação e ordenação com filtro por ano. Teste se a reescrita do filtro melhora o tempo; clientes podem empatar no total.", sql="""SELECT c.id, c.nome, c.cidade,
       COUNT(p.id) AS quantidade_pedidos,
       SUM(p.valor_total) AS total_compras,
       AVG(p.valor_total) AS ticket_medio
FROM public.clientes c
JOIN public.pedidos p ON p.cliente_id = c.id
WHERE EXTRACT(YEAR FROM p.data_pedido) = 2025
GROUP BY c.id, c.nome, c.cidade
HAVING COUNT(p.id) >= 3
ORDER BY total_compras DESC;"""),
    dict(id="D05", title="Totais mensais de vendas", description="Agregue os pedidos por mês e teste a reescrita do filtro anual. Os resultados devem ser preservados; a medição determina o ganho observado.", sql="""SELECT DATE_TRUNC('month', data_pedido) AS mes,
       COUNT(*) AS quantidade_pedidos,
       SUM(valor_total) AS total_vendas
FROM public.pedidos
WHERE EXTRACT(YEAR FROM data_pedido) = 2025
GROUP BY DATE_TRUNC('month', data_pedido)
ORDER BY mes;"""),
]
