function setStage(stage){
  state.stages[stage]=true;
  const box=document.getElementById('stages'); box.innerHTML='';
  STAGES.forEach(s=>{
    const el=document.createElement('div');
    let cls='stage';
    if(state.stages[s] && s!==stage && s!=='complete') cls+=' done';
    if(s===stage) cls+=' active';
    el.className=cls; el.textContent=STAGE_LABEL[s];
    box.appendChild(el);
  });

  const coreCenter = document.getElementById('aiCoreCenter');
  const coreStatus = document.getElementById('aiCoreStatus');
  const execAgents = document.getElementById('execAgents');

  if(stage === 'complete'){
    if(coreCenter) coreCenter.classList.remove('thinking');
    if(coreStatus) coreStatus.textContent = 'Online · Ready';
    if(execAgents) execAgents.innerHTML = '';
  } else {
    if(coreCenter) coreCenter.classList.add('thinking');
    if(coreStatus) coreStatus.textContent = STAGE_LABEL[stage] || 'Processing...';
  }
}
