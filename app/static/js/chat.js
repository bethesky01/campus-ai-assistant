const form = document.querySelector('#chat-form');
const input = document.querySelector('#question');
const conversation = document.querySelector('#conversation');
const welcome = document.querySelector('#welcome');

function addMessage(role, content, sources = []) {
  const item = document.createElement('article');
  item.className = `message ${role}`;
  const label = document.createElement('span');
  label.className = 'message-label';
  label.textContent = role === 'user' ? 'You' : 'Campus AI';
  const body = document.createElement('div');
  body.textContent = content;
  item.append(label, body);
  if (sources.length) {
    const sourceArea = document.createElement('div');
    sourceArea.className = 'source-grid';
    sources.forEach(source => {
      const card = document.createElement('div');
      card.className = 'source-card';
      card.textContent = `▤ ${source.document_title} · ${source.page ? `Page ${source.page}` : 'Page unavailable'}`;
      sourceArea.append(card);
    });
    item.append(sourceArea);
  }
  conversation.append(item);
  item.scrollIntoView({behavior: 'smooth', block: 'end'});
  return item;
}

function addMetadata(item, metadata) {
  const badge = document.createElement('span');
  badge.className = `tool-badge ${metadata.grounded ? 'grounded' : ''}`;
  badge.textContent = `Tool Used: ${metadata.tool_used}`;
  item.insertBefore(badge, item.querySelector('div'));
  const safety = document.createElement('span');
  safety.className = `safety-badge ${metadata.safety_status === 'passed' ? 'passed' : 'attention'}`;
  safety.textContent = `Grounded: ${metadata.grounded ? 'Yes' : 'No'} · Safety: ${metadata.safety_status.replaceAll('_', ' ')}`;
  item.insertBefore(safety, item.querySelector('div'));
  if (metadata.sources?.length) {
    const sourceArea = document.createElement('div'); sourceArea.className = 'source-grid';
    metadata.sources.forEach(source => { const card = document.createElement('div'); card.className = 'source-card'; card.textContent = `▤ ${source.document_title} · ${source.page ? `Page ${source.page}` : 'Page unavailable'}`; sourceArea.append(card); });
    item.append(sourceArea);
  }
}

async function ask(question) {
  welcome.hidden = true;
  addMessage('user', question);
  const loading = addMessage('assistant loading', 'Routing your question…');
  form.classList.add('busy');
  try {
    let sessionId = localStorage.getItem('campus_session_id');
    const response = await fetch('/chat/stream', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({question, session_id: sessionId})});
    if (!response.ok || !response.body) throw new Error('The request failed.');
    loading.remove(); const item = addMessage('assistant', ''); const body = item.querySelector('div');
    const reader = response.body.getReader(); const decoder = new TextDecoder(); let buffer = '';
    while (true) {
      const {value, done} = await reader.read(); if (done) break; buffer += decoder.decode(value, {stream: true});
      const blocks = buffer.split('\n\n'); buffer = blocks.pop();
      for (const block of blocks) {
        const dataLine = block.split('\n').find(line => line.startsWith('data: ')); if (!dataLine) continue;
        const data = JSON.parse(dataLine.slice(6));
        if (data.session_id) { sessionId = data.session_id; localStorage.setItem('campus_session_id', sessionId); }
        if (data.event === 'token') body.textContent += data.content;
        if (data.event === 'metadata') addMetadata(item, data);
        if (data.event === 'error') throw new Error(data.message);
      }
    }
  } catch (error) {
    loading.remove();
    addMessage('assistant error', error.message);
  } finally {
    form.classList.remove('busy'); input.focus();
  }
}

form.addEventListener('submit', event => { event.preventDefault(); const value = input.value.trim(); if (value) { input.value = ''; ask(value); } });
document.querySelectorAll('.suggestions button').forEach(button => button.addEventListener('click', () => ask(button.textContent)));
