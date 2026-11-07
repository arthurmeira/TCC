"use strict";
const $ = id => document.getElementById(id);
const esc = value => String(value ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const number = (value, digits = 0) => Number(value).toLocaleString("pt-BR", {maximumFractionDigits:digits});
const duration = ms => ms >= 1000 ? `${number(ms / 1000, 2)} s` : `${number(ms, 2)} ms`;
const dateLabel = value => new Date(value).toLocaleString("pt-BR");
const state = {presets:null, analysis:null, comparison:null, page:"logs", logs:null, observed:null, source:"postgres", investigation:null, report:null, reports:[], queryId:null, sourceEventId:null, selectionReason:null, measurementCalls:3};
const attentionLabel = value => ({alto:"alta",médio:"média",baixo:"baixa"}[value] || value);
const levels = {alta:"high",alto:"high",média:"medium",médio:"medium",baixa:"low",baixo:"low"};
function pill(label, kind) { return `<span class="pill ${levels[kind] || "neutral"}">${esc(label)}</span>`; }
function message(id, text) { $(id).textContent = text || ""; $(id).hidden = !text; }
async function api(path, body) {
  const response = await fetch(path, body === undefined ? {} : {
    method:"POST", headers:{"Content-Type":"application/json", "X-TCC-Client":"local"}, body:JSON.stringify(body)
  });
  let result;
  try { result = await response.json(); } catch { throw new Error("A interface perdeu a conexão. Confira se sua janela de inicialização continua aberta."); }
  if (!response.ok) throw new Error(result.error || "Não foi possível concluir a operação.");
  return result;
}
function showPage(page, updateHash = true) {
  if($("investigation-dialog").open) $("investigation-dialog").close();
  if (!["logs","history"].includes(page)) page = "logs";
  state.page = page;
  document.querySelectorAll(".page").forEach(section => section.hidden = section.id !== `page-${page}`);
  document.querySelectorAll("[data-page]").forEach(button => {
    button.classList.toggle("active",button.dataset.page === page);
    if (button.dataset.page === page) button.setAttribute("aria-current","page"); else button.removeAttribute("aria-current");
  });
  if (updateHash) history.replaceState(null,"",`#${page}`);
  window.scrollTo({top:0,behavior:"instant"});
}
function selectExample(id) {
  const example = state.presets?.queries.find(query => query.id === id);
  if (!example) return;
  $("query-select").value = id;
  $("sql-input").value = example.sql;
  $("query-description").textContent = example.description;
  invalidateAnalysis();
}
function invalidateAnalysis() { state.analysis = null; $("analysis-result").replaceChildren(); message("analysis-error",""); }
function invalidateComparison() { state.comparison = null; state.report=null; $("benchmark-result").replaceChildren(); message("benchmark-error",""); $("comparison-result").replaceChildren(); message("comparison-error",""); }
function download(name, data) {
  const url = URL.createObjectURL(new Blob([JSON.stringify(data,null,2)],{type:"application/json;charset=utf-8"}));
  const link = document.createElement("a"); link.href = url; link.download = name; link.click();
  setTimeout(() => URL.revokeObjectURL(url),1000);
}
function metric(label, value, note) { return `<article class="metric"><span>${esc(label)}</span><strong>${esc(value)}</strong><small>${esc(note)}</small></article>`; }
const translations = {
  "Seq Scan":"Percorre os registros da tabela", "Index Scan":"Localiza registros com um índice",
  "Index Only Scan":"Obtém informações diretamente do índice", "Bitmap Heap Scan":"Busca na tabela as posições encontradas por índice",
  "Bitmap Index Scan":"Encontra posições por índice", "Gather":"Reúne o trabalho dos processos",
  "Gather Merge":"Reúne os resultados mantendo a ordem", "Hash Join":"Combina tabelas usando uma estrutura de busca",
  "Nested Loop":"Combina registros por buscas repetidas", "Merge Join":"Combina entradas ordenadas",
  "Hash":"Prepara uma estrutura de busca", "Sort":"Ordena os resultados", "Aggregate":"Agrupa ou resume os dados",
  "Limit":"Limita a quantidade de resultados", "Materialize":"Guarda um resultado intermediário",
};
function planNode(node) {
  return `<li><div><strong>${esc(node["Node Type"])}</strong>${node["Relation Name"] ? ` · ${esc(node["Relation Name"])}` : ""}<small>${esc(translations[node["Node Type"]] || "Operação do planejador PostgreSQL")} · ${number(node["Plan Rows"] || 0)} ${node["Plan Rows"] === 1 ? "linha estimada" : "linhas estimadas"}</small></div>${node.Plans?.length ? `<ul>${node.Plans.map(planNode).join("")}</ul>` : ""}</li>`;
}
function planTree(result) { return `<ul class="plan-tree">${planNode(result.plan.Plan)}</ul>`; }
function improvementsHtml(result) {
  const info = result.improvements || {proposals:[], notes:[]};
  const rewrites = info.proposals.some(p => p.kind === "rewrite");
  return `<article class="panel improvements">
    <span class="eyebrow">ANÁLISE POR REGRAS</span><h2>Possíveis melhorias</h2>
    <p class="muted">Cada sugestão é uma hipótese. Compare o plano e meça antes de adotar uma mudança.</p>
    ${!rewrites ? '<div class="notice info"><strong>Nenhuma reescrita recomendada.</strong> As regras não encontraram uma alteração aplicável à consulta. Isso não comprova que ela já tenha o melhor desempenho possível.</div>' : ''}
    ${info.proposals.map((proposal, i) => `<section class="proposal">
      <div class="result-toolbar"><h3>${esc(proposal.title)}</h3>${pill(proposal.kind === 'rewrite' ? 'Consulta alternativa' : 'Índice sugerido', 'neutral')}</div>
      <p>${esc(proposal.explanation)}</p>
      <pre class="proposal-sql">${esc(proposal.sql)}</pre>
      <details><summary>Evidência e condições</summary><p><strong>Evidência:</strong> ${esc(proposal.evidence)}</p><p>${esc(proposal.conditions)}</p><p>${esc(proposal.status)}</p></details>
      <div class="proposal-actions"><button type="button" class="text-button" data-copy-proposal="${i}">Copiar SQL</button>${proposal.kind === 'rewrite' ? `<button type="button" class="button primary" data-compare-proposal="${i}">Comparar e validar →</button>` : '<p class="footnote">Este índice não foi criado. Sua avaliação exige um teste próprio.</p>'}</div>
    </section>`).join('')}
    ${info.notes.map(note => `<p class="footnote">${esc(note)}</p>`).join('')}
    ${!info.proposals.length ? '<p class="muted">Não há outra proposta concreta para esta consulta.</p>' : ''}
  </article>`;
}
function bindImprovements(result) {
  document.querySelectorAll('[data-copy-proposal]').forEach(button => button.addEventListener('click', async () => {
    try {
      await navigator.clipboard.writeText(result.improvements.proposals[Number(button.dataset.copyProposal)].sql);
      button.textContent = 'SQL copiado';
    } catch { button.textContent = 'Selecione o SQL acima e copie manualmente'; }
  }));
  document.querySelectorAll('[data-compare-proposal]').forEach(button => button.addEventListener('click', () => {
    const proposal = result.improvements.proposals[Number(button.dataset.compareProposal)];
    state.queryId = result.logContext?.queryId || null;
    state.sourceEventId = result.logContext?.sourceEventId || null;
    state.selectionReason = result.logContext?.selectionReason || null;
    $("original-sql").value = result.sql;
    $("alternative-sql").value = proposal.sql;
    $("comparison-description").textContent = proposal.title;
    $("comparison-condition").textContent = proposal.conditions;
    invalidateComparison();
    showPage('compare');
    $("compare-form").requestSubmit();
  }));
}
function renderAnalysis(result) {
  const history = result.history;
  const historyBox = history ? `<div class="history-box"><h3>Histórico de execução</h3><div class="history-values"><div><strong>${number(history.calls)}</strong><span>execuções registradas</span></div><div><strong>${duration(history.mean_exec_time)}</strong><span>tempo médio medido no servidor</span></div><div><strong>${number(history.rows / history.calls)}</strong><span>linhas por execução, em média</span></div></div><p class="footnote">Esses valores vêm de execuções anteriores. Analisar o plano não acrescenta uma execução deste SELECT.</p></div>` : '<div class="history-box"><h3>Esta consulta ainda não tem histórico correspondente.</h3>O plano pode ser analisado normalmente. Nenhum tempo de execução foi inventado ou medido nesta análise.</div>';
  $("analysis-result").innerHTML = `<div class="result-heading"><div><span class="eyebrow">${result.plan_kind==="generic"?"PLANO GENÉRICO · SEM OS VALORES ORIGINAIS":"RESULTADO DA ANÁLISE"}</span><h2>Análise da consulta</h2></div><div class="result-score">${pill(`Atenção ${attentionLabel(result.attention_level)}`,result.attention_level)}</div></div><p class="muted">A triagem usa regras e o plano estimado. Um alerta indica o que vale investigar; não confirma lentidão.</p><div class="result-metrics">${metric("Linhas esperadas pelo plano",number(result.estimated_rows),"Estimativa de registros retornados")}${metric("Custo estimado",number(result.total_cost,2),"Unidade do planejador, não milissegundos")}${metric("Operação principal",result.root_node,translations[result.root_node] || "Etapa no topo do plano")}</div>${historyBox}${improvementsHtml(result)}<article class="panel"><div class="result-toolbar"><h2>${result.findings.length ? "Evidências e sugestões" : "Nenhum padrão de alerta identificado"}</h2><button class="text-button" id="download-analysis">↓ Baixar análise</button></div>${result.findings.length ? result.findings.map((finding,index) => `<div class="finding"><span class="finding-number">${String(index+1).padStart(2,"0")}</span><div><h3>${esc(finding.title)} ${pill(finding.severity,finding.severity)}</h3><p><span class="finding-label">Evidência.</span>${esc(finding.evidence)}</p><p><span class="finding-label">O que investigar.</span>${esc(finding.recommendation)}</p></div></div>`).join("") : '<p class="muted">Isso significa apenas que as regras atuais não encontraram seus padrões. Não comprova que a consulta será rápida.</p>'}<details><summary>Ver plano estimado</summary><p class="footnote">A árvore mostra operações e estimativas do PostgreSQL. Os dados fluem dos ramos inferiores para o topo.</p>${planTree(result)}</details><details><summary>Ver o plano técnico completo (JSON)</summary><pre>${esc(JSON.stringify(result.plan,null,2))}</pre></details><p class="footnote">Consulta não executada · Analisado em ${esc(dateLabel(result.analyzed_at))} · Query ID ${esc(result.query_id || "indisponível")}</p></article>`;
  bindImprovements(result);
  $("download-analysis").addEventListener("click",() => download("analise-consulta.json",result));
}
function renderComparison(result) {
  const a = result.original, b = result.alternative;
  const delta = a.total_cost > 0 ? (b.total_cost-a.total_cost)/a.total_cost*100 : null;
  const row = (name,original,alternative) => `<tr><td>${esc(name)}</td><td>${original}</td><td>${alternative}</td></tr>`;
  $("comparison-result").innerHTML = `<div class="result-heading"><div><span class="eyebrow">PLANOS LADO A LADO</span><h2>Comparação dos planos</h2></div></div><article class="panel"><table class="comparison-table"><thead><tr><th scope="col">O que comparar</th><th scope="col">Original</th><th scope="col">Alternativa</th></tr></thead><tbody>${row("Operação principal",esc(a.root_node),esc(b.root_node))}${row("Custo estimado",number(a.total_cost,2),number(b.total_cost,2))}${row("Linhas estimadas",number(a.estimated_rows),number(b.estimated_rows))}${row("Atenção das regras",esc(attentionLabel(a.attention_level)),esc(attentionLabel(b.attention_level)))}</tbody></table><p class="muted">${delta === null ? "Não há base para calcular a variação percentual de custo." : `Variação do custo estimado: ${delta > 0 ? "+" : ""}${number(delta,2)}%.`} Custo não é tempo. Um custo maior pode refletir uma estimativa mais realista da quantidade de dados.</p><details class="plan-detail"><summary>Ver detalhes dos planos</summary><div class="comparison-trees"><div><h3>Plano original</h3>${planTree(a)}</div><div><h3>Plano alternativo</h3>${planTree(b)}</div></div></details>${a.history ? `<div class="history-box"><h3>Referência histórica da original</h3>${number(a.history.rows/a.history.calls)} ${a.history.rows/a.history.calls===1?"linha":"linhas"} por execução e ${duration(a.history.mean_exec_time)} de tempo médio, em ${number(a.history.calls)} chamadas anteriores. Esses valores não são uma medição da alternativa.</div>` : ""}<button id="download-comparison" class="text-button">↓ Baixar comparação em JSON</button></article>`;
  $("download-comparison").addEventListener("click",() => download("comparacao-planos.json",result));
}
document.querySelectorAll("[data-page]").forEach(button => button.addEventListener("click",() => showPage(button.dataset.page)));
window.addEventListener("hashchange",() => showPage(location.hash.slice(1),false));
$("query-select").addEventListener("change",event => {
  if (event.target.value === "custom") { $("sql-input").value=""; $("query-description").textContent="Escreva sua pergunta ao banco usando uma instrução SELECT."; invalidateAnalysis(); }
  else selectExample(event.target.value);
});
$("sql-input").addEventListener("input",() => {
  $("query-select").value="custom"; $("query-description").textContent="Consulta editada por você. A análise usará exatamente o SQL abaixo."; invalidateAnalysis();
});
for (const id of ["original-sql","alternative-sql"]) $(id).addEventListener("input",()=>{ invalidateComparison(); if(id==="original-sql"&&!state.sourceEventId)state.queryId=null; $("comparison-condition").textContent="Consultas editadas. Verifique se retornam os mesmos dados antes de adotar a alteração."; });
$("analyze-form").addEventListener("submit",async event => {
  event.preventDefault(); const sql = $("sql-input").value;
  invalidateAnalysis(); const button=$("analyze-button"); button.disabled=true; button.textContent="Analisando e buscando melhorias…";
  try {
    const result=await api("/api/analyze",{sql});
    if ($("sql-input").value === sql) { state.analysis=result; renderAnalysis(result); $("analysis-result").scrollIntoView({behavior:"smooth",block:"start"}); }
  } catch(error) { message("analysis-error",error.message); }
  finally { button.disabled=false; button.textContent="Analisar e propor melhorias →"; }
});
$("compare-form").addEventListener("submit",async event => {
  event.preventDefault(); const original=$("original-sql").value, alternative=$("alternative-sql").value;
  invalidateComparison(); const button=$("compare-button"); button.disabled=true; button.textContent="Comparando planos…";
  try {
    const result=await api("/api/compare",{original,alternative});
    if ($("original-sql").value === original && $("alternative-sql").value === alternative) { state.comparison=result; renderComparison(result); $("comparison-result").scrollIntoView({behavior:"smooth",block:"start"}); }
  } catch(error) { message("comparison-error",error.message); }
  finally { button.disabled=false; button.textContent="Comparar planos ⇄"; }
});
async function start() {
  showPage(location.hash.slice(1),false);
  try {
    state.presets = await api("/api/presets");
    const exampleOption=q=>`<option value="${esc(q.id)}">${esc(q.id)} · ${esc(q.title)}</option>`;
    $("query-select").innerHTML=state.presets.queries.map(exampleOption).join('')+'<option value="custom">Minha própria consulta</option>';
    $("run-example-select").innerHTML='<option value="">Escolha uma consulta</option>'+state.presets.queries.map(exampleOption).join('');
    selectExample("C01");
    $("comparison-condition").textContent="Confira se as duas consultas retornam os mesmos dados.";
  } catch(error) { message("global-error",error.message); }
  await loadLogs();
}

$("run-example-select").addEventListener('change',event=>{
  const example=state.presets?.queries.find(q=>q.id===event.target.value);
  $("run-example").disabled=!example;
  $("run-example-description").textContent=example?.description||'';
  $("run-example-sql").textContent=example?.sql||'';
  $("run-example-sql").hidden=!example;
  message('run-example-status','');message('run-example-error','');
});
$("run-example").addEventListener('click',async()=>{
  const button=$("run-example"),select=$("run-example-select"),id=select.value;
  if(!id)return;
  button.disabled=true;select.disabled=true;message('run-example-error','');message('run-example-status','Executando a consulta no banco de teste…');
  try{
    const result=await api('/api/presets/execute',{id});
    message('run-example-status',`${result.title}: execução concluída (${number(result.rows)} linhas). Atualizando estatísticas…`);
    try{
      await api('/api/statements/sync',{});state.source='postgres';await loadLogs();
      message('run-example-status',`${result.title}: execução concluída (${number(result.rows)} linhas) e estatísticas atualizadas. Procure a consulta na lista abaixo; ela pode estar agrupada com chamadas anteriores.`);
    }catch(error){message('run-example-status',`${result.title}: execução concluída (${number(result.rows)} linhas). A atualização das estatísticas falhou; use Atualizar consultas.`);message('run-example-error',error.message);}
  }catch(error){message('run-example-status','');message('run-example-error',error.message);}
  finally{button.disabled=false;select.disabled=false;}
});

function shortSql(sql) { return sql.replace(/\/\*[\s\S]*?\*\//g, "").replace(/\s+/g," ").trim(); }
const pageState={logs:1,history:1},pageSize=10;
function paginate(items,kind){
  const count=Math.ceil(items.length/pageSize);
  pageState[kind]=Math.max(1,Math.min(pageState[kind],count||1));
  const nav=$(kind==='logs'?'log-pagination':'history-pagination');
  nav.innerHTML=count>1?Array.from({length:count},(_,i)=>`<button type="button" data-pagination="${kind}" data-number="${i+1}" ${pageState[kind]===i+1?'aria-current="page"':''} aria-label="Página ${i+1}">${i+1}</button>`).join(''):'';
  return items.slice((pageState[kind]-1)*pageSize,pageState[kind]*pageSize);
}
document.addEventListener('click',event=>{const button=event.target.closest('[data-pagination]');if(!button)return;const kind=button.dataset.pagination;pageState[kind]=Number(button.dataset.number);if(kind==='logs')renderLogList();else renderHistory();});
function renderHistory(){
  $('report-count').textContent=`(${state.reports.length})`;
  $('export-history').disabled=!state.reports.length;
  const outcome=r=>['no_proposal','not_equivalent','plan_unavailable'].includes(r.status)?r.status:r.reduction_pct==null?'unknown':r.reduction_pct>0?'faster':r.reduction_pct<0?'slower':'same';
  const labels={faster:'Tempo menor',slower:'Tempo maior',same:'Sem diferença',unknown:'Não informado',no_proposal:'Sem alternativa automática',not_equivalent:'Resultados diferentes',plan_unavailable:'Plano indisponível'};
  const count=key=>state.reports.filter(r=>outcome(r)===key).length;
  $('history-overview').innerHTML=[['Registros',state.reports.length,'Total apresentado'],['Tempo menor',count('faster'),'Alternativa mais rápida'],['Tempo maior',count('slower'),'Alternativa mais lenta'],['Sem resultado medido',count('no_proposal')+count('not_equivalent')+count('plan_unavailable')+count('unknown'),'Sem comparação de tempo']].map(([title,value,note])=>`<div class="history-stat"><span>${title}</span><strong>${number(value)}</strong><small>${note}</small></div>`).join('');
  const term=$('history-search').value.trim().toLocaleLowerCase('pt-BR'),filter=$('history-filter').value;
  const visible=state.reports.map((r,i)=>({r,i})).filter(({r})=>(filter==='all'||outcome(r)===filter)&&(!term||[r.original_sql,r.alternative_sql,r.rule,r.id].some(v=>String(v||'').toLocaleLowerCase('pt-BR').includes(term))));
  const groups=new Map();
  for(const item of visible){
    const key=item.r.original_sql ? JSON.stringify([item.r.original_sql.trim(),item.r.alternative_sql?.trim()||'',item.r.status||'measured']) : `sem-sql-${item.i}`;
    if(!groups.has(key))groups.set(key,[]);
    groups.get(key).push(item);
  }
  $('history-filter-count').textContent=state.reports.length?`${groups.size} pares de consultas · ${visible.length} de ${state.reports.length} rodadas exibidas` : '';
  const displayedGroups=paginate(Array.from(groups.values()),'history');
  $('saved-reports').innerHTML=visible.length ? displayedGroups.map((items,index)=>{
    const rowNumber=(pageState.history-1)*pageSize+index+1;
    const latest=items[0].r, snippet=shortSql(latest.original_sql||'SQL original indisponível');
    if(['no_proposal','not_equivalent','plan_unavailable'].includes(latest.status))return `<details class="history-pair"><summary class="history-pair-heading"><span class="list-row-number history-row-number">${rowNumber}</span><div><span class="history-group-count">${items.length} ${items.length===1?'registro':'registros'} · última: ${esc(dateLabel(latest.created_at))}</span><strong class="history-query">${esc(snippet)}</strong></div><span class="history-pair-change">${esc(labels[latest.status])}</span><span class="history-open">Ver detalhes ↓</span></summary><div class="history-pair-content"><p>${esc(latest.reason||labels[latest.status])}</p><p class="footnote">Não há tempos de comparação para este registro.</p><details><summary>Ver consultas completas</summary><h4>Original</h4><pre>${esc(latest.original_sql||'Indisponível')}</pre>${latest.alternative_sql?`<h4>Alternativa</h4><pre>${esc(latest.alternative_sql)}</pre>`:''}</details><button class="text-button" type="button" data-history-group="${items.map(x=>x.i).join(',')}">↓ Baixar registros em JSON</button></div></details>`;
    const samples=side=>items.flatMap(({r})=>Array.isArray(r.metrics?.[side]?.samples_ms)?r.metrics[side].samples_ms.filter(v=>typeof v==='number'&&Number.isFinite(v)):[]);
    const original=samples('original'),alternative=samples('alternative');
    const average=values=>values.length?values.reduce((sum,v)=>sum+v,0)/values.length:null;
    const stat=v=>v==null?'Indisponível':duration(v);
    const meanOriginal=average(original),meanAlternative=average(alternative);
    const change=meanOriginal>0&&meanAlternative!=null?(meanAlternative-meanOriginal)/meanOriginal*100:null;
    const changeText=change==null?'Comparação indisponível':`${number(Math.abs(change),2)}% ${change<0?'menor':change>0?'maior':'de diferença'} no tempo médio da alternativa`;
    const row=(label,values)=>`<tr><td>${label}</td><td>${number(values.length)}</td><td>${stat(average(values))}</td><td>${stat(values.length?Math.min(...values):null)}</td><td>${stat(values.length?Math.max(...values):null)}</td></tr>`;
    return `<details class="history-pair"><summary class="history-pair-heading"><span class="list-row-number history-row-number">${rowNumber}</span><div><span class="history-group-count">${items.length} ${items.length===1?'rodada':'rodadas'} · última: ${esc(dateLabel(latest.created_at))}</span><strong class="history-query">${esc(snippet)}</strong></div><span class="history-pair-change ${change==null?'unavailable':change<0?'faster':change>0?'slower':'same'}">${changeText}</span><span class="history-open">Ver detalhes ↓</span></summary><div class="history-pair-content"><table class="comparison-table"><thead><tr><th>Versão</th><th>Execuções medidas</th><th>Tempo médio</th><th>Menor tempo</th><th>Maior tempo</th></tr></thead><tbody>${row('Original',original)}${row('Alternativa',alternative)}</tbody></table><p class="footnote">Resumo das amostras disponíveis nas rodadas exibidas; aquecimentos não incluídos.</p><details><summary>Ver consultas completas</summary><h4>Original</h4><pre>${esc(latest.original_sql||'Indisponível')}</pre><h4>Alternativa</h4><pre>${esc(latest.alternative_sql||'Indisponível')}</pre></details><button class="text-button" type="button" data-history-group="${items.map(x=>x.i).join(',')}">↓ Baixar relatórios deste resumo em JSON</button></div></details>`;
  }).join('') : `<p class="muted">${state.reports.length?'Nenhuma medição corresponde à busca ou ao filtro.':'Nenhuma medição salva. Investigue uma consulta e clique em Medir desempenho para registrar uma rodada.'}</p>`;
}
$('history-search').addEventListener('input',()=>{pageState.history=1;renderHistory();});
$('history-filter').addEventListener('change',()=>{pageState.history=1;renderHistory();});
$('export-history').addEventListener('click',()=>{
  const cols=['id','data','resultado','status','motivo','regra','banco','versao_postgresql','repeticoes','equivalentes','mediana_original_ms','mediana_alternativa_ms','media_original_ms','media_alternativa_ms','minimo_original_ms','minimo_alternativa_ms','maximo_original_ms','maximo_alternativa_ms','reducao_mediana_percentual','sql_original','sql_alternativa'];
  const cell=v=>{let s=String(v??'');if(/^[\s]*[=+@\t\r]/.test(s))s="'"+s;return '"'+s.replace(/"/g,'""')+'"';};
  const lines=state.reports.map(r=>{const a=r.metrics?.original||{},b=r.metrics?.alternative||{};return [r.id,r.created_at,r.verdict,r.status||'medido',r.reason,r.rule,r.environment?.database,r.environment?.postgresql_version,a.calls,r.equivalent,a.median_ms,b.median_ms,a.mean_ms,b.mean_ms,a.min_ms,b.min_ms,a.max_ms,b.max_ms,r.reduction_pct,r.original_sql,r.alternative_sql].map(cell).join(';');});
  const url=URL.createObjectURL(new Blob(['\ufeff',cols.map(cell).join(';'),'\r\n',lines.join('\r\n')],{type:'text/csv;charset=utf-8'}));
  const link=document.createElement('a');link.href=url;link.download='historico-medicoes.csv';link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
});
$('saved-reports').addEventListener('click',event=>{const button=event.target.closest('[data-history-group]');if(button){const reports=button.dataset.historyGroup.split(',').map(i=>state.reports[Number(i)]);download('medicoes-da-consulta.json',reports);}});
async function loadLogs() {
  try {
    const source=state.source;
    const data=await api(source==='logs'?'/api/logs':'/api/statements');
    if(source==='logs')state.logs=data;else state.observed=data;
    renderLogList();
    state.reports=(await api("/api/reports")).reports;
    $("report-count").textContent=`(${state.reports.length})`;
    renderHistory();
  } catch(error) { message("log-error",error.message); }
}
function addReviewMarkers(queries){
  const byId=new Map(queries.map(q=>[q.id,q]));
  $("log-list").querySelectorAll('[data-investigate]').forEach(button=>{
    const q=byId.get(button.dataset.investigate), signal=q?.review;
    if(!signal)return;
    const cell=button.closest('tr').querySelector('td');
    const box=document.createElement(signal.needed?'details':'p');
    box.className='query-review '+(signal.needed?'needs-review':'no-review');
    if(signal.needed){
      const title=document.createElement('summary');title.textContent='⚑ '+signal.label;box.append(title);
      const list=document.createElement('ul');
      signal.reasons.forEach(reason=>{const li=document.createElement('li');li.textContent=reason;list.append(li);});
      box.append(list);
      const note=document.createElement('p');note.textContent=signal.method;box.append(note);
    }else{box.textContent=signal.label;box.title=signal.method||signal.label;}
    cell.append(box);
  });
}
function renderLogList() {
  const postgres=state.source==='postgres',data=postgres?state.observed:state.logs;
  if(!data)return;
  $("sync-queries").hidden=!postgres;
  $("log-import-form").hidden=postgres;
  $("log-batches").hidden=postgres;
  $("source-description").textContent=postgres?'Estatísticas acumuladas por estrutura de consulta; valores originais podem estar ausentes.':'Tempos dos eventos importados. Investigar usa a execução de maior duração de cada grupo.';
  if(!postgres)$("log-batch-list").innerHTML=data.imports.length?data.imports.map(b=>`<article><strong>${esc(b.source)}</strong><p>${number(b.accepted)} aceitos · ${number(b.ignored)} ignorados · importado em ${esc(dateLabel(b.imported_at))}</p><details><summary>Identificador SHA-256 do conteúdo</summary><code>${esc(b.id)}</code></details></article>`).join(''):'<p>Nenhum arquivo importado.</p>';
  $("log-metrics").innerHTML=metric(postgres?"Execuções acumuladas":"Execuções nos logs",number(data.calls),postgres?"Contadores atuais do PostgreSQL":"Registros individuais importados")+metric("Consultas agrupadas",number(data.queries.filter(q=>q.active!==false).length),postgres?"Banco, usuário e Query ID":"Estruturas SQL normalizadas")+metric("Tempo registrado",duration(data.total_ms),postgres?"Acumulado das entradas atuais":"Soma das durações dos logs");
  document.querySelectorAll("[data-source]").forEach(button=>{button.classList.toggle("active",button.dataset.source===state.source);button.setAttribute("aria-pressed",String(button.dataset.source===state.source));});
  const context=state.observed?.latest?.context;
  $("sync-context").textContent=!postgres?'Fonte: arquivos de log · Coletar exemplos reais executa consultas de demonstração e importa seus registros. Importar arquivo apenas lê o conteúdo.':context?`Banco: ${context.database_name} · Última atualização: ${dateLabel(context.captured_at)}${context.can_read_other_users?"":" · Visibilidade limitada às consultas do usuário conectado"}`:"Banco: tcc_sql_optimizer_logs · Atualizar estatísticas não executa as consultas observadas.";
  const labels={new:"Nova",updated:"Atualizada",unchanged:"Sem alteração",restarted:"Nova base após reinício"};
  const sort=$("log-sort").value;
  const activity=q=>{
    const raw=postgres?q.last_activity:q.last_seen;
    const parsed=raw?Date.parse(raw.replace(/ ([+-]\d{2})$/, "$1:00")):NaN;
    return Number.isFinite(parsed)?parsed:null;
  };
  const queries=[...data.queries].sort((a,b)=>{
    const active=Number(b.active!==false)-Number(a.active!==false);if(active)return active;
    if(sort==="recent"||sort==="oldest"){
      const x=activity(a),y=activity(b);
      if(x===null||y===null)return x===y?0:x===null?1:-1;
      return sort==="recent"?y-x:x-y;
    }
    return b[sort]-a[sort];
  });
  const displayedQueries=paginate(queries,'logs');
  $("log-list").innerHTML=queries.length ? displayedQueries.map((q,index)=>{
    const n=(pageState.logs-1)*pageSize+index+1;
    const signal=q.review, active=signal?.needed;
    const when=activity(q)===null?'Não identificada':dateLabel(activity(q));
    const user=postgres?`${q.user_name} · ${q.active===false?'Fora do snapshot atual':labels[q.status]}`:`${number(q.variants)} ${q.variants===1?'variante':'variantes'}`;
    return `<article class="history-pair observed-card"><div class="history-pair-heading observed-card-heading"><span class="list-row-number query-row-number">${n}</span><div class="observed-card-main"><span class="history-group-count">${esc(user)} · ${number(q.calls)} chamadas · ${duration(q.total_ms)} no total · ${duration(q.mean_ms)} em média</span><strong class="history-query" title="${esc(shortSql(q.sql))}">${esc(shortSql(q.sql))}</strong><span class="history-group-count">Atividade detectada: ${esc(when)}</span></div><span class="observed-review ${active?'needs-review':'no-review'}">${esc(signal?.label||'Sem sinal nesta triagem')}</span><button class="text-button observed-investigate" type="button" data-investigate="${esc(q.id)}">Investigar →</button></div></article>`;
  }).join('') : `<div class="empty"><strong>${postgres?'Busque as consultas observadas pelo banco.':'Comece pelos registros de execução.'}</strong><p>${postgres?'Execute consultas nas tabelas do banco tcc_sql_optimizer_logs pelo DBeaver e clique em Atualizar consultas.':'Importe um arquivo de log para começar.'}</p></div>`;
}
document.querySelectorAll("[data-source]").forEach(button=>button.addEventListener("click",async()=>{state.source=button.dataset.source;$("log-investigation").replaceChildren();state.investigation=null;message('log-status','');message('log-error','');await loadLogs();}));
$("sync-queries").addEventListener("click",async()=>{
  const button=$("sync-queries");button.disabled=true;button.textContent="Sincronizando…";message("log-error","");message("log-status","Lendo as estatísticas do PostgreSQL…");
  try{
    const result=await api("/api/statements/sync",{});state.source="postgres";await loadLogs();
    $("log-investigation").replaceChildren();state.investigation=null;
    message("log-status",`${result.new} novas · ${result.updated} atualizadas · ${result.unchanged} sem alteração${result.restarted?` · ${result.restarted} com contadores reiniciados`:""}${result.unavailable?` · ${result.unavailable} fora do snapshot atual`:""}.${result.initial?" Primeira leitura: os valores incluem o acumulado disponível no banco.":""}${result.global_reset?" O PostgreSQL reiniciou as estatísticas; uma nova base foi registrada.":""}`);
  }catch(error){message("log-error",error.message);message("log-status","");}
  finally{button.disabled=false;button.textContent="↻ Atualizar consultas";}
});
$("log-sort").addEventListener("change",()=>{pageState.logs=1;renderLogList();});
$("log-import-form").addEventListener('submit',async event=>{
  event.preventDefault();
  const file=$("log-file").files[0],button=$("import-log-button");
  if(!file)return;
  button.disabled=true;message('log-error','');message('log-status','Importando registros…');
  try{
    if(file.size>20*1024*1024)throw new Error('Selecione um arquivo de até 20 MB.');
    const content=new TextDecoder('utf-8',{fatal:true}).decode(await file.arrayBuffer());
    const result=await api('/api/logs/import',{content,filename:file.name,database_confirmed:$("log-database-confirmed").checked});
    state.source='logs';await loadLogs();
    message('log-status',result.duplicate?'Este conteúdo já foi importado. Nenhum registro foi duplicado.':`${result.accepted} execuções aceitas · ${result.ignored} registros ignorados. Selecione uma consulta para investigar.`);
  }catch(error){message('log-error',error.message);message('log-status','');}
  finally{button.disabled=false;}
});
let investigationRequest=0;
let investigationTrigger=null;
let previousBodyOverflow="";
function openInvestigation(){
  const dialog=$("investigation-dialog");
  if(!dialog.open){previousBodyOverflow=document.body.style.overflow;document.body.style.overflow="hidden";dialog.showModal();}
}
$("close-investigation").addEventListener("click",()=>$("investigation-dialog").close());
$("investigation-dialog").addEventListener("close",()=>{
  investigationRequest++;document.body.style.overflow=previousBodyOverflow;
  if(investigationTrigger?.isConnected&&!investigationTrigger.disabled&&!investigationTrigger.closest("[hidden]"))investigationTrigger.focus({preventScroll:true});
});
$("investigation-dialog").addEventListener("click",event=>{
  if(event.target!==$("investigation-dialog"))return;
  const r=event.target.getBoundingClientRect();
  if(event.clientX<r.left||event.clientX>r.right||event.clientY<r.top||event.clientY>r.bottom)event.target.close();
});
function sqlMarkup(sql){
  const tokens=sql.split(/('(?:''|[^'])*'|"(?:""|[^"])*"|\$\d+|\b(?:SELECT|FROM|WHERE|JOIN|INNER|LEFT|RIGHT|FULL|OUTER|ON|AS|AND|OR|NOT|IN|IS|NULL|TRUE|FALSE|GROUP|BY|ORDER|HAVING|LIMIT|OFFSET|ASC|DESC|WITH|DISTINCT|UNION|ALL|CASE|WHEN|THEN|ELSE|END|BETWEEN|EXISTS)\b)/gi);
  return tokens.map((token,index)=>index%2?`<span class="${token.startsWith("'")?'sql-string':token.startsWith('"')?'sql-name':token.startsWith('$')?'sql-param':'sql-keyword'}">${esc(token)}</span>`:esc(token)).join("");
}
function logEvidenceHtml(q){
  const e=q.selected_event;
  if(!e)return '';
  const batch=q.batches.find(b=>b.id===e.import_id);
  return `<section class="panel"><h3>Origem da consulta</h3><p><strong>Arquivo:</strong> ${esc(batch?.source||'Não identificado')}<br><strong>Banco no registro:</strong> ${esc(e.database_name||'Não informado; análise na conexão atual')}<br><strong>Execução selecionada:</strong> ${esc(e.occurred_at||'Horário não informado')} · ${duration(e.duration_ms)}</p><p class="footnote">${esc(q.sample_policy)} O grupo contém ${number(q.variants)} variante(s) e ${number(q.batches.length)} lote(s). A média do grupo não substitui os valores desta execução.</p><details><summary>Lote e evento de origem</summary><p>SHA-256 do conteúdo: <code>${esc(e.import_id)}</code></p><p>Evento: <code>${esc(e.id)}</code></p></details><label for="log-selection-reason">Por que você selecionou esta consulta?</label><textarea id="log-selection-reason" rows="2" maxlength="2000" placeholder="Ex.: maior tempo acumulado entre as consultas do lote." style="width:100%"></textarea><p class="footnote">O motivo será salvo junto à origem quando você medir a alternativa.</p><p id="log-selection-error" class="notice error" hidden role="alert"></p></section>`;
}
function logSelection(q){
  if(!q.selected_event)return null;
  const input=$('log-selection-reason'), reason=input?.value.trim();
  if(!reason){message('log-selection-error','Informe o motivo da seleção antes de continuar.');input?.focus();return null;}
  return {queryId:q.id,sourceEventId:q.selected_event.id,selectionReason:reason};
}
async function investigate(id,button){
  const request=++investigationRequest;investigationTrigger=button;
  button.disabled=true;button.textContent="Investigando…";message("log-error","");
  $("log-investigation").innerHTML='<p class="muted" role="status">Carregando análise…</p>';openInvestigation();
  try{
    if(id.startsWith("pg:")){const result=await api("/api/statements/investigate",{id});if(request===investigationRequest&&$("investigation-dialog").open)renderObservedInvestigation(result);return;}
    const result=await api("/api/logs/investigate",{id});if(request!==investigationRequest||!$("investigation-dialog").open)return;state.investigation=result;
    const q=result.record,a=result.analysis;
    $("log-investigation").innerHTML=`<article class="panel investigation"><p class="eyebrow">CONSULTA SELECIONADA DOS LOGS</p><h2>Análise da consulta</h2><p class="muted">${number(q.calls)} chamadas · ${duration(q.total_ms)} acumulados · ${duration(q.mean_ms)} em média. A investigação usa a variante com maior duração registrada.</p><pre class="selected-sql">${esc(shortSql(q.sql))}</pre><details><summary>Evidências do plano atual (${a.findings.length})</summary>${a.findings.map(f=>`<div class="compact-finding"><strong>${esc(f.title)}</strong><p>${esc(f.evidence)}</p></div>`).join("") || '<p class="muted">Nenhum padrão das regras atuais foi encontrado.</p>'}<button class="text-button" id="full-analysis">Abrir análise completa →</button></details><div class="recommendations">${result.recommendations.length ? result.recommendations.map((r,i)=>`<div class="recommendation"><span class="pill neutral">Proposta automática · regra ${esc(r.id)}</span><h3>${esc(r.title)}</h3><p>${esc(r.evidence)}</p><p class="footnote">${esc(r.condition)}</p><details><summary>Ver SQL proposto</summary><pre>${esc(r.alternative)}</pre></details><button class="button primary" data-use-proposal="${i}">Comparar e validar proposta →</button></div>`).join("") : '<div class="empty"><strong>Nenhuma reescrita automática disponível para este caso.</strong><p>As evidências do plano continuam disponíveis. Você pode elaborar uma alternativa e medi-la na tela de comparação.</p><button id="manual-proposal" class="text-button">Preparar uma alternativa →</button></div>'}</div></article>`;
    $("log-investigation").insertAdjacentHTML('afterbegin',logEvidenceHtml(q));
    $('log-selection-reason')?.addEventListener('input',()=>message('log-selection-error',''));
    $("full-analysis").addEventListener("click",()=>{const context=logSelection(q);if(!context)return;a.logContext=context;state.analysis=a;$("sql-input").value=q.sql;$("query-select").value="custom";$("query-description").textContent="Consulta selecionada dos logs.";renderAnalysis(a);showPage("logs");$("analysis-result").scrollIntoView({behavior:"smooth",block:"start"});});
    $("investigation-body").scrollTop=0;
  }catch(error){if(request===investigationRequest&&$("investigation-dialog").open)$("log-investigation").innerHTML=`<p class="notice error" role="alert">${esc(error.message)}</p>`;}
  finally{button.disabled=false;button.textContent="Investigar →";}
}
function proposalCard(r,index){
  const p=r.projection;
  const change=p?.cost_reduction_pct;
  const changes=[];
  if(p){
    for(const before of p.operations_before){const after=p.operations_after.find(item=>item.table===before.table);if(after&&after.operation!==before.operation)changes.push(`${before.table}: ${before.operation} → ${after.operation}`);}
    if(p.subplans_before!==p.subplans_after)changes.push(`Subplanos: ${p.subplans_before} → ${p.subplans_after}`);
  }
  return `<section class="proposal-card"><div class="proposal-heading"><h3>SQL sugerido</h3><button type="button" class="text-button" data-copy-proposal="${index}">Copiar SQL</button></div><p class="proposal-change">${esc(r.title)}</p><pre class="selected-sql formatted-sql"><code>${sqlMarkup(r.alternative)}</code></pre>${p?`<div class="projection-grid"><div><span>Custo estimado ${p.generic?"· plano genérico":""}</span><strong>${number(p.cost_before,2)} → ${number(p.cost_after,2)}</strong><small>${change==null?"Variação indisponível":`${number(Math.abs(change),2)}% ${change>=0?"menor":"maior"}`}</small></div><div><span>Tempo da alternativa</span><strong>Ainda não medido</strong><small>O custo do plano não representa milissegundos.</small></div></div>${changes.length?`<p class="proposal-operations">${esc([...new Set(changes)].join(" · "))}</p>`:""}`:`<p class="muted">${esc(r.projection_error||"Estimativa do plano indisponível.")}</p>`}<details class="proposal-evidence"><summary>Justificativa</summary><p>${esc(r.evidence)}</p><p>${esc(r.condition)}</p></details><div id="proposal-result-${index}" aria-live="polite"></div></section>`;
}
function investigationParameterValues(parameters){
  const values=Array(Math.max(...parameters)).fill(null),raw={};
  for(const n of parameters){
    const value=$(`investigation-param-${n}`).value.trim();
    if(!value)throw new Error(`Informe o valor do parâmetro $${n}.`);
    if(value==='*')throw new Error(`Parâmetro $${n}: * não significa “todos”. Informe um valor real; em filtros LIKE, o curinga é %.`);
    raw[String(n)]=value;
    if(value.startsWith('[')||value.startsWith('{'))throw new Error('Use valores simples, não listas ou objetos.');
    if(value.startsWith('"')){
      try{values[n-1]=JSON.parse(value);}catch{throw new Error(`Parâmetro $${n}: confira as aspas do texto.`);}
    }else if(value.startsWith("'")&&value.endsWith("'")&&value.length>=2){
      values[n-1]=value.slice(1,-1).replace(/''/g,"'");
    }else{
      try{values[n-1]=JSON.parse(value);}catch{values[n-1]=value;}
    }
    if((typeof values[n-1]==='object'&&values[n-1]!==null)||
       (typeof values[n-1]==='number'&&!Number.isFinite(values[n-1])))
      throw new Error(`Parâmetro $${n}: informe texto, número, true, false ou null.`);
  }
  return {values,raw};
}
async function measureProposal(index,button){
  if(state.investigationMeasuring)return;
  state.investigationMeasuring=true;
  const calls=Number($('investigation-calls').value);
  const controls=[...document.querySelectorAll("#log-investigation button, #log-investigation input, #log-investigation select")].map(el=>[el,el.disabled]);
  controls.forEach(([el])=>el.disabled=true);
  const investigation=state.investigation,r=investigation.recommendations[index],target=$(`proposal-result-${index}`);
  button.disabled=true;button.textContent="Medindo…";target.innerHTML=`<p class="muted" role="status">Executando ${calls} repetições por versão e conferindo os resultados…</p>`;
  try{
    const report=await api("/api/benchmark",{original:r.original,alternative:r.alternative,calls,query_id:investigation.record.id,rule:r.title});
    if(!target.isConnected||state.investigation!==investigation)return;
    const a=report.metrics.original,b=report.metrics.alternative;
    r.measured_report=report;
    const timeBox=target.closest('.proposal-card').querySelector('.projection-grid>div:nth-child(2)');
    if(timeBox){timeBox.querySelector('strong').textContent=duration(b.median_ms);timeBox.querySelector('small').textContent=`Mediana medida · ${a.calls} repetições`;}
    target.innerHTML=`<div class="proposal-measurement"><h4>${esc(report.verdict)}</h4><div class="measured-times"><div><span>Original</span><strong>${duration(a.median_ms)}</strong></div><span aria-hidden="true">→</span><div><span>Alternativa</span><strong>${duration(b.median_ms)}</strong></div></div><p>${report.reduction_pct==null?esc(report.verdict):`${number(Math.abs(report.reduction_pct),2)}% ${report.reduction_pct>=0?"de redução":"de aumento"} na mediana desta rodada.`}</p><p>${report.reduction_pct < 0 ? "A alternativa foi mais lenta nesta rodada. Mantenha a original enquanto não houver evidência de ganho." : "Este resultado vale para a rodada medida; não garante ganho em outros dados ou condições."}</p><small>${a.calls} repetições por versão, após aquecimento. Resultados conferidos por assinatura.</small><button type="button" class="text-button download-proposal-report">↓ Baixar medição em JSON</button></div>`;
    target.insertAdjacentHTML('beforeend',executionTimes(report));
    target.querySelector('.download-proposal-report').addEventListener('click',()=>download(`medicao-${report.id}.json`,report));
    await loadLogs();
  }catch(error){if(target.isConnected)target.innerHTML=`<p class="notice error" role="alert">${esc(error.message)}</p>`;await loadLogs();}
  finally{state.investigationMeasuring=false;controls.forEach(([el,disabled])=>{if(el.isConnected)el.disabled=disabled;});button.textContent="Medir desempenho";}
}
function investigationProposals(result) {
  const proposals = [...result.recommendations];
  const indexes = [];
  for (const p of result.analysis?.improvements?.proposals || []) {
    if (p.kind === 'index') { indexes.push(p); continue; }
    if (p.rule_id === 'date_year_range' && proposals.some(r => r.id === 'year-range')) continue;
    if (!proposals.some(r => r.alternative.trim() === p.sql.trim())) proposals.push({
      id:p.rule_id, title:p.title, evidence:p.explanation, condition:p.conditions,
      original:result.materialized_sql || result.record.sql, alternative:p.sql,
      requires_parameters:result.parameters?.length > 0 && !result.materialized_sql
    });
  }
  result.recommendations = proposals;
  return indexes;
}
function observedHistory(q) {
  const available = value => value !== null && value !== undefined && Number.isFinite(Number(value));
  const shown = value => available(value) ? duration(Number(value)) : 'Indisponível';
  const perCall = q.calls > 0 ? q.rows / q.calls : null;
  const delta = q.delta?.valid && q.delta.calls > 0 ? q.delta : null;
  return `<section class="observed-history" aria-label="Histórico registrado pelo PostgreSQL">
    <div class="observed-history-heading"><div><span class="eyebrow">DADOS DO POSTGRESQL</span><h3>Desempenho registrado</h3></div></div>
    <div class="observed-history-grid">
      ${metric('Tempo médio', shown(q.mean_exec_time), 'Por execução')}
      ${metric('Execuções', number(q.calls), 'Chamadas acumuladas')}
      ${metric('Tempo total', shown(q.total_exec_time), 'Soma no servidor')}
    </div>
    ${delta ? `<p class="observed-history-delta">Desde a última atualização: +${number(delta.calls)} ${delta.calls===1?'execução':'execuções'} e +${shown(delta.total_exec_time)}.</p>` : ''}
    <details><summary>Ver mais métricas e a origem dos dados</summary>
      <div class="observed-history-extra">
        ${metric('Menor tempo', shown(q.min_exec_time), 'Desde a coleta de mínimo/máximo')}
        ${metric('Maior tempo', shown(q.max_exec_time), 'Desde a coleta de mínimo/máximo')}
        ${metric('Linhas retornadas', available(q.rows) ? number(q.rows) : 'Indisponível', perCall !== null ? `${number(perCall,1)} por execução, em média` : 'Total registrado')}
      </div>
      <p>Banco ${esc(q.database_name || 'indisponível')} · usuário ${esc(q.user_name || 'indisponível')} · Query ID ${esc(q.query_id || 'indisponível')}.</p>
      <p>Período das estatísticas desde ${q.stats_since ? esc(dateLabel(q.stats_since)) : 'data indisponível'}. ${q.minmax_stats_since ? `Mínimo e máximo desde ${esc(dateLabel(q.minmax_stats_since))}.` : ''}</p>
      <p>${q.last_activity ? `Mudança detectada na atualização de ${esc(dateLabel(q.last_activity))}; esse não é necessariamente o horário exato da execução.` : 'Última atividade não identificada.'}</p>
      <p>${available(q.stddev_exec_time) ? `Variação dos tempos (desvio padrão): ${shown(q.stddev_exec_time)}. ` : ''}Leituras de blocos compartilhados: ${available(q.shared_blks_read) ? number(q.shared_blks_read) : 'indisponível'}; acertos no cache: ${available(q.shared_blks_hit) ? number(q.shared_blks_hit) : 'indisponível'}. Blocos lidos não equivalem necessariamente a leituras físicas do disco.</p>
      <p>Fonte: pg_stat_statements. O PostgreSQL agrupa consultas com a mesma estrutura, inclusive com valores diferentes. Esses números são acumulados e podem ser reiniciados pelo servidor. Esta tela não executa a consulta.</p>
    </details>
  </section>`;
}
function renderObservedInvestigation(result, optimized = false){
  state.investigation=result;
  const q=result.record;
  const formattedSql=result.formatted_sql||result.materialized_sql||q.sql;
  const indexes=investigationProposals(result);
  const parameters=result.parameters || [];
  const ready=optimized && result.recommendations.some(r=>!r.requires_parameters);
  $("log-investigation").innerHTML=`
    <article class="panel investigation">
      ${observedHistory(q)}
      <section class="investigation-query"><div class="sql-toolbar"><div><span class="eyebrow">SQL REGISTRADO</span><h3>Consulta investigada</h3></div><button id="copy-investigation-sql" class="text-button" type="button">Copiar SQL</button></div><pre class="selected-sql formatted-sql"><code>${sqlMarkup(formattedSql)}</code></pre></section>
      <section class="investigation-evidence"><h3>Evidências e sugestões</h3>${result.analysis ? `<p class="muted">${result.analysis.plan_kind === 'generic' ? 'Análise do plano genérico, sem os valores originais dos parâmetros.' : 'Análise do plano estimado para a consulta informada.'} Os alertas indicam pontos para investigar.</p>${result.analysis.findings.length ? result.analysis.findings.map((finding,index)=>`<div class="finding"><span class="finding-number">${String(index+1).padStart(2,'0')}</span><div><h3>${esc(finding.title)} ${pill(finding.severity,finding.severity)}</h3><p><span class="finding-label">Evidência.</span> ${esc(finding.evidence)}</p><p><span class="finding-label">O que investigar.</span> ${esc(finding.recommendation)}</p></div></div>`).join('') : '<p class="muted">Nenhum padrão de alerta foi identificado pelas regras disponíveis.</p>'}` : `<p class="muted">${esc(result.plan_error || 'O plano estimado está indisponível para esta consulta.')}</p>`}</section>
      ${parameters.length ? `<section class="investigation-parameters"><div><span class="eyebrow">PARÂMETROS</span><h3>Valores para testar</h3><p>O histórico não guarda os valores originais. Digite um valor real, como 42, 2026-01-01 ou cancelado. Use null para nulo; * não significa todos.</p></div><div class="parameter-fields">${parameters.map(n=>`<div><label for="investigation-param-${n}">Parâmetro $${n}</label><input id="investigation-param-${n}" data-investigation-param="${n}" type="text" placeholder="Digite um valor" value="${esc(result.input_parameters?.[String(n)] ?? '')}"></div>`).join('')}</div></section>` : ''}
      <section class="investigation-workflow"><span class="eyebrow">PRÓXIMOS PASSOS</span><div class="investigation-actions"><button id="optimize-investigation" type="button" class="button primary">Propor otimização</button><label class="investigation-calls-label" for="investigation-calls">Repetições por versão<select id="investigation-calls">${[3,10,30,50].map(n=>`<option value="${n}" ${state.measurementCalls===n?'selected':''}>${n}</option>`).join('')}</select></label><button id="measure-investigation" type="button" class="button secondary" ${ready?'':'disabled'}>Medir desempenho</button></div>
      <p id="investigation-action-status" role="status" class="muted">${optimized ? ready?(result.recommendations.length>1?'O botão acima mede a primeira alternativa disponível. Para medir outra, use o botão junto à sugestão.':'A alternativa está pronta para medir.'):'Nenhuma alternativa executável encontrada; uma sugestão de índice precisa de um teste próprio.':'Comece pela proposta. A medição só fica disponível quando houver uma alternativa executável.'}</p>
      <p class="footnote">A medição confere os resultados e executa o número escolhido de repetições para cada versão, após aquecimento.</p></section>
      <div id="investigation-action-error" class="notice error" role="alert" hidden></div>
      <div id="investigation-results">${optimized ? `${result.recommendations.length ? '' : '<div class="notice info"><strong>Nenhuma reescrita recomendada pelas regras disponíveis.</strong> Isso não significa que a consulta tenha desempenho ótimo.</div>'}${result.recommendations.map((r,i)=>proposalCard(r,i)+(result.recommendations.length>1&&!r.requires_parameters?`<button type="button" class="button secondary" data-measure-proposal="${i}">Medir esta alternativa</button>`:'')).join('')}${indexes.map(p=>`<section class="proposal-card"><h3>${esc(p.title)}</h3><p>${esc(p.explanation)}</p><pre>${esc(p.sql)}</pre><p class="footnote">${esc(p.conditions)}</p><strong>Índice sugerido, ainda não criado ou medido.</strong></section>`).join('')}` : ''}</div>
      <button id="download-observed" class="text-button" type="button">↓ Baixar análise em JSON</button>
    </article>`;
  $("copy-investigation-sql").addEventListener("click",async event=>{
    try{await navigator.clipboard.writeText(formattedSql);event.currentTarget.textContent="Copiado";}
    catch{event.currentTarget.textContent="Não foi possível copiar";}
  });
  $("download-observed").addEventListener("click",()=>download(`analise-postgresql-${q.query_id}.json`,result));
  $('investigation-calls').addEventListener('change',event=>{state.measurementCalls=Number(event.target.value);});
  $("optimize-investigation").addEventListener('click', async event => {
    const button=event.currentTarget;button.disabled=true;button.textContent='Procurando alternativas…';
    message('investigation-action-error','');
    const request=investigationRequest;
    try {
      let updated;
      if(parameters.length){
        const {values,raw}=investigationParameterValues(parameters);
        updated=await api('/api/statements/investigate',{id:q.id,parameters:values,record_outcome:true});
        updated.input_parameters=raw;
      }else updated=await api('/api/statements/investigate',{id:q.id,record_outcome:true});
      if(request===investigationRequest && $('investigation-dialog').open && state.investigation===result)renderObservedInvestigation(updated,true);
      await loadLogs();
    }catch(error){if(request===investigationRequest)message('investigation-action-error',error.message);}
    finally{button.disabled=false;button.textContent='Propor otimização';}
  });
  $('measure-investigation').addEventListener('click', event => {
    const index=result.recommendations.findIndex(r=>!r.requires_parameters);
    measureProposal(index,event.currentTarget);
  });
  document.querySelectorAll('[data-investigation-param]').forEach(input=>input.addEventListener('input',()=>{
    $('measure-investigation').disabled=true;
    $('investigation-results').replaceChildren();
    message('investigation-action-error','');
    $('investigation-action-status').textContent='Os valores foram alterados. Clique novamente em Propor otimização antes de medir.';
  }));
  $('investigation-body').scrollTop=0;
}
function useProposal(index){
  const item=state.investigation;
  const context=item.record.selected_event?logSelection(item.record):null;
  if(item.record.selected_event&&!context)return;
  const r=index===null?{original:item.materialized_sql||item.record.sql,alternative:item.materialized_sql||item.record.sql,condition:"Edite a alternativa e verifique se preserva os resultados.",evidence:"Consulta selecionada dos logs."}:item.recommendations[index];
  invalidateComparison();state.queryId=item.record.id;
  state.sourceEventId=context?.sourceEventId||null;state.selectionReason=context?.selectionReason||null;
  $("original-sql").value=r.original;$("alternative-sql").value=r.alternative;
  $("comparison-description").textContent=r.evidence;$("comparison-condition").textContent=r.requires_parameters ? "Para medir, substitua os parâmetros pelos mesmos valores nos dois SQLs." : r.condition;
  showPage("compare");
}
function executionTimes(report){
  const a=report.metrics.original,b=report.metrics.alternative;
  const rows=[['Mediana','median_ms'],['Média','mean_ms'],['Mínimo','min_ms'],['Máximo','max_ms']];
  return `<section class="panel"><h3>Tempos de execução</h3><p class="muted">Comparação das ${number(a.calls)} repetições medidas por versão, após aquecimento.</p><table class="comparison-table"><thead><tr><th>Métrica</th><th>Original</th><th>Alternativa</th></tr></thead><tbody>${rows.map(([label,key])=>`<tr><td>${label}</td><td>${duration(a[key])}</td><td>${duration(b[key])}</td></tr>`).join('')}</tbody></table></section>`;
}
function experimentOriginHtml(report){
  const o=report.origin;
  if(!o)return '<p class="footnote">Relatório anterior à rastreabilidade de origem; sem vínculo detalhado registrado.</p>';
  if(o.kind!=='execution_log')return `<p class="footnote">Origem: ${o.kind==='pg_stat_statements'?'estatísticas agregadas do PostgreSQL':'consulta manual ou exemplo'}. ${esc(o.note||'')}</p>`;
  return `<section class="panel"><h3>Do log ao experimento</h3><p><strong>Arquivo:</strong> ${esc(o.batch.source)}<br><strong>Evento:</strong> ${esc(o.event.id)}<br><strong>Registro:</strong> ${esc(o.event.occurred_at||'Horário não informado')} · ${duration(o.event.duration_ms)}<br><strong>Motivo da seleção:</strong> ${esc(o.selection_reason)}</p><p>${o.original_matches_event?'A original testada corresponde ao SQL do evento registrado.':'A original foi editada em relação ao evento; a origem é uma referência, não reprodução exata.'}</p><details><summary>Evidência de origem</summary><p>SHA-256: <code>${esc(o.content_sha256)}</code></p><pre>${esc(o.event.sql)}</pre><p>${esc(o.sample_policy)}</p></details></section>`;
}
function renderBenchmark(report){
  state.report=report;const a=report.metrics.original,b=report.metrics.alternative;
  const row=(title,x,y)=>`<tr><td>${title}</td><td>${x}</td><td>${y}</td></tr>`;
  $("benchmark-result").innerHTML=`<article class="panel benchmark-report"><p class="eyebrow">RESULTADO MEDIDO · ${esc(dateLabel(report.created_at))}</p><h2>${esc(report.verdict)}</h2><p class="benchmark-delta">${report.reduction_pct===null?"Sem base para variação":`${number(Math.abs(report.reduction_pct),2)}% ${report.reduction_pct>=0?"de redução":"de aumento"}`}<span>na mediana do tempo de execução do servidor</span></p><p class="muted">${a.calls} repetições medidas por versão, após um aquecimento. Assinaturas dos resultados conferidas: ${number(a.rows)} linhas em cada versão.</p><h3>Tempos de execução</h3><table class="comparison-table"><thead><tr><th>Métrica</th><th>Original</th><th>Alternativa</th></tr></thead><tbody>${row("Mediana",duration(a.median_ms),duration(b.median_ms))}${row("Média",duration(a.mean_ms),duration(b.mean_ms))}${row("Mínimo",duration(a.min_ms),duration(b.min_ms))}${row("Máximo",duration(a.max_ms),duration(b.max_ms))}${row("Operação principal",esc(a.root_node),esc(b.root_node))}</tbody></table><details><summary>Método e evidências</summary><p class="footnote">${esc(report.method)}</p><p class="footnote">${esc(report.result_check)}</p><pre>${esc(report.original_sql)}\n\n${esc(report.alternative_sql)}</pre></details><button class="text-button" id="download-benchmark">↓ Baixar relatório completo em JSON</button></article>`;
  $("download-benchmark").addEventListener("click",()=>download(`experimento-${report.id}.json`,report));
}
$("run-benchmark").addEventListener("click",async()=>{
  const button=$("run-benchmark"),original=$("original-sql").value,alternative=$("alternative-sql").value;
  button.disabled=true;button.textContent="Executando o teste…";message("benchmark-error","");$("benchmark-result").replaceChildren();
  message("benchmark-status","Executando as duas versões no banco de teste. Conferindo os resultados e medindo os tempos…");
  try{
    const report=await api("/api/benchmark",{original,alternative,calls:Number($("benchmark-calls").value),query_id:state.queryId,selection_reason:state.selectionReason,source_event_id:state.sourceEventId});
    if($("original-sql").value===original && $("alternative-sql").value===alternative){renderBenchmark(report);$("benchmark-result").scrollIntoView({behavior:"smooth",block:"start"});}
    await loadLogs();
  }catch(error){message("benchmark-error",error.message);}
  finally{button.disabled=false;button.textContent="Executar e medir";message("benchmark-status","");}
});
document.addEventListener("click",event=>{
  const investigation=event.target.closest("[data-investigate]");if(investigation)investigate(investigation.dataset.investigate,investigation);
  const proposal=event.target.closest("[data-use-proposal]");if(proposal)useProposal(Number(proposal.dataset.useProposal));
  if(event.target.closest("#manual-proposal"))useProposal(null);
  const saved=event.target.closest("[data-report]");if(saved){const report=state.reports[Number(saved.dataset.report)];invalidateComparison();$("original-sql").value=report.original_sql;$("alternative-sql").value=report.alternative_sql;state.sourceEventId=report.origin?.event?.id||null;state.selectionReason=report.origin?.selection_reason||null;state.queryId=state.sourceEventId||report.query_id?.startsWith('pg:')?report.query_id:null;$("comparison-description").textContent="Experimento salvo; resultado da rodada indicada abaixo.";$("comparison-condition").textContent="As assinaturas foram comparadas no momento do teste.";renderBenchmark(report);showPage("compare");$("benchmark-result").scrollIntoView({behavior:"smooth"});}
});
document.addEventListener("click",async event=>{
  const measure=event.target.closest("[data-measure-proposal]");if(measure)measureProposal(Number(measure.dataset.measureProposal),measure);
  const copy=event.target.closest(".proposal-card [data-copy-proposal]");if(copy){try{await navigator.clipboard.writeText(state.investigation.recommendations[Number(copy.dataset.copyProposal)].alternative);copy.textContent="Copiado";}catch{copy.textContent="Não foi possível copiar";}}
});
start();
