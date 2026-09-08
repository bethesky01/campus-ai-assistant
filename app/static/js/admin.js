const uploadForm = document.querySelector('#upload-form');
const uploadStatus = document.querySelector('#upload-status');
const fileInput = uploadForm.querySelector('input[type=file]');
const progressPanel = document.querySelector('#ingestion-progress');
const progressBar = document.querySelector('#progress-bar');
const progressTrack = progressPanel.querySelector('.progress-track');
const progressPercent = document.querySelector('#progress-percent');
const progressTitle = document.querySelector('#progress-title');
const progressDetail = document.querySelector('#progress-detail');
const pipelineSteps = [...document.querySelectorAll('#pipeline-steps li')];
const stageOrder = ['validating', 'storing', 'extracting', 'safety', 'chunking', 'preparing', 'embedding', 'indexing', 'complete'];
const stepStages = {
  validate: ['validating', 'storing'],
  split: ['extracting', 'safety', 'chunking', 'preparing'],
  embed: ['embedding'],
  store: ['indexing'],
  ready: ['complete'],
};

fileInput.addEventListener('change', () => {
  document.querySelector('#file-name').textContent = fileInput.files[0]?.name || 'Choose a PDF';
});

function showStatus(message, type = '') {
  uploadStatus.hidden = false;
  uploadStatus.className = `notice ${type}`;
  uploadStatus.textContent = message;
}

function updateProgress(event) {
  const percent = Math.max(0, Math.min(100, Number(event.percent) || 0));
  progressBar.style.width = `${percent}%`;
  progressPercent.value = `${percent}%`;
  progressTrack.setAttribute('aria-valuenow', String(percent));
  progressDetail.textContent = event.message;
  const current = stageOrder.indexOf(event.stage);
  pipelineSteps.forEach(step => {
    const stages = stepStages[step.dataset.step];
    const start = stageOrder.indexOf(stages[0]);
    const end = stageOrder.indexOf(stages[stages.length - 1]);
    step.classList.toggle('done', event.stage === 'complete' || current > end);
    step.classList.toggle('active', current >= start && current <= end);
  });
  if (event.stage === 'complete') progressPanel.classList.add('complete');
}

function resetProgress() {
  progressPanel.hidden = false;
  progressPanel.classList.remove('complete', 'failed');
  pipelineSteps.forEach(step => step.classList.remove('active', 'done'));
  updateProgress({stage: 'validating', percent: 0, message: 'Starting the local ingestion pipeline'});
}

async function readProgressStream(response, onEvent) {
  if (!response.body) throw new Error('This browser cannot read upload progress streams.');
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  while (true) {
    const {value, done} = await reader.read();
    buffer += decoder.decode(value || new Uint8Array(), {stream: !done});
    const frames = buffer.split('\n\n');
    buffer = frames.pop() || '';
    for (const frame of frames) {
      const line = frame.split('\n').find(item => item.startsWith('data: '));
      if (line) onEvent(JSON.parse(line.slice(6)));
    }
    if (done) break;
  }
}

uploadForm.addEventListener('submit', async event => {
  event.preventDefault();
  const button = uploadForm.querySelector('button');
  button.disabled = true;
  showStatus('Uploading PDF and starting the local indexing pipeline...', 'working');
  resetProgress();
  try {
    const response = await fetch('/admin/upload/progress', {method: 'POST', body: new FormData(uploadForm)});
    if (!response.ok) throw new Error('Upload could not be started.');
    let data = null;
    let streamError = null;
    await readProgressStream(response, eventData => {
      if (eventData.type === 'progress') updateProgress(eventData);
      if (eventData.type === 'result') {
        data = eventData.document;
        updateProgress({stage: 'complete', percent: 100, message: `Knowledge base ready with ${data.chunk_count} chunks`});
      }
      if (eventData.type === 'error') streamError = eventData.message;
    });
    if (streamError) throw new Error(streamError);
    if (!data) throw new Error('Indexing ended without a result.');
    showStatus(`Indexed successfully - ${data.page_count} pages processed, ${data.chunk_count} chunks created.`, 'success');
    setTimeout(() => location.reload(), 1200);
  } catch (error) {
    progressPanel.classList.add('failed');
    progressTitle.textContent = 'Indexing failed';
    progressDetail.textContent = error.message;
    showStatus(error.message, 'error');
    button.disabled = false;
  }
});

document.querySelector('tbody').addEventListener('click', async event => {
  const button = event.target.closest('button[data-action]');
  if (!button) return;
  const row = button.closest('tr');
  const id = row.dataset.id;
  const action = button.dataset.action;
  if (action === 'delete' && !confirm('Delete this PDF and all of its indexed chunks?')) return;
  button.disabled = true;
  button.textContent = action === 'delete' ? 'Deleting...' : 'Indexing...';
  try {
    const response = await fetch(`/admin/documents/${id}${action === 'reindex' ? '/reindex' : ''}`, {
      method: action === 'reindex' ? 'POST' : 'DELETE',
    });
    if (!response.ok) {
      const data = await response.json();
      throw new Error(data.detail || 'Operation failed.');
    }
    location.reload();
  } catch (error) {
    alert(error.message);
    button.disabled = false;
    button.textContent = action === 'delete' ? 'Delete' : 'Re-index';
  }
});
