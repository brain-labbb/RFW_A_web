// Recorded physics simulation demos: muted looping previews, click to enlarge with sound.
const base = import.meta.env.BASE_URL;
const format = document.createElement('video').canPlayType('video/mp4; codecs="avc1.42E01E"') ? 'mp4' : 'webm';
const demos = [
  ['ball_transfer_load_wave-3', 'Ball transfer · load wave'],
  ['foosball_physical_goal-9', 'Foosball · physical goal'],
  ['gyroscope_driven', 'Gyroscope · driven precession'],
  ['hydraulic_can_crush-4', 'Hydraulic can crush'],
  ['petal_20260825_142252', 'Petal grasp · I'],
  ['petal_20260825_142319', 'Petal grasp · II'],
  ['robot_soft_grasp_materials_contact_fem_candidate', 'Soft grasp · contact FEM'],
  ['seed_spreader_rpm_comparison-4', 'Seed spreader · RPM comparison'],
  ['sports_car_scissor_jack', 'Sports car · scissor jack'],
];
const grid = document.querySelector('#simdemo-grid');
const dialog = document.querySelector('#simdemo-dialog');
const enlarged = dialog.querySelector('video');
const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;
const videos = [], visible = new Set();
function sync(video) {
  if (reduced || document.hidden || !visible.has(video) || document.querySelector('dialog[open]')) {
    video.pause();
    return;
  }
  if (!video.hasAttribute('src')) video.src = video.dataset.src;
  video.play().catch(() => {});
}
const observer = new IntersectionObserver(entries => {
  for (const entry of entries) {
    if (entry.isIntersecting) visible.add(entry.target);
    else visible.delete(entry.target);
    sync(entry.target);
  }
}, {threshold: .15});
for (const [file, label] of demos) {
  const src = `${base}media/simdemos/${file}.${format}`;
  const figure = document.createElement('figure');
  const button = document.createElement('button');
  button.className = 'simdemo-open';
  button.setAttribute('aria-label', `Enlarge demo: ${label}`);
  const video = document.createElement('video');
  video.muted = video.defaultMuted = true;
  video.loop = video.playsInline = true;
  video.preload = reduced ? 'metadata' : 'none';
  video.poster = `${base}media/simdemos/${file}.webp`;
  video.dataset.src = src;
  video.setAttribute('aria-label', label);
  const hint = document.createElement('span');
  hint.className = 'simdemo-hint';
  hint.textContent = 'Enlarge ↗';
  button.append(video, hint);
  button.addEventListener('click', () => {
    videos.forEach(v => v.pause());
    dialog.querySelector('#simdemo-dialog-title').textContent = label;
    enlarged.src = src;
    enlarged.setAttribute('aria-label', label);
    dialog.showModal();
    enlarged.play().catch(() => {});
  });
  const caption = document.createElement('figcaption');
  caption.textContent = label;
  figure.append(button, caption);
  grid.append(figure);
  videos.push(video);
  observer.observe(video);
}
dialog.addEventListener('close', () => {
  enlarged.pause();
  enlarged.removeAttribute('src');
  enlarged.load();
  videos.forEach(sync);
});
document.addEventListener('visibilitychange', () => {
  if (document.hidden) enlarged.pause();
  videos.forEach(sync);
});
