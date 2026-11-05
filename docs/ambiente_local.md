# Preparação após a formatação — 12/10/2026

O ambiente Python está pronto e o PostgreSQL está instalado: o serviço
`postgresql-x64-18` está em execução, com início automático e porta 5432
aberta. A senha do `.env` foi corrigida e a conexão está validada.
O banco `tcc_sql_optimizer` e suas cinco tabelas foram criados e populados.
A extensão `pg_stat_statements` está carregada e a coleta foi validada.
O projeto também possui uma interface web local, o **Observatório SQL**.
Dê dois cliques em `Abrir interface.cmd` e comece por **Entenda o projeto**.
Veja [o guia da interface](interface.md) para usar e apresentar o protótipo.

## Instalado e verificado

| Componente | Estado |
| --- | --- |
| Python 3.14.7 | Instalado para o usuário |
| Ambiente virtual `.venv` | Criado na raiz do projeto |
| Psycopg e psycopg-binary 3.3.6 | Instalados conforme requirements-lock.txt |
| python-dotenv 1.2.3 e tzdata 2026.4 | Instalados conforme requirements-lock.txt |
| DBeaver Community 26.2.0 | Instalado para o usuário, com Java incluído |
| Git 2.56.0.windows.2 | Já estava instalado |
| PostgreSQL 18.6 | Serviço instalado e conexão validada |
| pg_stat_statements 1.12 | Extensão ativa, com coleta validada |

Verificações concluídas: `pip check`, compilação e importação dos módulos
Python existentes e prévia do workload (12 consultas, 730 execuções).
Também foram concluídos conexão, geração da base padrão e validação de
consistência: os cinco indicadores de erro retornaram zero. Os clientes
frequentes concentram 80,02% dos pedidos, conforme esperado.
O teste funcional concluiu as 12 consultas sem erro em 10,7 segundos.
A rodada completa concluiu 730 execuções sem erro em 55,8 segundos no cliente.
O coletor selecionou 12 consultas, com exatamente 730 chamadas. Os arquivos
CSV e JSON foram comparados campo a campo: quantidades, métricas, textos,
horário de coleta e IDs correspondem.
O analisador preventivo vinculou Q05 às 15 chamadas históricas e gerou os
alertas esperados. O comparador por e-mail mostrou `Seq Scan` na original e
`Index Scan` na alternativa, sem executar os SELECTs candidatos.

| Tabela | Registros confirmados |
| --- | ---: |
| clientes | 100.000 |
| produtos | 50.000 |
| pedidos | 1.000.000 |
| itens_pedido | 2.498.714 |
| pagamentos | 1.000.000 |

Relatório local: `results/validacao_ambiente_2026-10-12.json`.
Não execute novamente o gerador de dados neste banco.

## Usar o projeto agora

O serviço inicia automaticamente com o Windows. Abra o PowerShell na raiz
do projeto e use:

```powershell
.\.venv\Scripts\python.exe -m src.database
.\.venv\Scripts\python.exe -m src.analyzer --sql-file sql/candidate_query.sql
.\.venv\Scripts\python.exe -m src.collector --top 5 --no-export
```

A rodada de verificação está em `results/ambiente_2026-10-12/`:

- `query_metrics.csv` e `query_metrics.json`: métricas das 730 execuções.
- `workload.log` e `collector.log`: execução e coleta.
- `analyzer.log` e `compare_plans.log`: análise preventiva e comparação.

Os resultados estão ignorados pelo Git; faça uma cópia de segurança se quiser
preservá-los após outra formatação. Para novas medições, siga o roteiro do
README e escolha outra pasta de saída. Não repita a geração dos dados.
Não houve reset de métricas nesta validação: após o reinício, o filtro do
experimento estava vazio antes de executar as 730 chamadas.

O `.env` usa host `localhost`, porta `5432`, banco
`tcc_sql_optimizer`, usuário `postgres` e a senha escolhida na instalação. Ele está
ignorado pelo Git e tem acesso restrito ao usuário e ao sistema.

## Histórico dos bloqueios durante a instalação

Os eventos abaixo ocorreram antes de o serviço ser instalado com sucesso.
Não representam o estado atual descrito no início deste documento.

A ferramenta recusou a execução do instalador com elevação (`RunAs`).
Como alternativa, os binários oficiais foram extraídos em
`%LOCALAPPDATA%\TCC\PostgreSQL18\pgsql`, mas o Controle de Aplicativos
do Windows bloqueou `initdb.exe` com erro 4551. O log CodeIntegrity, evento
3077, confirmou a rejeição por política de assinatura/integridade.
Nenhuma proteção do Windows foi desativada e nenhum banco foi criado.

Atualização após a tentativa manual: os arquivos foram instalados em
`C:\Program Files\PostgreSQL\18`, mas a inicialização também falhou.
Às 13:49:14, o evento 3077 registrou o bloqueio do `initdb.exe` dessa pasta.
`Get-MpComputerStatus` confirmou `SmartAppControlState = On`, e o executável
`initdb.exe` não possui assinatura digital. A pasta de dados continua vazia
e não foi encontrado serviço PostgreSQL registrado. Repetir o mesmo
instalador sem resolver a compatibilidade com essa política não conclui
a instalação. A Microsoft informa que o Smart App Control não oferece
exceções individuais por aplicativo:
[documentação da Microsoft](https://support.microsoft.com/en-us/windows/security/threat-malware-protection/smart-app-control-frequently-asked-questions).

O instalador oficial tem assinatura válida da EnterpriseDB e SHA-256
conferido com o manifesto do WinGet:

```text
227e2bc08091b4c2b8338c7d61b11d057f895711480b006f90bfcfcd2410a58a
```

Ele está salvo em:

```text
C:\Users\Arthur Meira\Downloads\TCC-instaladores\postgresql-18.6-5-windows-x64.exe
```

1. Abra esse instalador pelo Explorador de Arquivos e confirme a solicitação
   do Windows, conferindo o editor EnterpriseDB.
2. Instale PostgreSQL Server e Command Line Tools. DBeaver já está instalado;
   pgAdmin e Stack Builder são opcionais para este projeto.
3. Use a porta `5432`. Para o usuário `postgres`, use a senha que está no
   campo `DB_PASSWORD` do `.env`, ou escolha outra e atualize esse campo.
4. Aguarde a conclusão. Se o Windows também bloquear o instalador ou a
   inicialização, registre a mensagem para análise da política responsável.

Fontes: [instalação oficial para Windows](https://www.postgresql.org/download/windows/)
e [binários fornecidos pela EDB](https://www.enterprisedb.com/download-postgresql-binaries).

## Roteiro para futuras instalações em banco vazio

As etapas de criação e população abaixo já foram concluídas neste PC.
Não as repita no banco atual. A instalação atual está concluída e validada.

No DBeaver, crie uma conexão PostgreSQL com host `localhost`, porta `5432`,
banco inicial `postgres`, usuário `postgres` e a senha escolhida. Na primeira
conexão, ele pode solicitar o download do driver PostgreSQL.

Crie o banco com auto-commit ativado:

```sql
CREATE DATABASE tcc_sql_optimizer;
```

Configure uma conexão com esse banco e execute `sql/schema.sql` inteiro.
Se o banco ou as tabelas já existirem, não os exclua nem recrie: confira o
estado antes de prosseguir.

Para habilitar a coleta, siga a Etapa 4 do README: acrescente
`pg_stat_statements` a `shared_preload_libraries` no `postgresql.conf`,
reinicie o serviço PostgreSQL e execute `sql/pg_stat_statements_setup.sql`
no banco do TCC. Preserve outras bibliotecas que já estejam configuradas.

Abra o PowerShell na pasta do projeto:

```powershell
.\.venv\Scripts\python.exe -m src.database
```

Após confirmar conexão e tabelas vazias, gere a base sintética padrão:

```powershell
.\.venv\Scripts\python.exe -m scripts.populate_database
```

A geração insere aproximadamente 4,65 milhões de registros. Depois do COMMIT,
execute `sql/validate_population.sql` no DBeaver e faça o teste funcional:

```powershell
.\.venv\Scripts\python.exe -m scripts.generate_workload --smoke
.\.venv\Scripts\python.exe -m src.analyzer --sql-file sql/candidate_query.sql
```

Para uma rodada de medição com 730 chamadas, siga a sequência de reset,
workload e coleta do README. Não repopule tabelas carregadas.
Os registros dos experimentos anteriores permanecem históricos; seus dados
e estatísticas não foram recuperados da instalação anterior.

## Uso do Python

Não é necessário ativar a `.venv` nem alterar a política do PowerShell.
Os comandos com `.venv\Scripts\python.exe` funcionam diretamente.
Abra um terminal novo para reconhecer o Python recém-instalado no PATH.

Se a `.venv` estiver ausente numa próxima instalação:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
.\.venv\Scripts\python.exe -m pip check
```

O README registra Python 3.14.3 e PostgreSQL 18.1 no experimento antigo.
Esta preparação usa Python 3.14.7 e baixou PostgreSQL 18.6. Registre a versão
efetivamente instalada antes de comparar novas medições.
