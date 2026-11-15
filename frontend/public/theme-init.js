// Apply the saved theme before first paint to avoid a flash (external file keeps the CSP strict).
try {
  var t = localStorage.getItem('nl-sql-theme')
  if (t === 'light' || t === 'dark') document.documentElement.dataset.theme = t
} catch (e) {}
