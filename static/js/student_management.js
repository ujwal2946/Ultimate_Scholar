(function(){
  function initDeleteButtons(){
    const buttons = document.querySelectorAll('.student-delete-btn');
    buttons.forEach(btn => {
      btn.addEventListener('click', function(){
        const name = btn.getAttribute('data-student-name') || 'this student';
        const ok = window.confirm(`Are you sure you want to delete ${name}? This action cannot be undone.`);
        if(!ok) return;
        // find parent form and submit
        const form = btn.closest('form');
        if(form){
          // submit after confirmation
          form.submit();
        }
      });
    });
  }

  function initLoadingOverlay(){
    const overlayId = 'studentMgmtLoadingOverlay';
    if(document.getElementById(overlayId)) return;

    const overlay = document.createElement('div');
    overlay.id = overlayId;
    overlay.style.position = 'fixed';
    overlay.style.top = '0';
    overlay.style.left = '0';
    overlay.style.width = '100%';
    overlay.style.height = '100%';
    overlay.style.background = 'rgba(0,0,0,0.35)';
    overlay.style.display = 'none';
    overlay.style.alignItems = 'center';
    overlay.style.justifyContent = 'center';
    overlay.style.zIndex = '1055';
    overlay.innerHTML = `
      <div class="card card-glass p-3" style="min-width:220px; text-align:center;">
        <div class="spinner-border text-primary" role="status"></div>
        <div class="mt-2 text-muted small">Please wait...</div>
      </div>
    `;
    document.body.appendChild(overlay);

    window.showStudentMgmtLoading = function(){ overlay.style.display = 'flex'; };
    window.hideStudentMgmtLoading = function(){ overlay.style.display = 'none'; };
  }

  function initFormSubmitLoading(){
    const forms = document.querySelectorAll('form');
    forms.forEach(f => {
      f.addEventListener('submit', function(){
        if(typeof window.showStudentMgmtLoading === 'function') window.showStudentMgmtLoading();
      });
    });
  }

  function initToasts(){
    // minimal: use bootstrap alerts already rendered by templates.
    // We'll show a toast if window.__studentMgmtSuccess is set.
    if(window.__studentMgmtSuccess !== true) return;

    const toastEl = document.createElement('div');
    toastEl.className = 'toast align-items-center text-bg-success border-0 show';
    toastEl.role = 'alert';
    toastEl.ariaLive = 'assertive';
    toastEl.ariaAtomic = 'true';
    toastEl.style.position = 'fixed';
    toastEl.style.bottom = '20px';
    toastEl.style.right = '20px';
    toastEl.style.zIndex = '1060';
    toastEl.innerHTML = `
      <div class="d-flex">
        <div class="toast-body">
          Student created successfully!
        </div>
        <button type="button" class="btn-close btn-close-white me-2 m-auto" aria-label="Close"></button>
      </div>
    `;
    document.body.appendChild(toastEl);

    const closeBtn = toastEl.querySelector('.btn-close');
    if(closeBtn){
      closeBtn.addEventListener('click', ()=> toastEl.remove());
    }

    setTimeout(()=>{
      if(toastEl && toastEl.parentNode) toastEl.remove();
    }, 3500);
  }

  document.addEventListener('DOMContentLoaded', function(){
    initDeleteButtons();
    initLoadingOverlay();
    initFormSubmitLoading();
    initToasts();
  });
})();

