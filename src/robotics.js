// Recorded task demonstrations: five simulation assets and one real target per task.
const section = document.querySelector('#sim2real');
const mediaUrl = path => import.meta.env.BASE_URL + path;
const format = document.createElement('video').canPlayType('video/mp4; codecs="avc1.42E01E"') ? 'mp4' : 'webm';
const sourceUrl = clip => mediaUrl(clip.src.replace(/\.mp4$/, `.${format}`));
const reduced = matchMedia('(prefers-reduced-motion: reduce)');
const picker = section.querySelector('#robotics-picker');
const grid = section.querySelector('#robotics-grid');
const play = section.querySelector('#robotics-play');
const replay = section.querySelector('#robotics-replay');
const dialog = document.querySelector('#robotics-dialog');
const enlarged = dialog.querySelector('video');
let playing = !reduced.matches && !navigator.connection?.saveData;
let videos = [], active = null;
const visible = new Set();
function updateButton() {
  play.textContent = playing ? 'Pause videos' : 'Play videos';
  play.setAttribute('aria-label', `${playing ? 'Pause' : 'Play'} task videos`);
}
function sync(video) {
  if (!playing || document.hidden || !visible.has(video) || document.querySelector('dialog[open]')) {
    video.pause();
    return;
  }
  if (!video.hasAttribute('src')) video.src = video.dataset.src;
  video.play().catch(error => {
    if (error.name === 'NotAllowedError' && video.isConnected) {
      playing = false;
      videos.forEach(v => v.pause());
      updateButton();
    }
  });
}
const observer = new IntersectionObserver(entries => {
  for (const entry of entries) {
    if (entry.isIntersecting) visible.add(entry.target);
    else visible.delete(entry.target);
    sync(entry.target);
  }
}, {threshold: .15});
function enlarge(clip, task) {
  videos.forEach(v => v.pause());
  document.querySelector('#robotics-dialog-title').textContent = `${task.label} · ${clip.label} · ${clip.speed}×`;
  enlarged.poster = mediaUrl(clip.poster);
  enlarged.src = sourceUrl(clip);
  enlarged.setAttribute('aria-label', `${task.label}: ${clip.label}`);
  dialog.showModal();
  enlarged.play().catch(() => {});
}
function select(task) {
  if (active === task.id) return;
  active = task.id;
  observer.disconnect();
  visible.clear();
  videos.forEach(video => { video.pause(); video.removeAttribute('src'); video.load(); });
  videos = [];
  grid.replaceChildren();
  picker.querySelectorAll('button').forEach(button => button.setAttribute('aria-pressed', String(button.dataset.task === task.id)));
  section.querySelector('#robotics-selection').textContent = task.label;
  section.querySelector('#task-description').textContent = task.description;
  const realSpeed = task.videos.find(v => v.domain === 'real').speed;
  section.querySelector('#robotics-speed').textContent = `Playback: simulation 4× · real world ${realSpeed}×`;
  for (const clip of task.videos) {
    const figure = document.createElement('figure');
    if (clip.domain === 'real') figure.className = 'robotics-real';
    const caption = document.createElement('figcaption');
    const label = document.createElement('span'); label.textContent = clip.label;
    const speed = document.createElement('span'); speed.className = 'robotics-speed'; speed.textContent = `${clip.speed}×`;
    caption.append(label, speed);
    const button = document.createElement('button');
    button.className = 'robotics-enlarge';
    button.setAttribute('aria-label', `Enlarge ${task.label}: ${clip.label}`);
    const video = document.createElement('video');
    video.muted = video.defaultMuted = true;
    video.loop = video.playsInline = true;
    video.preload = 'none';
    video.poster = mediaUrl(clip.poster);
    video.dataset.src = sourceUrl(clip);
    video.dataset.clip = clip.id;
    video.setAttribute('aria-label', `${task.label}: ${clip.label}, ${clip.speed} times speed`);
    video.addEventListener('error', () => {
      if (!video.hasAttribute('src')) return;
      button.classList.add('has-error');
      hint.textContent = 'Open video ↗';
    });
    const hint = document.createElement('span'); hint.className = 'robotics-enlarge-hint'; hint.textContent = 'Enlarge ↗';
    button.append(video, hint);
    button.addEventListener('click', () => enlarge(clip, task));
    figure.append(caption, button);
    grid.append(figure);
    videos.push(video);
    observer.observe(video);
  }
  updateButton();
  window.__roboticsReady = task.id;
}
play.addEventListener('click', () => { playing = !playing; updateButton(); videos.forEach(sync); });
replay.addEventListener('click', () => {
  playing = true;
  videos.forEach(video => { if (video.readyState > 0) video.currentTime = 0; });
  updateButton(); videos.forEach(sync);
});
dialog.addEventListener('close', () => {
  enlarged.pause(); enlarged.removeAttribute('src'); enlarged.load(); videos.forEach(sync);
});
document.addEventListener('visibilitychange', () => {
  if (document.hidden) enlarged.pause();
  videos.forEach(sync);
});
for (const modal of document.querySelectorAll('dialog')) {
  new MutationObserver(() => videos.forEach(sync)).observe(modal, {attributes: true, attributeFilter: ['open']});
}
reduced.addEventListener('change', () => {
  if (reduced.matches) { playing = false; updateButton(); videos.forEach(sync); }
});
fetch(mediaUrl('data/robotics.json')).then(response => {
  if (!response.ok) throw Error('Recordings unavailable');
  return response.json();
}).then(data => {
  for (const task of data.tasks) {
    const button = document.createElement('button');
    button.type = 'button'; button.dataset.task = task.id; button.setAttribute('aria-pressed', 'false');
    const image = document.createElement('img');
    image.src = mediaUrl(task.videos.find(v => v.domain === 'real').poster);
    image.alt = ''; image.loading = 'lazy'; image.width = 64; image.height = 40;
    const label = document.createElement('span'); label.textContent = task.label;
    button.append(image, label); button.addEventListener('click', () => select(task)); picker.append(button);
  }
  const header = document.createElement('tr');
  for (const text of ['Training assets', ...data.tasks.map(t => t.label), 'Mean']) {
    const th = document.createElement('th'); th.scope = 'col'; th.textContent = text; header.append(th);
  }
  section.querySelector('#robotics-results thead').append(header);
  for (const result of data.results) {
    const row = document.createElement('tr');
    if (result.edits === 9) row.className = 'ours';
    const th = document.createElement('th'); th.scope = 'row'; th.textContent = result.setting; row.append(th);
    for (const text of [...result.successes.map(n => `${n}/10`), `${result.average}%`]) {
      const td = document.createElement('td'); td.textContent = text; row.append(td);
    }
    section.querySelector('#robotics-results tbody').append(row);
  }
  select(data.tasks[0]);
}).catch(() => {
  grid.textContent = 'Recordings could not load. Please reload the page.';
  play.disabled = replay.disabled = true;
});
