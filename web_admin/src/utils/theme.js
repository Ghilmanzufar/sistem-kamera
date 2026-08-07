// 👱 Ponytail Theme Utility: Dark & Light Mode Switcher
export function getStoredTheme() {
  return localStorage.getItem('app_theme') || 'dark';
}

export function applyTheme(theme) {
  const root = document.documentElement;
  if (theme === 'light') {
    root.classList.add('light');
    root.classList.remove('dark');
  } else {
    root.classList.add('dark');
    root.classList.remove('light');
  }
  localStorage.setItem('app_theme', theme);
}

export function initTheme() {
  const theme = getStoredTheme();
  applyTheme(theme);
  return theme;
}

export function toggleTheme() {
  const current = getStoredTheme();
  const nextTheme = current === 'light' ? 'dark' : 'light';
  applyTheme(nextTheme);
  return nextTheme;
}
