/* Shared public content: values are validated by the admin service on publish. */
const publicProfile = window.PORTFOLIO_CONTENT?.profile;
const safeText = value => String(value ?? '').replace(/[&<>"']/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));

function applyProfile() {
  const p = publicProfile;
  if (!p) return;
  const name = document.getElementById('hero-name');
  const parts = p.name.trim().split(/\s+/);
  const rest = document.createElement('span');
  rest.textContent = parts.slice(1).join(' ') || parts[0];
  name.replaceChildren(document.createTextNode(parts.length > 1 ? parts[0] : ''), document.createElement('br'), rest);
  const small = document.createElement('span');
  small.className = 'brand-small';
  small.textContent = p.name.toUpperCase();
  document.querySelector('.brand>span:last-child').replaceChildren(document.createTextNode(p.brand), small);
  document.querySelector('.brand-mark').textContent = p.brandMark;
  const image = document.querySelector('.portrait-frame img');
  image.src = p.photo;
  image.alt = p.photoAlt;
  const email = document.querySelector('.contact-email');
  email.textContent = p.email;
  email.href = 'mailto:' + p.email;
  document.querySelectorAll('a[href*="linkedin.com"]').forEach(a => a.href = p.linkedin);
  document.querySelectorAll('a[href="https://github.com/ThalysonPin"]').forEach(a => a.href = p.github);
  document.querySelector('.contact-social a:last-child').href = p.whatsapp;
  document.querySelector('.footer>span').textContent = p.footer;
  document.querySelectorAll('.metrics strong').forEach((node, i) => node.textContent = p.metrics[i] ?? '');
}

function applyThemeColors() {
  const themes = window.PORTFOLIO_CONTENT?.theme;
  if (!themes) return;
  let savedTheme;
  try { savedTheme = localStorage.getItem('tedsp-theme'); } catch {}
  if (!window.portfolioThemeInitialized && !savedTheme) document.documentElement.dataset.theme = themes.default;
  window.portfolioThemeInitialized = true;
  const palette = themes[document.documentElement.dataset.theme === 'dark' ? 'dark' : 'light'];
  for (const key of new Set([...Object.keys(themes.light), ...Object.keys(themes.dark)])) document.documentElement.style.removeProperty('--' + key);
  for (const [key, color] of Object.entries(palette)) {
    if (/^[a-z-]+$/.test(key) && /^#[\da-f]{3,8}$/i.test(color)) document.documentElement.style.setProperty('--' + key, color);
  }
}

function mergeManagedIssues(feed) {
  const config = window.PORTFOLIO_CONTENT;
  if (!config) return feed;
  const hidden = new Set(config.hiddenIssues.map(Number));
  return [...feed.filter(project => !hidden.has(Number(project.number))).map(project => {
    const override = config.issueOverrides[project.number];
    if (!override) return project;
    const translations = {};
    for (const lang of ['pt','en']) translations[lang] = {...project.translations?.[lang], ...override.translations?.[lang]};
    return {...project, ...override, translations};
  }), ...config.customIssues.filter(project => !hidden.has(Number(project.number)))];
}

function managedIssueHtml(project) {
  if (typeof project.bodyText !== 'string') return project.bodyHtml || '';
  const paragraphs = project.bodyText.split(/\n\s*\n/).map(p => '<p>' + safeText(p).replace(/\n/g, '<br>') + '</p>').join('');
  const images = (project.images || []).filter(localIssueImage).map(src => '<img src="' + safeText(src) + '" alt="" loading="lazy">').join('');
  return paragraphs + images;
}
