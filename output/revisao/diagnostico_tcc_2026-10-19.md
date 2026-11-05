# Revisão criteriosa do TCC — diagnóstico de 19 de outubro de 2026

Objeto: artigo de Arthur Meira, Ciência da Computação, Universidade do Extremo Sul Catarinense — UNESC, Criciúma. Texto principal: anexo iniciado por “Artigo revisado com base nas observações do orientador”. Esta revisão não altera o artigo nem a implementação.

Premissas confirmadas pelo autor: o modelo LaTeX foi adaptado durante as revisões; a orientação é de **15 a 20 páginas, excluindo referências e apêndices**. Essa orientação prevalece sobre escolhas de outros TCCs. Não se presumiu que uma classe chamada `UNESC.cls` seja oficial.

## 1. Parecer geral

**O trabalho tem uma base científica e uma descrição metodológica aproveitáveis, mas ainda não deve ser considerado pronto para entrega.** A revisão necessária é localizada: não há motivo para reescrever tudo ou ampliar o projeto experimental indiscriminadamente.

O texto explica o problema, apresenta uma pergunta de pesquisa respondível e organiza uma sequência coerente: gerar dados, executar uma carga, coletar estatísticas, analisar planos, comparar alternativas e validar um caso. O caráter preventivo se aplica à análise da consulta candidata, não à inexistência de execuções anteriores: o histórico foi produzido por uma carga efetivamente executada. Essa distinção é compatível com o objetivo.

São pontos fortes que devem ser preservados:

- O resumo descreve problema, método, resultados e conclusão sem depender de identificadores como Q05 e Q12; tem aproximadamente 240 palavras.
- A distinção entre estatísticas acumuladas e logs individuais foi corrigida no título e no desenvolvimento.
- O texto separa custo estimado, tempo no servidor e tempo no cliente; não afirma que a reescrita por ano foi comprovadamente mais rápida.
- A geração da base, a semente, as distribuições, os volumes, as frequências e as regras heurísticas estão descritos de maneira acessível.
- A equivalência da busca por e-mail está condicionada à normalização dos dados; a comparação dos primeiros resultados não é apresentada como prova universal.
- A interface implementada, os testes funcionais e a ausência de avaliação de usabilidade com participantes estão diferenciados.
- As limitações são explícitas, incluindo cache, ambiente, repetição limitada e dados sintéticos.

Os impedimentos mais relevantes são:

1. **Bibliografia local incompatível com o texto enviado:** há 11 chaves citadas e sete delas não existem em nenhum dos dois arquivos `referencias.bib` encontrados. Se o Overleaf tiver um arquivo mais recente, ele precisa ser conferido; o problema comprovado é do conjunto local disponível.
2. **Não há PDF correspondente ao texto enviado:** os PDFs locais conferidos têm o título anterior, baseado em “logs”, e outra estrutura. Portanto, não é possível certificar as páginas, margens ou a legibilidade da versão atual.
3. **Modelo adaptado sem procedência institucional confirmada:** as duas classes locais têm configurações diferentes. Uma usa papel A4 e recuo de 1,25 cm; a outra configura papel de 190 × 290 mm e recuo de 2 cm. O preâmbulo enviado seleciona a família Helvetica (`phv`). O modelo geral de artigo disponibilizado pela Biblioteca em 2025 é uma referência oficial útil, mas não comprova qual adaptação específica o curso aceita.
4. **Duas afirmações técnicas precisam de correção:** “maior duração por chamada” não deve sugerir identificação do máximo individual entre todas as execuções; e a rejeição de “construções com WITH” está descrita de forma mais ampla que a implementação.
5. **A rastreabilidade dos resultados originais é incompleta:** os valores estão documentados em registros locais transcritos de terminal, mas os CSV/JSON originais mencionados na documentação não foram encontrados. Resultados posteriores não substituem esses arquivos.
6. **Ainda aparece o histórico pessoal de reinstalação**, apesar da orientação expressa de removê-lo.

O título atual é coerente com o protótipo, desde que “otimização” continue significando apoio à investigação e validação de uma alteração, e não otimização automática geral. A avaliação comprova funcionamento e ilustra dois casos; não mede precisão dos alertas, taxa de falsos positivos ou eficácia em bancos reais diversos. Não é necessário prometer essas avaliações para concluir o escopo atual.

### Alcance da verificação

Foram confrontados o texto, as duas classes e bibliografias locais, PDFs anteriores, scripts de geração/carga/validação, módulos de coleta/análise/comparação, esquema SQL, consultas, documentação experimental e resultados posteriores disponíveis. Os sete testes automatizados locais passaram nesta revisão; são testes HTTP com simulação de dependências, não repetição do benchmark nem validação independente dos tempos históricos. Não foi executada nova carga no banco.

As skills de PDF e documentos foram usadas para separar leitura textual de conferência visual. Foram examinadas páginas relevantes dos PDFs e extraídas as instruções do modelo Word; sua renderização não foi concluída por indisponibilidade do executável de conversão. Não se atribui a essa leitura uma certificação visual do modelo ou do artigo atual.

## 2. Tabela de conformidade

“Atende” significa que há evidência no material examinado; não equivale a aprovação institucional. “Pendente” identifica uma verificação que os arquivos disponíveis não permitem concluir.

| Critério | Evidência | Situação | Correção ou providência |
|---|---|---|---|
| Instituição e curso | Identificação do artigo, página do curso e coleção COM do repositório | Confirmados: UNESC de Criciúma, Ciência da Computação | Não confundir com instituições homônimas. |
| Modalidade artigo | Pedido do professor e dois artigos do mesmo curso, de julho de 2026 | Compatível; regulamento específico atual não confirmado | Obter o modelo/regulamento efetivamente adotado na turma. |
| 15–20 páginas sem referências/apêndices | Confirmação expressa do autor | Pendente na versão atual | Compilar exatamente o texto enviado com a classe e o `.bib` definitivos. |
| Estrutura científica | Introdução, fundamentação, métodos, resultados/discussão, conclusão, referências | Adequada | Manter; não há evidência de que fundamentação separada seja proibida. |
| Título e objetivos | Análise preventiva, integração de métricas/planos, validação de uma alteração | Coerentes com o escopo | Não converter a contribuição em promessa de otimizador automático ou universal. |
| Autoria e identificação | Autor, orientador, curso, instituição, cidade e contatos | Presentes | Conferir grafia e apresentação final com o modelo adotado. |
| Resumo e abstract | Aproximadamente 240 e 228 palavras; método e resultados; sem Q05/Q12 | Conteúdo adequado; resumo dentro dos 100–250 indicados no modelo geral de 2025 | Preservar concisão e coerência entre idiomas. |
| Palavras-chave/keywords | Cinco em cada idioma, separadas por ponto e vírgula | Adequadas no texto | Conferência visual final; não há aqui comprovação de número obrigatório específico do curso. |
| Papel, margens, fonte, recuo e espaçamento | Duas classes divergentes; `phv`; PDF anterior de 190 × 290 mm | Não certificado; há divergências em relação ao modelo geral | Resolver o modelo antes de ajustar a extensão. Verificar também espaços simples nas exceções indicadas pelo modelo. |
| Citações e referências | 11 chaves citadas, sete ausentes nos `.bib` locais | Incompleto no conjunto disponível | Completar ou fornecer a bibliografia atual; conferir saída compilada, anos e autor-data. |
| Fluxograma | Figura com seis etapas do processo, legenda, fonte e chamada textual | Atende à orientação “aplicação ou processo” | Não é obrigatório criar outro diagrama; um fluxo da interface seria apenas complementar. |
| Base experimental | Cinco tabelas, relações, índices, 4.648.714 registros e distribuições descritos | Bem documentada | Vincular a uma versão estável do código e dos arquivos de dados/resultados. |
| Geração e carga | Semente 2026, lotes de 10.000, COPY e ANALYZE; trechos adaptados | Adequadas | Manter explicações; acrescentar referência ao procedimento completo de reprodução. |
| Carga de consultas | 12 consultas; frequências somam 730; ordem pseudoaleatória; parâmetros fixos | Adequada, com lacunas de empacotamento | Disponibilizar o SQL exato, parâmetros e comandos em repositório/artefato identificado. |
| Ambiente das rodadas | Versões originais e posteriores separadas; hardware original incompleto | Transparente, mas não plenamente reproduzível | Não atribuir hardware posterior à primeira rodada; retirar narrativa de reinstalação. |
| Estatísticas, custos e tempos | Distinções explícitas entre `pg_stat_statements`, EXPLAIN e cliente | Tecnicamente adequadas | Preservar; especificar melhor associação ao histórico e diferenças entre os dois scripts de medição. |
| Ranking Q12 | Campo de tempo médio e apenas uma chamada | Redação imprecisa | Usar “maior tempo médio entre as consultas”; não afirmar máximo individual global. |
| Validação de entrada SQL | Código restringe o início da instrução; aceita um WITH aninhado no teste da função | Descrição excessivamente ampla | Substituir “construções com WITH” por “instruções iniciadas por WITH”. |
| Reescrita da consulta por ano | Comparação de planos, sem medição da alternativa | Delimitação correta | Não converter estimativa mais próxima ou score menor em ganho temporal. |
| Validação por e-mail | 100 chamadas por versão; deltas; primeiros resultados comparados | Evidência limitada ao caso e à rodada | Preservar condições semânticas e limites; recuperar arquivos originais se disponíveis. |
| Interface e testes | Implementação, sete testes automatizados e registros de integração posteriores | Funcionamento documentado | Não apresentar como estudo de usabilidade nem como prova de ausência de qualquer efeito em todo SQL possível. |
| Figuras, tabelas e códigos | 1 figura, 6 tabelas, 7 listagens; legendas e fontes no código-fonte | Em geral adequados; visual atual pendente | Acrescentar chamada explícita à tabela do ranking; verificar quebras, fontes e legibilidade no PDF final. |
| Aplicação global das correções do professor | Resumo acessível e distinções técnicas corrigidas; reinstalação ainda aparece | Parcialmente atendida | Generalizar os ajustes; cotejar com todas as anotações originais, não apenas o resumo fornecido. |

Referência institucional de formatação: [modelo geral de artigo científico da UNESC, 2025](https://www.unesc.net/files/editor/files/modelo%20de%20artigo%20cient%C3%ADfico_2025.docx). As ressalvas sobre vigência e aplicação específica estão detalhadas na seção 7.

## 3. Extensão e equilíbrio das seções

### Medição do texto atual

A contagem aproxima palavras de prosa, removendo comandos LaTeX, títulos, citações, tabelas, figura e listagens. Números e identificadores podem ser contados como palavras; algumas linhas de fonte dos códigos permanecem. Não é uma medição de área impressa. O corpo tem cerca de **4.627 palavras**; com resumo e abstract, aproximadamente **5.095**, sem bibliografia. Não há PDF correspondente para atribuir páginas atuais a cada seção.

As faixas abaixo são **sugestões editoriais coordenadas, não regras institucionais**. As páginas incluem os elementos gráficos de cada parte. Seus limites combinados ficam aproximadamente entre 15,75 e 19 páginas, antes das referências/apêndices. Não se deve expandir uma seção só para atingir uma faixa.

| Seção | Extensão atual | Problema ou avaliação | Faixa sugerida | Justificativa |
|---|---|---|---|---|
| Identificação, resumo e abstract | Resumo: 240 palavras; abstract: 228 | Bem dimensionados; próximo do teto do resumo | Manter aproximadamente 200–250 palavras por idioma; conjunto inicial de 1,5–2 páginas | Evitar cortar resultados e condições essenciais ou ocupar uma página artificialmente. |
| Introdução | 501 palavras; 9 parágrafos | Clara; alguma repetição com a fundamentação | 500–650 palavras; 1,5–2 páginas | Pequenos ajustes de contribuição e delimitação bastam. |
| Fundamentação teórica | 606 palavras; 3 subseções | Correta, mas enxuta na relação entre histórico, cardinalidade e decisão de otimizar | 800–1.000 palavras; 2–2,5 páginas, se o PDF comportar | Aprofundar conceitos usados nos resultados, sem criar revisão genérica de bancos de dados. |
| Materiais e métodos | 2.137 palavras; 9 subseções, figura, tabelas e códigos | Parte mais forte e extensa; lacunas são de rastreabilidade/configuração, não de volume de prosa | 2.100–2.500 palavras; 6–7 páginas | Preservar reprodução; substituir narrativa pessoal por informação operacional, preferencialmente sem aumento líquido. |
| Resultados e discussão | 1.127 palavras; 5 subseções | Resultados bem delimitados; discussão ainda pouco conectada à literatura | 1.300–1.700 palavras; 4–4,5 páginas | Explicar o significado dos dois casos, do score e das condições sem repetir tabelas. |
| Conclusão | 256 palavras; 5 parágrafos | Proporcional e prudente; corrigir a afirmação sobre Q12 | 250–350 palavras; 0,75–1 página | Responder à pergunta de pesquisa sem novos resultados ou promessa geral. |
| Referências | 11 fontes citadas, mas apenas 4 dessas chaves presentes nos `.bib` locais | Incompletas no material disponível | Extensão necessária às fontes realmente usadas; previsão editorial de 1–2 páginas, fora da contagem | Não estabelecer quota de referências ou encurtá-las para caber no corpo. |

### O que os PDFs disponíveis permitem afirmar

O [PDF anterior de 15 páginas](<C:/Users/Arthur Meira/Desktop/TCC/output/pdf/TCC_Arthur_Meira_revisado.pdf>) inicia introdução na página 2, métodos na 4, resultados na 9 e conclusão na 14; as referências começam ainda na 14 e continuam na 15. Assim, **15 páginas totais desse PDF não significam 15 páginas válidas sem referências**. Mesmo contando integralmente a página compartilhada, o conteúdo anterior às referências não alcança 15 páginas. Além disso, ele não contém a versão atual com fundamentação separada. Também foi encontrado um PDF anterior de 25 páginas; ele não resolve a medição do novo texto.

### Comparação de distribuição, não de regras

| Artigo do mesmo curso/modalidade | Distribuição observada nos PDFs | Utilidade para este TCC |
|---|---|---|
| Wesley Emanuel da Silva, julho de 2026, 19 páginas totais | Introdução p. 2–5; métodos p. 6–12; resultados p. 12–16; conclusão p. 16–18; referências p. 18–19 | Exemplo de explicitação de dados, parâmetros e discussão que retorna à literatura. |
| Felipe Trevisani Cardoso, julho de 2026, 30 páginas totais | Introdução p. 2–5; métodos p. 5–11; resultados p. 11–19; conclusão p. 19–20; referências p. 20–21; apêndices p. 22–30 | Exemplo de separação de dados detalhados em apêndices; suas 30 páginas não justificam ampliar o limite do seu professor. |

As faixas compartilham páginas de transição e não devem ser somadas como blocos inteiros. Os dois trabalhos integram o referencial à introdução; isso é uma escolha de organização, não prova de que sua seção de fundamentação deva ser excluída. Consulte [Silva (2026)](https://repositorio.unesc.net/items/63cc247e-07d1-4f44-9e14-a32912d2e90b) e [Cardoso (2026)](https://repositorio.unesc.net/items/0c16ae88-722b-4ab2-abaf-f336b49f1e30).

### Parágrafos, subseções e elementos

Não há problema geral de parágrafos excessivamente longos: os parágrafos de prosa ficam predominantemente em algumas dezenas de palavras; os maiores encontrados na introdução e na fundamentação têm aproximadamente 68 e 71 palavras. Não recomendo fragmentá-los mais. As 9 subseções de métodos correspondem a etapas distintas e são justificáveis.

As 7 listagens têm 17, 20, 12, 12, 4, 2 e 5 linhas físicas, incluindo linhas vazias. São curtas e pertinentes. Os exemplos de geração, COPY, consumo de resultados e cálculo das médias ajudam a explicar o experimento; os pequenos SQLs tornam as reescritas verificáveis. Não há motivo para mandar todas as listagens para apêndice.

Os riscos de paginação estão no uso repetido de posicionamento `[H]`, em tabelas de três colunas com texto extenso e nas fontes reduzidas. São riscos a verificar no PDF atual, não defeitos visuais já demonstrados. Não reduzir fonte, margens ou espaçamento para forçar o limite.

## 4. Correções prioritárias e origem

### Obrigatórias para considerar a revisão encerrada

1. **Resolver a bibliografia e compilar sem citações indefinidas.** Origem: correspondência entre citações/referências e verificabilidade acadêmica; problema objetivo no conjunto local.
2. **Definir o modelo aceito e verificar 15–20 páginas do texto atual, sem referências/apêndices.** Origem: professor e confirmação do autor. A escolha entre classes adaptadas não pode ser arbitrária.
3. **Remover todas as menções pessoais à reinstalação**, mantendo apenas distinção de rodadas, ambientes e consequências metodológicas. Origem: orientação expressa recebida.
4. **Corrigir Q12 e a abrangência da rejeição de WITH.** Origem: precisão técnica e correspondência com métricas/código.
5. **Preservar e tornar rastreável a procedência dos resultados.** Origem: rigor científico. Não é obrigatório inventar ou repetir o experimento: é obrigatório não apresentar transcrições como arquivos brutos conferidos nem substituir a rodada original pela posterior.
6. **Cotejar a versão final com todas as anotações do orientador.** Origem: pedido expresso. O resumo das orientações não permite garantir que todas as marcações específicas foram resolvidas.

### Importantes

- Consolidar um pacote reprodutível: versão do código, SQL exato, parâmetros, comandos e resultados de cada rodada. Origem: expectativa do professor e boa prática experimental.
- Explicitar a associação entre plano e histórico e o tratamento de consultas sem histórico. Origem: método central da contribuição.
- Descrever as diferenças entre a medição da carga e a validação por e-mail, sem presumir configurações históricas que não foram preservadas. Origem: reprodutibilidade e comparação justa.
- Fortalecer fundamentação e discussão com as fontes já usadas, sobretudo cardinalidade, seletividade e limites do histórico agregado. Origem: sugestão científica/editorial, não quota institucional de páginas.
- Inserir a chamada textual à tabela do ranking e conferir o estilo autor-data gerado. Origem: apresentação científica e orientação institucional de citações.
- Explicar a alteração da pontuação por regras acionadas; não tratá-la como escala calibrada de melhoria. Origem: coerência entre método heurístico e interpretação dos resultados.

### Opcionais

- Encurtar o título ou explicitar PostgreSQL no título, se o professor concordar; o título atual é defensável e não precisa ser substituído.
- Incluir uma única imagem legível da interface, somente se ajudar a entender a interação. O fluxograma atual já atende à exigência informada.
- Acrescentar outras repetições, parâmetros e medidas de dispersão em estudo futuro. Isso fortaleceria inferências, mas não deve ser transformado em novo requisito institucional sem orientação do professor.
- Acrescentar um diagrama relacional se os relacionamentos continuarem difíceis de entender após a revisão textual. Não é necessário apenas para aumentar páginas.

## 5. Sugestões pontuais de alteração

### 5.1 Introdução, título e contribuição

Trecho: “desenvolver e avaliar um processo automatizado de análise preventiva”.

O termo “automatizado” é aceitável para coleta, geração de planos e aplicação das regras. Convém esclarecer, junto da contribuição, que a seleção dos dois casos e a decisão de adotar alterações são humanas, e que a avaliação é exploratória/funcional, não uma validação estatística da capacidade de detectar todos os problemas.

Evitar repetir na fundamentação as mesmas definições de plano e cardinalidade que já aparecem na introdução. A introdução contextualiza; a fundamentação deve explicar os conceitos necessários para interpretar os resultados. Não há necessidade de formalismo matemático adicional.

### 5.2 Fundamentação: histórico não é verdade absoluta de cardinalidade

Trecho: “Comandos de estrutura equivalente podem compartilhar uma entrada”.

Está correto. Acrescentar a consequência operacional: a média de linhas por chamada pode agregar parâmetros com seletividades diferentes. A comparação com a estimativa do plano é um sinal para investigação, não uma medida direta do erro de estimativa de uma execução específica. No seu experimento, os parâmetros fixos reduzem essa ambiguidade; não a eliminam em uso geral. Essa interpretação é consistente com a [documentação de pg_stat_statements](https://www.postgresql.org/docs/18/pgstatstatements.html).

### 5.3 Ambiente: retirar a narrativa pessoal em todos os pontos

Ocorrências: ambiente de desenvolvimento; coleta das estatísticas; verificações posteriores; limitações.

Trecho: “Após a reinstalação do computador...”. Uma substituição localizada possível para o início do parágrafo é:

```text
Em uma verificação posterior, foram utilizados PostgreSQL 18.6 e Python 3.14.7. As características de hardware registradas nessa etapa não permitem reconstruir integralmente o ambiente da primeira rodada. Por esse motivo, os resultados das duas etapas foram documentados separadamente, sem atribuir diferenças de tempo exclusivamente às alterações nas consultas.
```

Os valores de hardware já informados podem permanecer como caracterização da verificação posterior, se houver registro que os sustente. Não devem ser transferidos para a rodada original. Nas demais ocorrências, trocar a referência à reinstalação por “verificação posterior” ou “rodada posterior”, conforme o caso.

### 5.4 Banco, volumes e geração

Os totais somam corretamente 4.648.714 registros. As escolhas de semente, concentração de clientes/produtos, anos, estados dos pedidos e dois ou três itens por pedido estão compatíveis com o gerador examinado. O uso de centavos inteiros/Decimal evita introduzir uma explicação inadequada de valores monetários em ponto flutuante.

Manter a distinção entre propriedade do gerador e restrição do esquema: gerar um pagamento por pedido não equivale a impor unicidade de `order_id` na tabela de pagamentos. O texto já faz essa ressalva; ela é importante. Os índices existentes decorrem das restrições descritas, não de índices experimentais acrescentados após observar os tempos.

Na justificativa dos volumes, apresentar a base como suficiente para produzir situações contrastantes no protótipo. Não chamá-la de representativa de comércio eletrônico real sem fonte ou validação externa.

### 5.5 Carga e condições de execução

A soma das frequências está correta: 730 chamadas. Elas são escolhas experimentais, não uma distribuição empiricamente observada em produção. A ausência de concorrência simulada também está adequadamente delimitada.

Adicionar uma referência precisa ao arquivo que contém as 12 consultas e aos comandos de execução. A reprodução deve permitir descobrir os valores concretos de filtros, não apenas os nomes Q01–Q12. Identificadores locais não são o `queryid` do PostgreSQL.

O código atual da carga desabilita preparação automática (`prepare_threshold = None`), usa autocommit e consome linhas por streaming. A validação por e-mail usa outro caminho de execução e `fetchall`; não contém a mesma desativação explícita da preparação. É importante documentar essa diferença quando se discutem tempos do cliente. Não se deve inferir retroativamente que o código atual é idêntico ao executado na rodada original sem uma versão arquivada.

Entre as configurações que merecem registro, caso disponíveis, estão extensão/versão, rastreamento e identificador de consultas, timeout, paralelismo, memória de trabalho e situação dos contadores. A ausência de registro deve ser declarada; não preencher com valores padrão presumidos.

### 5.6 Coleta: explicar associação e escopo

Trecho: “estatísticas [...] relacionadas aos planos de execução”.

Acrescentar como isso acontece: o código utiliza o identificador de consulta e restringe o histórico pelo banco, usuário e nível de execução. Para uma alternativa ainda não executada, pode não existir histórico próprio. A consulta original pode continuar servindo como referência descritiva, mas isso não cria medições da alternativa.

O coletor também filtra referências às tabelas experimentais; não é uma lista fechada que, em qualquer banco, garanta selecionar somente as 12 consultas previstas. A hipótese de isolamento da rodada é relevante para interpretar os deltas.

O código de cálculo da média está identificado como adaptado e é didático. Sua condição `chamadas > 0` difere ligeiramente do teste de valor não nulo do script; no intervalo válido com deltas positivos, o resultado coincide. Para reprodução exata e tratamento de resets, remeter ao script versionado. Não apresentar o fragmento como tratamento completo de todas as falhas possíveis.

### 5.7 Análise preventiva: corrigir WITH

Trecho: “Foram rejeitados [...] construções com WITH”.

A função de validação não proíbe toda ocorrência de WITH. Foi verificado, sem executar no banco, que uma construção aninhada como `SELECT * FROM (WITH t AS (SELECT 1 AS x) SELECT x FROM t) AS q;` passa pela validação. A correção de redação é:

```text
Foram rejeitados comandos de alteração, múltiplas instruções, SELECT INTO e instruções iniciadas por WITH, conforme o escopo do validador implementado. Essas verificações restringem a entrada, mas não constituem um analisador sintático completo para qualquer expressão SQL.
```

Isso corrige a descrição, sem ampliar o projeto para construir um parser SQL completo.

### 5.8 Regras e pontuação

As oito regras e seus limiares correspondem à implementação examinada. Explicitar que a pontuação resume sinais selecionados, não probabilidade de lentidão, gravidade calibrada nem ganho esperado. A implementação evita repetir o mesmo sinal antes de limitar a soma a dez; mencionar isso se a intenção for permitir reprodução exata da pontuação.

No caso por ano, a passagem de 9 para 7 não comprova melhoria de 22% ou qualquer redução proporcional de risco. Mudam os sinais observados e a disponibilidade de histórico próprio. A análise descritiva comparando ambos os planos com o histórico original não é a mesma operação que pontuar cada consulta com seu histórico disponível.

### 5.9 Ranking: corrigir Q12 e referenciar a tabela

Trecho em resultados: “A Q12 apresentou a maior duração por chamada...”. Trecho correspondente na conclusão: “a maior duração em uma chamada”.

Os dados citados sustentam maior **tempo médio** entre as consultas. Como Q12 teve uma chamada, sua própria média coincide com essa observação. Isso não demonstra que nenhuma execução individual de outra consulta tenha durado mais. Para a conclusão sobre máximo global, seria necessário preservar os máximos pertinentes ou os tempos individuais. A distinção decorre dos campos da [extensão pg_stat_statements](https://www.postgresql.org/docs/18/pgstatstatements.html).

Substituição possível:

```text
A Q12 apresentou o maior tempo médio entre as consultas analisadas, com 6.795,63 milissegundos. Como houve apenas uma chamada dessa consulta, sua média corresponde a uma única observação e não caracteriza a variabilidade de execuções repetidas.
```

Adicionar antes da tabela uma chamada como:

```text
A Tabela~\ref{tab:ranking} apresenta as consultas destacadas por tempo acumulado, tempo médio e frequência.
```

Aplicar a mesma precisão à conclusão e à apresentação oral. Q01: os 9,25 ms em 500 chamadas resultam em 0,0185 ms; exibir 0,02 ms é arredondamento, não contradição.

### 5.10 Consulta por ano: preservar o resultado negativo e explicar melhor

A estimativa passa de 5.000 para 499.434 linhas, aproximando-se da referência histórica de 499.676 linhas por chamada. Entretanto, o custo estimado sobe de 19.003 para 38.633,07. Isso não é uma contradição que precise ser ocultada: uma estimativa de maior volume pode elevar o custo previsto. Custo não é milissegundo, e estimar melhor não garante executar mais rápido. Essa leitura é compatível com [Using EXPLAIN, PostgreSQL 18](https://www.postgresql.org/docs/18/using-explain.html).

O volume selecionado próximo de metade da tabela ajuda a explicar por que uma leitura sequencial pode continuar razoável. Discutir seletividade e existência de índices, sem recomendar que toda varredura seja substituída por um índice.

Não misturar a estimativa 499.434 da comparação documentada com valores diferentes dos arquivos posteriores. A média histórica não é uma medição da alternativa. O texto atual já evita alegar ganho temporal; preservar essa cautela.

### 5.11 Busca por e-mail: boa evidência de caso, não equivalência universal

O resultado relatado de 26,33 para 0,0303 ms no servidor corresponde a redução aproximada de 99,88% na média daquela rodada. Não usar esse percentual para a aplicação inteira, para todas as consultas nem para o tempo do cliente. A diferença entre as médias do cliente, 26,7149 e 0,3964 ms, envolve outra grandeza e outra redução percentual.

Há uma justificativa técnica plausível: comparação direta em coluna normalizada permite o índice existente, enquanto um índice sobre `email` não equivale a um índice sobre `lower(email)`. O [manual de índices de expressão](https://www.postgresql.org/docs/18/indexes-expressional.html) sustenta essa distinção, mas não substitui a medição do seu experimento.

Preservar que os primeiros resultados completos foram comparados. Nas demais chamadas, contar linhas não verifica igualdade de conteúdo. Para esse filtro de uma linha, a verificação é útil; para consultas gerais, duplicidades, valores nulos, collation, parâmetro pesquisado e ordenação podem exigir tratamento adicional. Não transformar essa observação em exigência de prova formal para o TCC.

### 5.12 Interface e verificações posteriores

O registro de 12 de outubro confirma, naquela etapa, os totais e os cinco indicadores de consistência examinados. “Cinco indicadores iguais a zero” não significa que todo tipo possível de inconsistência foi excluído. Explicar ou enumerar quais verificações foram realizadas, se isso ainda não estiver acessível pelo artefato de reprodução.

O registro posterior da interface preserva 730 chamadas antes/depois nas operações verificadas. É uma evidência funcional localizada; não uma prova exaustiva para qualquer SQL ou qualquer efeito do planejamento. Manter a redação restrita aos testes executados.

Os testes automatizados que passaram nesta revisão não executam o benchmark original. Não os usar para afirmar que os tempos foram novamente obtidos.

### 5.13 Discussão e conclusão

Vale acrescentar dois pequenos blocos de discussão: um ligando o caso por ano à literatura sobre cardinalidade; outro ligando o caso por e-mail à seletividade e às condições semânticas da reescrita. Explicar também o que o protótipo acrescenta à simples leitura isolada do EXPLAIN: organização de histórico, regras explícitas e comparação acompanhada de evidências.

Não afirmar inovação de algoritmo de otimização, validação de segurança completa ou melhoria comprovada da experiência do usuário. O ganho científico compatível com os dados é a construção e avaliação exploratória de um processo integrado de apoio.

Na conclusão, preservar limitações e trabalhos futuros, corrigir a expressão sobre Q12 e responder diretamente à pergunta da introdução. Não é necessário acrescentar mais páginas de conclusão.

### 5.14 Bibliografia: correspondência e metadados

| Chave citada | Situação nos dois `.bib` locais | Ação |
|---|---|---|
| `lan2021optimizer` | Presente; autoria, título, veículo, volume/páginas e DOI conferidos | Manter. |
| `kossmann2022dependencies` | Presente; metadados conferidos | Manter 2022 para o volume 31; publicação online em 2021 não torna esse ano de volume incorreto. |
| `abbasi2024` | Ausente; artigo existente | Cadastrar a referência; manter explícito que o contexto de eventos complexos difere do seu. |
| `huang2023` | Ausente; artigo existente | Cadastrar; distinguir número do artigo de intervalo de páginas. |
| `leis2025optimizers` | Ausente; artigo de 2025 existente | Cadastrar a retrospectiva correta; não substituir inadvertidamente pelo artigo original de 2015. |
| `postgresql2026pgstat` e `postgresql2026explain` | Presentes; páginas oficiais confirmadas | Conferir data bibliográfica: o ano de acesso não prova ano de publicação da página. |
| `postgresql2025expression` e `postgresql2025populate` | Ausentes; páginas oficiais confirmadas | Cadastrar páginas específicas da versão documentada. |
| `psycopgcopy` e `python2025time` | Ausentes; páginas oficiais confirmadas | Cadastrar documentação e versão pertinente, com data real de consulta. |

`gaddam2025` e `postgresql2026copy` existem nos `.bib`, mas não são citados no texto atual. Não são duplicatas apenas por tratarem de temas próximos. Na ausência de `nocite`, normalmente não entram na lista impressa. Não inserir citações artificiais só para aproveitá-los.

Os cinco artigos científicos citados são de 2021–2025 e cobrem temas relevantes. A questão principal é integração ao argumento e aos resultados, não quantidade. Documentação oficial é a fonte apropriada para funcionamento de APIs e campos; não substitui a fundamentação científica da contribuição. Não foi identificada necessidade de adicionar fontes genéricas apenas para aumentar a bibliografia.

O uso de `abntex2cite`/`abntex2-alf` não garante sozinho conformidade com todas as orientações mais recentes. Conferir no PDF a capitalização autor-data, autoria institucional, DOI/URL, datas de acesso, destaque de títulos e espaçamento. O guia institucional de 2025 referencia NBR 10520:2023; não tratar a aparência de um TCC comparável como norma.

## 6. Pendências dependentes de arquivos, dados ou confirmação

| Pendência | Por que importa | Se não houver o material |
|---|---|---|
| PDF compilado exatamente do texto enviado, com `.cls` e `.bib` efetivamente utilizados | Confirmar páginas, cortes, fontes, margens, tabelas, referências cruzadas e bibliografia | A conformidade visual e a extensão ficam pendentes; o PDF antigo não serve como substituto. |
| Modelo/regulamento específico atualmente adotado em Ciência da Computação | Resolver divergências entre classes e o modelo geral da Biblioteca | Usar o modelo geral apenas como referência provisória; obter confirmação do professor/curso. |
| Conjunto integral das anotações do orientador | Verificar aplicação de cada correção e das ocorrências semelhantes | A revisão cobre as orientações expressas recebidas, não certifica marcações não acessíveis. |
| CSV/JSON originais de `results/rodada_001`, mencionados na documentação | Recalcular e auditar os resultados originais com precisão | Manter claramente a natureza transcrita/arredondada; não apresentar dados posteriores como originais. |
| Versão/commit ou arquivo do código usado em cada rodada | Evitar atribuir a implementação atual a testes antigos sem comprovação | Declarar essa limitação de rastreabilidade e disponibilizar a versão atual como tal. |
| Registro do ambiente original e configurações relevantes | Reproduzir condições e interpretar tempos | Não reconstruir por suposição nem usar o hardware posterior como equivalente. |
| Decisão sobre eventual nova rodada | Só necessária se houver pretensão de fortalecer a evidência empírica | Manter o estudo como avaliação exploratória delimitada, se isso estiver de acordo com o professor. |

Não é necessário perguntar novamente se referências/apêndices entram na contagem: essa questão já foi respondida pelo autor e foi incorporada à análise.

## 7. Fontes oficiais e trabalhos usados na comparação

Consulta realizada em **19 de outubro de 2026**. Data de acesso não deve ser confundida com data de publicação. As fontes abaixo foram usadas conforme seu alcance; a permanência de um documento antigo no portal não demonstra, isoladamente, vigência atual.

### 7.1 Instituição, regulamentos e normalização

| Documento | Data/identificação | O que foi verificado e limite | Link |
|---|---|---|---|
| Página de Ciência da Computação, UNESC | Página institucional, sem data de publicação confirmada | Identificação do curso; não foi localizado ali um regulamento atual de artigo que resolvesse todas as dúvidas | [Curso](https://www.unesc.net/ciencia-da-computacao) |
| Modelo de artigo científico da Biblioteca | Arquivo identificado como 2025 | Estrutura, resumo, palavras-chave e orientações de apresentação. Modelo geral, não prova de aceitação da sua classe adaptada | [Modelo Word](https://www.unesc.net/files/editor/files/modelo%20de%20artigo%20cient%C3%ADfico_2025.docx) |
| Procedimentos de citações e referências | Criciúma, 2025; menciona NBR 10520:2023 e NBR 6023:2018 | Critérios de citação e referência apresentados pela Biblioteca; não se presume que indique todas as revisões normativas posteriores | [Guia PDF](https://www.unesc.net/files/editor/files/Cita%C3%A7%C3%A3o%20e%20Refer%C3%AAncia%202025.pdf) |
| Página de normas da Biblioteca | Página institucional consultada em 2026 | Origem dos materiais de orientação disponibilizados | [Normas](https://www.unesc.net/portal/capa/index/533/9236/) |
| Resolução 66/2009 | 6 de agosto de 2009 | Regulamento geral; admite especificação de modalidade pelo curso e remete a regulamentos próprios. As sete páginas foram examinadas. Não confirmada sua vigência integral em 2026 | [Resolução](https://www.unesc.net/portal/resources/official_documents/3010.pdf) |
| PPC público de Ciência da Computação | Arquivo sem data de aprovação atual confirmada; metadado de criação do PDF em dezembro de 2019 | Trecho de TCC nas p. 47–48 refere-se a monografia, estrutura antiga e resoluções 66/2009 e 25/2009. Não foi imposto como regulamento atual de artigo | [PPC](https://www.unesc.net/portal/resources/official_documents/17818.pdf?1524592578=) |

O modelo geral de 2025 indica Arial ou Times New Roman 12, recuo de 2 cm e entrelinha 1,5, com exceções em espaço simples; o arquivo utiliza A4 e margens de 3 cm superior/esquerda e 2 cm inferior/direita. Isso permite apontar divergências nas adaptações locais, mas não escolher unilateralmente qual formatação específica o curso autoriza.

Há uma inconsistência interna no modelo Word: um trecho ainda menciona NBR 10520:2002, enquanto referências e o guia de 2025 apontam a edição de 2023. Portanto, não convém copiar mecanicamente a menção antiga. **Não foi localizado e validado um regulamento específico atual que estabeleça todos os requisitos do artigo deste curso**, nem uma regra institucional pública confirmando o limite de páginas informado. Esse limite foi adotado por orientação do professor, não inventado a partir das fontes.

### 7.2 Artigos comparáveis do mesmo curso

1. **Silva, Wesley Emanuel da.** *Análise e funcionamento de algoritmos de recomendação em plataformas de streaming e redes sociais*. Julho de 2026; orientador André Faria Ruaro. O repositório identifica expressamente como Artigo de Conclusão de Curso de Ciência da Computação da UNESC. PDF de 19 páginas; foram examinadas a organização e passagens de método, resultados e conclusão, não realizada uma auditoria independente de seus experimentos. [Registro institucional](https://repositorio.unesc.net/items/63cc247e-07d1-4f44-9e14-a32912d2e90b) · [PDF](https://repositorio.unesc.net/bitstreams/e2781672-47d0-4b60-8bd4-32bb8c2177cb/download).
2. **Cardoso, Felipe Trevisani.** *Comparação de desempenho entre linguagens de programação na implementação de API*. Julho de 2026; orientador Marlon de Matos de Oliveira. Também identificado como artigo do mesmo curso. PDF de 30 páginas, com apêndices a partir da 22; utilizado para observar descrição experimental e separação de resultados detalhados. Sua declaração de uso de IA não foi tratada como obrigação institucional universal. [Registro institucional](https://repositorio.unesc.net/items/0c16ae88-722b-4ab2-abaf-f336b49f1e30) · [PDF](https://repositorio.unesc.net/bitstreams/8c0c0bf8-4bbe-44e3-a3e1-c2afc14997f9/download).

### 7.3 Fontes científicas verificadas para a bibliografia

| Fonte | Metadados conferidos | Avaliação de uso |
|---|---|---|
| Lan, Hai; Bao, Zhifeng; Peng, Yuwei | *A Survey on Advancing the DBMS Query Optimizer: Cardinality Estimation, Cost Model, and Plan Enumeration*. Data Science and Engineering, 6(1), 86–101, 2021. [DOI 10.1007/s41019-020-00149-7](https://link.springer.com/article/10.1007/s41019-020-00149-7) | Central para estimativas e otimização; entrada local adequada. |
| Kossmann, Jan; Papenbrock, Thorsten; Naumann, Felix | *Data Dependencies for Query Optimization: A Survey*. The VLDB Journal, 31(1), 1–22, 2022; publicação online em 2021. [DOI 10.1007/s00778-021-00676-3](https://link.springer.com/article/10.1007/s00778-021-00676-3) | Relevante para restrições e dependências; não confundir ano online com ano do volume citado. |
| Huang, Shiyue; Qin, Yanzhao; Zhang, Xinyi; Tu, Yaofeng; Li, Zhongliang; Cui, Bin | *Survey on performance optimization for database systems*. Science China Information Sciences, 66, artigo 121102, 2023. [DOI 10.1007/s11432-021-3578-6](https://doi.org/10.1007/s11432-021-3578-6) | Adequado à distinção entre previsão, diagnóstico e ajustes; entrada ausente. |
| Leis, Viktor; Gubichev, Andrey; Mirchev, Atanas; Boncz, Peter; Kemper, Alfons; Neumann, Thomas | *Still Asking: How Good Are Query Optimizers, Really?* Proceedings of the VLDB Endowment, 18(12), 5531–5536, 2025. DOI 10.14778/3750601.3760521. [PDF do periódico](https://www.vldb.org/pvldb/vol18/p5531-viktor.pdf) | Retrospectiva pertinente; é de fato uma publicação de 2025, distinta do trabalho de 2015. |
| Abbasi, Maryam; Bernardo, Marco V.; Váz, Paulo; Silva, José; Martins, Pedro | *Optimizing Database Performance in Complex Event Processing through Indexing Strategies*. Data, 9(8), artigo 93, 2024. [DOI 10.3390/data9080093](https://www.mdpi.com/2306-5729/9/8/93) | Existência confirmada; pertinência complementar, com contexto diferente já reconhecido no texto. |
| Gaddam, Suman Reddy | *Database Performance Optimization: Strategies that Scale*. International Journal of Computing and Engineering, 7(11), 1–12, publicado em 17 de julho de 2025. [DOI 10.47941/ijce.2967, página editorial](https://carijournals.org/journals/IJCE/article/view/2967) | Metadados locais conferem; não está citado na versão atual. Existência não é avaliação completa de qualidade metodológica. |

### 7.4 Documentação técnica primária

- **PostgreSQL, versão 18:** [pg_stat_statements](https://www.postgresql.org/docs/18/pgstatstatements.html), [Using EXPLAIN](https://www.postgresql.org/docs/18/using-explain.html), [Indexes on Expressions](https://www.postgresql.org/docs/18/indexes-expressional.html), [Populating a Database](https://www.postgresql.org/docs/18/populate.html) e [COPY](https://www.postgresql.org/docs/18/sql-copy.html). Suportam definições de campos, custo, planejamento, índices e carga; não validam os números do experimento por si mesmas.
- **Psycopg 3:** [Using COPY to and from tables](https://www.psycopg.org/psycopg3/docs/basic/copy.html). Documenta a operação usada na carga. A página corrente não deve ser confundida automaticamente com uma cópia arquivada da versão executada na rodada original.
- **Python 3.14:** [time.perf_counter](https://docs.python.org/3.14/library/time.html#time.perf_counter). É medição de tempo decorrido; não equivale a tempo de CPU do servidor.

Para essas páginas, registrar versão e data real de acesso; o ano no nome da chave BibTeX é apenas um identificador interno. Não deduzir ano de publicação a partir da versão do software, do rodapé de copyright ou do ano da consulta.

### 7.5 Evidências locais principais

- [Texto efetivamente revisado](<C:/Users/Arthur Meira/.codex/attachments/7b615f03-e65a-45d3-beb6-4c6f2b7019e1/Texto colado.txt>) e [pedido completo](<C:/Users/Arthur Meira/.codex/attachments/2aeae654-3995-4cec-92a7-94f6a2447625/Texto colado.txt>).
- [Classe de compatibilidade](<C:/Users/Arthur Meira/Desktop/TCC/output/latex/artigo_tcc_corrigido/UNESC.cls>), [outra classe local](<C:/Users/Arthur Meira/Desktop/TCC/output/latex/TCC_revisado_professor/UNESC.cls>) e [bibliografia local](<C:/Users/Arthur Meira/Desktop/TCC/output/latex/artigo_tcc_corrigido/referencias.bib>).
- [Registro do primeiro experimento](<C:/Users/Arthur Meira/Desktop/TCC/docs/experiment_001.md>), [validação por e-mail](<C:/Users/Arthur Meira/Desktop/TCC/docs/recommendation_validation_001.md>) e [comparação preventiva](<C:/Users/Arthur Meira/Desktop/TCC/docs/preventive_comparison_001.md>).
- [Analisador de planos](<C:/Users/Arthur Meira/Desktop/TCC/src/plan_analyzer.py>), [comparação de planos](<C:/Users/Arthur Meira/Desktop/TCC/src/compare_plans.py>), [geração da carga](<C:/Users/Arthur Meira/Desktop/TCC/scripts/generate_workload.py>), [validação da recomendação](<C:/Users/Arthur Meira/Desktop/TCC/scripts/validate_recommendation.py>) e [testes da interface](<C:/Users/Arthur Meira/Desktop/TCC/tests/test_webapp.py>).
- [Verificação posterior da base](<C:/Users/Arthur Meira/Desktop/TCC/results/validacao_ambiente_2026-10-12.json>) e [verificação da interface](<C:/Users/Arthur Meira/Desktop/TCC/results/interface-validation.json>).
- [Script de contagem e identificação dos PDFs](<C:/Users/Arthur Meira/Desktop/TCC/tmp/revisao_criteriosa_20261019/medir_artigo.py>), criado apenas para este diagnóstico.

**Conclusão da revisão:** preservar a estrutura e o núcleo metodológico; resolver referências, modelo/PDF e precisão das afirmações; depois fazer uma última conferência visual e de consistência. Não há fundamento para prometer aprovação pela banca, nem para exigir a reescrita integral ou um novo projeto experimental antes desses ajustes.
