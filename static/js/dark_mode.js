(function(){
  const root = document.documentElement;
  const key = 'std_dbms_theme';
  const saved = localStorage.getItem(key);

  function setTheme(theme){
    root.setAttribute('data-bs-theme', theme === 'dark' ? 'dark' : 'light');

    const btn = document.getElementById('darkModeToggle');
    if(btn){
      btn.setAttribute('aria-pressed', theme === 'dark' ? 'true' : 'false');
      const label = btn.querySelector('.theme-label');
      if(label) label.textContent = theme === 'dark' ? 'Light' : 'Dark';
    }
  }

  if(saved){ setTheme(saved); }

  const btn = document.getElementById('darkModeToggle');
  if(btn){
    btn.addEventListener('click', function(){
      const cur = root.getAttribute('data-bs-theme') || 'light';
      const next = cur === 'dark' ? 'light' : 'dark';
      localStorage.setItem(key, next);
      setTheme(next);
    });
  }

  // Mobile sidebar toggle
  const sidebar = document.getElementById('sidebar');
  const sidebarToggle = document.getElementById('sidebarToggle');
  if(sidebar && sidebarToggle){
    sidebarToggle.addEventListener('click', function(){
      const open = sidebar.classList.toggle('is-open');
      document.body.classList.toggle('sidebar-open', open);
      sidebarToggle.setAttribute('aria-expanded', open ? 'true' : 'false');
    });

    document.addEventListener('click', function(event){
      if(window.innerWidth <= 992 && sidebar.classList.contains('is-open') &&
         !sidebar.contains(event.target) && !sidebarToggle.contains(event.target)){
        sidebar.classList.remove('is-open');
        document.body.classList.remove('sidebar-open');
        sidebarToggle.setAttribute('aria-expanded', 'false');
      }
    });
  }
})();

