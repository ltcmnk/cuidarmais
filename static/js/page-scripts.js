// Centralized page scripts extracted from templates.
// Guarded initializers: each initializer runs only when its target DOM exists.
(function(){
    document.addEventListener('DOMContentLoaded', function(){

        /* -------------------- Toast, sidebar toggle and flash helpers -------------------- */
        // Provide a global toast helper (moved from inline template)
        window.showToast = function(message, type){
            try {
                const container = document.getElementById('flash-container');
                if (!container) return;
                // create a flash-like element so toasts visually match server-side flashes
                const wrapper = document.createElement('div');
                wrapper.className = 'flash flash--' + (type || 'info');
                const icon = document.createElement('span');
                icon.className = 'flash-icon';
                if (type === 'success') icon.textContent = '✓';
                else if (type === 'warning' || type === 'error') icon.textContent = '⚠';
                else icon.textContent = 'ℹ';
                const msg = document.createElement('div');
                msg.className = 'flash-message';
                msg.textContent = message;
                wrapper.appendChild(icon);
                wrapper.appendChild(msg);
                wrapper.style.opacity = '0';
                wrapper.style.transform = 'translateY(8px)';
                container.appendChild(wrapper);
                requestAnimationFrame(()=>{ wrapper.style.transition = 'opacity 250ms ease, transform 250ms ease'; wrapper.style.opacity = '1'; wrapper.style.transform = 'translateY(0)'; });

                // allow click to dismiss immediately (same behavior as server-side flashes)
                wrapper.addEventListener('click', function(){ try { this.style.transition = 'opacity 200ms ease'; this.style.opacity = '0'; setTimeout(()=> this.remove(), 220); } catch(e){} });

                setTimeout(()=>{
                    try { wrapper.style.transition = 'opacity 300ms ease'; wrapper.style.opacity = '0'; setTimeout(()=> wrapper.remove(), 350); } catch(e){}
                }, 3000);
            } catch(e) { console.error(e); }
        };

        // Sidebar toggle (moved from inline template)
        (function(){
            try {
                var toggle = document.querySelector('.sidebar-toggle');
                if (!toggle) return;
                toggle.addEventListener('click', function(){
                    document.body.classList.toggle('sidebar-open');
                });

                // close sidebar when clicking outside on small screens
                document.addEventListener('click', function(e){
                    if (!document.body.classList.contains('sidebar-open')) return;
                    var sidebar = document.querySelector('.sidebar');
                    if (!sidebar) return;
                    if (!sidebar.contains(e.target) && !toggle.contains(e.target)){
                        document.body.classList.remove('sidebar-open');
                    }
                });
            } catch(e) { /* swallow */ }
        })();

        /* Expand/collapse behavior removed — replaced by simple-expand.js (new implementation). */

        /* -------------------- Live table filtering (search-as-you-type) -------------------- */
        (function initLiveTableFilter(){
            try {
                const searchInputs = document.querySelectorAll('.filter-container .search-input');
                if (!searchInputs || searchInputs.length === 0) return;

                // Simple debounce helper
                function debounce(fn, wait){ let t = null; return function(){ const args = arguments; clearTimeout(t); t = setTimeout(()=> fn.apply(this, args), wait); }; }

                searchInputs.forEach(input => {
                    const table = document.querySelector('.table-container .data-table');
                    if (!table) return;
                    const tbody = table.querySelector('tbody');
                    if (!tbody) return;

                    // create a no-results row placeholder (class on TR for easy selection)
                    const noRow = document.createElement('tr');
                    noRow.className = 'no-results';
                    const noCell = document.createElement('td');
                    noCell.colSpan = table.querySelectorAll('thead th').length || 1;
                    noCell.style.textAlign = 'center';
                    noCell.style.padding = '1rem';
                    noCell.textContent = 'Nenhum registro encontrado.';
                    noRow.appendChild(noCell);

                    function filterNow(){
                        const q = (input.value || '').trim().toLowerCase();
                        let visible = 0;
                        Array.from(tbody.querySelectorAll('tr')).forEach(row => {
                            // skip our placeholder row if present
                            if (row.classList && row.classList.contains('no-results')) return;

                            // Prefer checking explicit attributes: username, cpf, userName (data-*)
                            const ds = row.dataset || {};
                            const username = (ds.username || '').toLowerCase();
                            const cpf = (ds.cpf || '').toLowerCase();
                            const uname = (ds.userName || ds.userName || '').toLowerCase();
                            // fallback to first cell text if no data attributes
                            const firstCell = row.querySelector('td');
                            const firstText = firstCell ? firstCell.textContent.trim().toLowerCase() : '';

                            const textToSearch = [username, cpf, uname, firstText].join(' ');
                            const match = q === '' || (textToSearch.indexOf(q) !== -1);
                            row.style.display = match ? '' : 'none';
                            if (match) visible++;
                        });

                        // manage placeholder presence (TR.no-results)
                        if (visible === 0){
                            if (!tbody.querySelector('tr.no-results')) tbody.appendChild(noRow);
                        } else {
                            const ph = tbody.querySelector('tr.no-results'); if (ph) ph.remove();
                        }
                    }

                    const debounced = debounce(filterNow, 180);
                    input.addEventListener('input', debounced);

                    // also filter on page load if there's a prefilled value
                    if (input.value && input.value.trim() !== '') filterNow();
                });
            } catch(e){ console.error('initLiveTableFilter error', e); }
        })();

        // Auto-dismiss flashes after 3s (moved from inline template)
        (function(){
            try {
                const flashes = document.querySelectorAll('.flash');
                if (!flashes) return;

                // Allow click to dismiss immediately
                flashes.forEach(f => {
                    f.addEventListener('click', function(){
                        try { this.style.transition = 'opacity 200ms ease'; this.style.opacity = '0'; setTimeout(()=> this.remove(), 220); } catch(e){}
                    });
                });

                // Auto-dismiss after 3s
                setTimeout(()=>{
                    flashes.forEach(f => {
                        try { f.style.transition = 'opacity 300ms ease'; f.style.opacity = '0'; setTimeout(()=> f.remove(), 350); } catch(e){}
                    });
                }, 3000);
            } catch(e) { /* swallow */ }
        })();

        /* -------------------- User form helpers -------------------- */
        (function initUserForm(){
            const form = document.querySelector('form');
            if (!form) return; // not on a page with a form

            // Keep SQL-named hidden inputs in sync with visible inputs
            const nomeVisible = document.getElementById('nome');
            const sobrenomeVisible = document.getElementById('sobrenome');
            const sqlNome = document.getElementById('sql_nome');
            function updateSqlNome(){
                if (!sqlNome) return;
                const n = (nomeVisible && nomeVisible.value) ? nomeVisible.value.trim() : '';
                const s = (sobrenomeVisible && sobrenomeVisible.value) ? sobrenomeVisible.value.trim() : '';
                sqlNome.value = (n + (s ? (' ' + s) : '') ).trim();
            }
            if (nomeVisible) nomeVisible.addEventListener('input', updateSqlNome);
            if (sobrenomeVisible) sobrenomeVisible.addEventListener('input', updateSqlNome);

            const birthVisible = document.getElementById('data_nascimento');
            const sqlBirth = document.getElementById('sql_data_nascimento');
            if (birthVisible && sqlBirth) birthVisible.addEventListener('change', () => sqlBirth.value = birthVisible.value);

            // prefer celular as the primary phone for legacy sql_phone field
            const phoneVisible = document.getElementById('celular') || document.getElementById('telefone_residencial');
            const sqlPhone = document.getElementById('sql_telefone');
            if (phoneVisible && sqlPhone) phoneVisible.addEventListener('input', () => sqlPhone.value = phoneVisible.value);

            // on submit, also copy visible values to legacy hidden fields if present
            form.addEventListener('submit', function(){
                updateSqlNome();
                if (birthVisible && sqlBirth) sqlBirth.value = birthVisible.value;
                if (phoneVisible && sqlPhone) sqlPhone.value = phoneVisible.value;
            });

            // Conditional fields wiring
            function updateConditionalFields(){
                try {
                    const occ = document.getElementById('ocupacao');
                    const occGroup = document.getElementById('ocupacao_outro_group');
                    const occOther = document.getElementById('ocupacao_outro');
                    if (occ && occGroup){
                        if (occ.value === 'outro'){
                            occGroup.style.display = 'block';
                            occOther && occOther.removeAttribute('disabled');
                        } else {
                            occGroup.style.display = 'none';
                            occOther && (occOther.disabled = true);
                        }
                    }

                    const acompRadios = document.getElementsByName('acomp_med_radio');
                    const acompQualGroup = document.getElementById('acomp_med_qual_group');
                    const acompQual = document.getElementById('acomp_med_qual');
                    if (acompRadios && acompQualGroup){
                        let selected = 'no';
                        for (const r of acompRadios) if (r.checked) { selected = r.value; break; }
                        if (selected === 'yes'){
                            acompQualGroup.style.display = 'block';
                            acompQual && acompQual.removeAttribute('disabled');
                        } else {
                            acompQualGroup.style.display = 'none';
                            acompQual && (acompQual.disabled = true);
                        }
                    }

                    const jaVolRadios = document.getElementsByName('ja_volunt_radio');
                    const jaVolOndeGroup = document.getElementById('ja_volunt_onde_group');
                    const jaVolOnde = document.getElementById('ja_volunt_onde');
                    if (jaVolRadios && jaVolOndeGroup){
                        let selected = 'no';
                        for (const r of jaVolRadios) if (r.checked) { selected = r.value; break; }
                        if (selected === 'yes'){
                            jaVolOndeGroup.style.display = 'block';
                            jaVolOnde && jaVolOnde.removeAttribute('disabled');
                        } else {
                            jaVolOndeGroup.style.display = 'none';
                            jaVolOnde && (jaVolOnde.disabled = true);
                        }
                    }

                    const habRadios = document.getElementsByName('hab_musical_radio');
                    const habQualGroup = document.getElementById('hab_musical_qual_group');
                    const habQual = document.getElementById('hab_musical_qual');
                    if (habRadios && habQualGroup){
                        let selected = 'no';
                        for (const r of habRadios) if (r.checked) { selected = r.value; break; }
                        if (selected === 'yes'){
                            habQualGroup.style.display = 'block';
                            habQual && habQual.removeAttribute('disabled');
                        } else {
                            habQualGroup.style.display = 'none';
                            habQual && (habQual.disabled = true);
                        }
                    }
                } catch(e) { console.error(e); }
            }

            const occEl = document.getElementById('ocupacao'); if (occEl) occEl.addEventListener('change', updateConditionalFields);
            const acompEls = document.getElementsByName('acomp_med_radio'); for (const r of acompEls) r.addEventListener('change', updateConditionalFields);
            const jaVolEls = document.getElementsByName('ja_volunt_radio'); for (const r of jaVolEls) r.addEventListener('change', updateConditionalFields);
            const habEls = document.getElementsByName('hab_musical_radio'); for (const r of habEls) r.addEventListener('change', updateConditionalFields);

            // Initialize conditional visibility
            updateConditionalFields();

            // Availability controls
            (function(){
                try {
                    const days = ['seg','ter','qua','qui','sex','sab','dom'];
                    for (const d of days){
                        const cb = document.getElementById('avail_' + d + '_on');
                        const start = document.querySelector('input[name="avail_' + d + '_start"]');
                        const end = document.querySelector('input[name="avail_' + d + '_end"]');
                        if (!cb) continue;
                        const setState = ()=>{
                            if (cb.checked){
                                start && start.removeAttribute('disabled');
                                end && end.removeAttribute('disabled');
                            } else {
                                start && (start.disabled = true);
                                end && (end.disabled = true);
                            }
                        };
                        cb.addEventListener('change', setState);
                        setState();
                    }
                } catch(e){ console.error(e); }
            })();

            // Username availability check (debounced)
            (function(){
                const usernameInput = document.getElementById('username');
                const feedback = document.getElementById('username-feedback');
                const currentUserIdEl = document.getElementById('current_user_id');
                const currentUserId = currentUserIdEl ? currentUserIdEl.value : '';
                const checkUrlEl = document.getElementById('check_username_url');
                const checkUrl = checkUrlEl ? checkUrlEl.value : '';
                let timer = null;
                let usernameAvailable = true;
                if (feedback && feedback.textContent && feedback.textContent.trim().length > 0) {
                    feedback.style.color = 'red';
                    usernameAvailable = false;
                }
                function checkNow(){
                    if (!usernameInput) return;
                    const v = usernameInput.value.trim();
                    if (!v){ if (feedback) { feedback.textContent = ''; } usernameAvailable = true; return; }
                    const urlBase = checkUrl || '/users/check_username';
                    fetch(urlBase + '?username=' + encodeURIComponent(v) + '&user_id=' + encodeURIComponent(currentUserId), { credentials: 'same-origin' })
                        .then(r => r.json()).then(j => {
                            if (!feedback) return;
                            if (j.available){
                                feedback.textContent = j.message || 'Disponível';
                                feedback.style.color = '';
                                feedback.classList.remove('error');
                                feedback.classList.add('success');
                                if (usernameInput) usernameInput.classList.remove('is-invalid');
                                usernameAvailable = true;
                            } else {
                                feedback.textContent = j.message || 'Indisponível';
                                feedback.style.color = '';
                                feedback.classList.remove('success');
                                feedback.classList.add('error');
                                if (usernameInput) usernameInput.classList.add('is-invalid');
                                usernameAvailable = false;
                            }
                        
                        }).catch(err => { if (feedback) { feedback.textContent = ''; } });
                }
                if (usernameInput){
                    usernameInput.addEventListener('input', function(){ if (timer) clearTimeout(timer); timer = setTimeout(checkNow, 450); });
                    usernameInput.addEventListener('blur', checkNow);
                }
                if (form){
                    form.addEventListener('submit', function(e){
                        if (typeof usernameAvailable !== 'undefined' && usernameAvailable === false){
                            e.preventDefault();
                            if (feedback) { feedback.focus && feedback.focus(); }
                            alert('Nome de usuário indisponível — escolha outro.');
                        }
                    });
                }
            })();
        })();

        /* -------------------- Intention form (wizard) -------------------- */
        (function initIntentionForm(){
            const form = document.getElementById('intentionForm');
            if (!form) return;

            const steps = Array.from(form.querySelectorAll('.step'));
            let current = 0;

            const setStep = (idx) => {
                steps.forEach((s,i)=>{
                    const hidden = i!==idx;
                    s.hidden = hidden;
                    s.classList.toggle('active', !hidden);
                });
                const curEl = document.getElementById('currentStep'); if (curEl) curEl.textContent = idx+1;
                const pct = Math.round(((idx+1)/steps.length)*100);
                const progressBar = document.getElementById('progressBar'); if (progressBar) progressBar.style.width = pct + '%';
            };

            function validateStep(idx){
                const step = steps[idx];
                const inputs = Array.from(step.querySelectorAll('input,select,textarea'));
                for (const el of inputs){
                    if (!el.willValidate) continue;
                    if (el.disabled) continue;
                    if (!el.checkValidity()){
                        el.reportValidity();
                        return false;
                    }
                }
                if (idx === 2) {
                    const days = ['seg','ter','qua','qui','sex','sab','dom'];
                    for (const d of days){
                        const on = form.querySelector(`input[name=avail_${d}_on]`);
                        if (on && on.checked){
                            const start = form.querySelector(`input[name=avail_${d}_start]`);
                            const end = form.querySelector(`input[name=avail_${d}_end]`);
                            if (!start || !end || !start.value || !end.value){ alert('Por favor informe horário de início e fim para ' + d); return false; }
                            if (start.value >= end.value){ alert('Horário de início deve ser anterior ao horário de fim para ' + d); return false; }
                        }
                    }
                }
                return true;
            }

            // Buttons
            const nextBtn1 = document.getElementById('nextBtn1'); if (nextBtn1) nextBtn1.addEventListener('click', function(){ if (!validateStep(0)) return; current = 1; setStep(current); });
            const nextBtn2 = document.getElementById('nextBtn2'); if (nextBtn2) nextBtn2.addEventListener('click', function(){ if (!validateStep(1)) return; current = 2; setStep(current); });
            const prevBtn2 = document.getElementById('prevBtn2'); if (prevBtn2) prevBtn2.addEventListener('click', function(){ current = 0; setStep(current); });
            const prevBtn3 = document.getElementById('prevBtn3'); if (prevBtn3) prevBtn3.addEventListener('click', function(){ current = 1; setStep(current); });

            form.addEventListener('submit', function(e){ if (!validateStep(0)) { e.preventDefault(); current = 0; setStep(current); return; } if (!validateStep(1)) { e.preventDefault(); current = 1; setStep(current); return; } });

            // Conditional fields and availability
            function updateConditionalFields(){
                try {
                    const occ = document.getElementById('ocupacao');
                    const occGroup = document.getElementById('ocupacao_outro_group');
                    const occOther = document.getElementById('ocupacao_outro');
                    if (occ && occGroup){ if (occ.value === 'outro'){ occGroup.classList.remove('conditional-hidden'); occOther && occOther.removeAttribute('disabled'); } else { occGroup.classList.add('conditional-hidden'); occOther && (occOther.disabled = true); } }

                    const estado = document.getElementById('estado_civil');
                    const conjugeGroup = document.getElementById('conjuge_group');
                    if (estado && conjugeGroup){ if (String(estado.value).toLowerCase() === 'casado'){ conjugeGroup.classList.remove('conditional-hidden'); } else { conjugeGroup.classList.add('conditional-hidden'); } }

                    const acompRadios = document.getElementsByName('acomp_med_radio');
                    const acompQualGroup = document.getElementById('acomp_med_qual_group');
                    const acompQual = document.getElementById('acomp_med_qual');
                    if (acompRadios && acompQualGroup){ let selected = 'no'; for (const r of acompRadios) if (r.checked) { selected = r.value; break; } if (selected === 'yes'){ acompQualGroup.classList.remove('conditional-hidden'); acompQual && acompQual.removeAttribute('disabled'); acompQual && acompQual.focus(); } else { acompQualGroup.classList.add('conditional-hidden'); acompQual && (acompQual.disabled = true); } }

                    const jaVolRadios = document.getElementsByName('ja_volunt_radio');
                    const jaVolOndeGroup = document.getElementById('ja_volunt_onde_group');
                    const jaVolOnde = document.getElementById('ja_volunt_onde');
                    if (jaVolRadios && jaVolOndeGroup){ let selected = 'no'; for (const r of jaVolRadios) if (r.checked) { selected = r.value; break; } if (selected === 'yes'){ jaVolOndeGroup.classList.remove('conditional-hidden'); jaVolOnde && jaVolOnde.removeAttribute('disabled'); jaVolOnde && jaVolOnde.focus(); } else { jaVolOndeGroup.classList.add('conditional-hidden'); jaVolOnde && (jaVolOnde.disabled = true); } }

                    const habRadios = document.getElementsByName('hab_musical_radio');
                    const habQualGroup = document.getElementById('hab_musical_qual_group');
                    const habQual = document.getElementById('hab_musical_qual');
                    if (habRadios && habQualGroup){ let selected = 'no'; for (const r of habRadios) if (r.checked) { selected = r.value; break; } if (selected === 'yes'){ habQualGroup.classList.remove('conditional-hidden'); habQual && habQual.removeAttribute('disabled'); habQual && habQual.focus(); } else { habQualGroup.classList.add('conditional-hidden'); habQual && (habQual.disabled = true); } }
                } catch(e){ console.error(e); }
            }
            const occEl = document.getElementById('ocupacao'); if (occEl) occEl.addEventListener('change', updateConditionalFields);
            const estadoEl = document.getElementById('estado_civil'); if (estadoEl) estadoEl.addEventListener('change', updateConditionalFields);
            const acompRadios = document.getElementsByName('acomp_med_radio'); for (const r of acompRadios) r.addEventListener('change', updateConditionalFields);
            const jaVolRadios = document.getElementsByName('ja_volunt_radio'); for (const r of jaVolRadios) r.addEventListener('change', updateConditionalFields);
            const habRadios = document.getElementsByName('hab_musical_radio'); for (const r of habRadios) r.addEventListener('change', updateConditionalFields);

            const availDays = ['seg','ter','qua','qui','sex','sab','dom'];
            function attachAvailHandlers(){
                for (const d of availDays){
                    const cb = document.getElementById(`avail_${d}_on`);
                    const start = form.querySelector(`input[name=avail_${d}_start]`);
                    const end = form.querySelector(`input[name=avail_${d}_end]`);
                    if (!cb) continue;
                    const toggle = () => {
                        const enabled = cb.checked;
                        if (start) { start.disabled = !enabled; if (!enabled) start.value = ''; }
                        if (end) { end.disabled = !enabled; if (!enabled) end.value = ''; }
                    };
                    cb.addEventListener('change', toggle);
                    toggle();
                }
            }
            attachAvailHandlers();

            // hide sidebar toggle on mobile when viewing this form
            try { document.body.classList.add('hide-toggle-on-mobile'); } catch(e){}

            updateConditionalFields();
            setStep(0);
        })();

        /* -------------------- Intent modal -------------------- */
        (function initIntentModal(){
            // keep functions global for inline onclick handlers that refer to them
            window.openIntentModal = function(id){
                const row = document.querySelector('tr[data-intent-id="' + id + '"]');
                if (!row) return;
                const modal = document.getElementById('intent-modal-backdrop');
                const title = document.getElementById('intent-modal-title');
                const body = document.getElementById('intent-modal-body');
                title.textContent = row.getAttribute('data-nome') || '';

                const fields = [
                    ['Hospital','hospital'],['Nome','nome'],['Data de nascimento','data_nascimento'],['Local de nascimento','local_nascimento'],['RG','rg'],['CPF','cpf'],['Estado civil','estado_civil'],['Nome cônjuge','nome_conjuge'],['Nome do pai','nome_pai'],['Nome da mãe','nome_mae'],['Endereço','endereco'],['Telefone residencial','telefone_residencial'],['Celular','celular'],['Religião','religiao'],['E-mail','email'],['Escolaridade / curso','escolaridade_curso'],['Local de trabalho','local_trabalho'],['Telefone do trabalho','telefone_trabalho'],['Ocupação','ocupacao'],['Ocupação (outro)','ocupacao_outro'],['Acompanhamento médico','acomp_med'],['Transporte','transporte'],['Como ficou sabendo','ficou_sab'],['Já foi voluntário?','ja_volunt'],['Onde (se sim)','ja_volunt_onde'],['Faz voluntariado atualmente','faz_volunt'],['Contribuições / serviços','contrib_ser'],['Habilidade musical?','hab_musical'],['Qual habilidade musical','hab_musical_qual'],['Auxiliar alimentação?','aux_alimentacao'],['Enviado em','createdat']
                ];

                function boolToSimNao(v){ if (v === null || v === undefined || v === '') return '-'; const s = String(v).trim().toLowerCase(); if (s === '1' || s === 'true' || s === 'sim' || s === 'yes') return 'Sim'; if (s === '0' || s === 'false' || s === 'nao' || s === 'não' || s === 'no') return 'Não'; return v; }
                function formatDateTime(value){ if (!value) return '-'; const d = new Date(value); if (isNaN(d.getTime())) return value; const dd = String(d.getDate()).padStart(2,'0'); const mm = String(d.getMonth()+1).padStart(2,'0'); const yyyy = d.getFullYear(); const hh = String(d.getHours()).padStart(2,'0'); const min = String(d.getMinutes()).padStart(2,'0'); return `${dd}/${mm}/${yyyy} ${hh}:${min}`; }
                function formatDate(value){ if (!value) return '-'; const d = new Date(value); if (isNaN(d.getTime())) return value; const dd = String(d.getDate()).padStart(2,'0'); const mm = String(d.getMonth()+1).padStart(2,'0'); const yyyy = d.getFullYear(); return `${dd}/${mm}/${yyyy}`; }

                const booleanKeys = new Set(['acomp_med','ja_volunt','faz_volunt','hab_musical','aux_alimentacao']);

                let html = '<dl style="display:grid; grid-template-columns: 180px 1fr; gap:0.5rem 1rem;">';
                fields.forEach(([label, key]) => {
                    let val = row.getAttribute('data-' + key);
                    if (!val) val = '';
                    if (booleanKeys.has(key)) { val = boolToSimNao(val); }
                    if (key === 'createdat') { val = formatDateTime(val); } else if (key === 'data_nascimento') { val = formatDate(val); }
                    html += `<dt style="font-weight:600; color:var(--text-secondary);">${label}</dt><dd>${val || '-'}</dd>`;
                });
                html += '</dl>';
                body.innerHTML = html;
                modal.style.display = 'flex';
                modal.setAttribute('aria-hidden','false');
                const closeBtn = modal.querySelector('.modal-close'); if (closeBtn) closeBtn.focus();
            };

            window.closeIntentModal = function(){ const modal = document.getElementById('intent-modal-backdrop'); if (!modal) return; modal.style.display = 'none'; modal.setAttribute('aria-hidden','true'); };
            document.addEventListener('keydown', function(e){ if (e.key === 'Escape') { try { window.closeIntentModal && window.closeIntentModal(); } catch(e){} } });
        })();

        /* -------------------- Announcements modal -------------------- */
        (function initAnnouncementModal(){
            window.openAnnouncementModal = function(id){
                // tolerate multiple id naming patterns that templates may use
                const titleEl = document.getElementById('full-title-' + id) || document.getElementById('title-' + id) || document.getElementById('title-' + id + '') ;
                const msgFull = document.getElementById('full-msg-' + id) || document.getElementById('full-' + id) || document.getElementById('full_msg_' + id) || document.getElementById('full-msg_' + id);
                const msgTrunc = document.getElementById('msg-' + id) || document.getElementById('truncated-' + id) || document.getElementById('msg_' + id) || document.getElementById('truncated_msg_' + id);
                const modalBackdrop = document.getElementById('announcement-modal-backdrop');
                const modalTitle = document.getElementById('announcement-modal-title');
                const modalBody = document.getElementById('announcement-modal-body');
                modalTitle.textContent = titleEl ? titleEl.textContent : '';
                const row = document.querySelector('tr[data-ann-id="' + id + '"]');
                if (row) { const author = row.getAttribute('data-ann-author') || ''; const pub = row.getAttribute('data-ann-pub') || ''; const modalAuthor = document.getElementById('announcement-modal-author'); const modalPub = document.getElementById('announcement-modal-pub'); if (modalAuthor) modalAuthor.textContent = author; if (modalPub) modalPub.textContent = pub; }
                if (msgFull && msgFull.textContent) { modalBody.textContent = msgFull.textContent.trim(); } else if (msgTrunc && msgTrunc.textContent) { modalBody.textContent = msgTrunc.textContent.trim(); } else { modalBody.textContent = ''; }
                modalBackdrop.style.display = 'flex'; modalBackdrop.setAttribute('aria-hidden','false'); const closeBtn = modalBackdrop.querySelector('.modal-close'); if (closeBtn) closeBtn.focus();
            };
            window.closeAnnouncementModal = function(){ const modalBackdrop = document.getElementById('announcement-modal-backdrop'); if (!modalBackdrop) return; modalBackdrop.style.display = 'none'; modalBackdrop.setAttribute('aria-hidden','true'); };
            document.addEventListener('keydown', function(e){ if (e.key === 'Escape') { try { window.closeAnnouncementModal && window.closeAnnouncementModal(); } catch(e){} } });
            document.addEventListener('click', function(e){ const backdrop = document.getElementById('announcement-modal-backdrop'); if (!backdrop) return; if (e.target === backdrop) closeAnnouncementModal(); });
        })();

        /* Announcements expand/collapse: inline simple-expand implementation.
           This was previously a separate `simple-expand.js` file; embedding
           here avoids an extra DOMContentLoaded listener and keeps handlers
           consolidated in `page-scripts.js`. */
        (function initSimpleExpand(){
            // Toggle expanded state for a container
            function toggle(container){
                if (!container) return;
                const truncated = container.querySelector('.truncated-box');
                const full = container.querySelector('.full-text');
                // Prefer the button inside the container, fallback to global
                const btn = container.querySelector('[data-target="' + container.id + '"]') || document.querySelector('[data-target="' + container.id + '"]');
                if (!btn) return;

                const expanded = container.classList.toggle('expanded');
                if (expanded) {
                    btn.textContent = 'Ver menos';
                    btn.setAttribute('aria-expanded','true');
                    btn.setAttribute('aria-label','Ver menos');
                } else {
                    btn.textContent = 'Ver mais';
                    btn.setAttribute('aria-expanded','false');
                    btn.setAttribute('aria-label','Ver mais');
                }
            }

            // Delegate clicks for expand buttons
            document.addEventListener('click', function(e){
                const btn = e.target.closest && e.target.closest('.expand-btn');
                if (!btn) return;
                const targetId = btn.getAttribute('data-target');
                if (!targetId) return;
                const container = document.getElementById(targetId);
                if (!container) return;
                e.preventDefault();
                toggle(container);
            });

            // Initialize each announcement/event message block.
            document.querySelectorAll('.announcement-message').forEach(function(container){
                try {
                    const full = container.querySelector('.full-text');
                    const truncated = container.querySelector('.truncated-box');
                    if (!full) return;
                    if (truncated) {
                        // Expandable: hide the full copy until expanded
                        full.style.display = 'none';
                        full.style.maxHeight = 'none';
                        try { full.setAttribute('aria-hidden', 'true'); } catch(e){}
                    } else {
                        // Short message: force visible and override stylesheet cascades
                        try { full.removeAttribute('aria-hidden'); } catch(e){}
                        try {
                            full.style.setProperty('display', 'block', 'important');
                            full.style.setProperty('opacity', '1', 'important');
                            full.style.setProperty('max-height', 'none', 'important');
                        } catch(e) {
                            full.style.display = 'block';
                            full.style.opacity = '1';
                            full.style.maxHeight = 'none';
                        }
                    }
                } catch (e) { /* swallow per-site pattern */ }
            });
        })();

        /* -------------------- User (volunteer) modal -------------------- */
        (function initUserModal(){
            window.openUserModal = function(id){
                const row = document.querySelector('tr[data-user-id="' + id + '"]');
                if (!row) return;
                const modal = document.getElementById('user-modal-backdrop');
                const title = document.getElementById('user-modal-title');
                const body = document.getElementById('user-modal-body');
                title.textContent = row.getAttribute('data-name') || row.getAttribute('data-username') || '';

                const fields = [
                    ['Hospital','hospital'],['Nome','nome'],['Sobrenome','sobrenome'],['Data de nascimento','data_nascimento'],['Local de nascimento','local_nascimento'],['RG','rg'],['CPF','cpf'],['Endereço','endereco'],['Nº','numero'],['Bairro','bairro'],['CEP','cep'],['Cidade','cidade'],['Telefone residencial','telefone_residencial'],['Celular','celular'],['E-mail','email'],['Estado civil','estado_civil'],['Nome do cônjuge','nome_conjuge'],['Religião','religiao'],['Escolaridade / curso','escolaridade_curso'],['Local de trabalho','local_trabalho'],['Telefone do trabalho','telefone_trabalho'],['Ocupação','ocupacao'],['Ocupação (outro)','ocupacao_outro'],['Acompanhamento médico','acomp_med'],['Acompanhamento (qual)','acomp_med_qual'],['Transporte','transporte'],['Como ficou sabendo','ficou_sab'],['Já foi voluntário?','ja_volunt'],['Onde (se sim)','ja_volunt_onde'],['Contribuições / serviços','contrib_ser'],['Habilidade musical?','hab_musical'],['Qual habilidade musical','hab_musical_qual'],['Auxiliar alimentação?','aux_alimentacao'],['Código do crachá','codigo_cracha'],['Função','role'],['Horas (resumo)','hours'],['Horas trabalhadas','hours_trabalhadas']
                ];

                function boolToSimNao(v){ if (v === null || v === undefined || v === '') return '-'; const s = String(v).trim().toLowerCase(); if (s === '1' || s === 'true' || s === 'sim' || s === 'yes') return 'Sim'; if (s === '0' || s === 'false' || s === 'nao' || s === 'não' || s === 'no') return 'Não'; return v; }

                let html = '<dl style="display:grid; grid-template-columns: 160px 1fr; gap:0.5rem 1rem;">';
                fields.forEach(([label, key]) => {
                    let val = row.getAttribute('data-' + key) || '';
                    // boolean-like fields
                    if (['acomp_med','ja_volunt','hab_musical','aux_alimentacao'].indexOf(key) >= 0) { val = boolToSimNao(val); }
                    html += `<dt style="font-weight:600; color:var(--text-secondary);">${label}</dt><dd>${val || '-'}</dd>`;
                });

                // availability (days): show start-end pairs if present
                const days = [['seg','2ª feira'],['ter','3ª feira'],['qua','4ª feira'],['qui','5ª feira'],['sex','6ª feira'],['sab','Sábado'],['dom','Domingo']];
                html += `<dt style="font-weight:600; color:var(--text-secondary);">Disponibilidade</dt><dd>`;
                let anyAvail = false;
                days.forEach(([d,label]) => {
                    const on = row.getAttribute('data-avail_' + d + '_on');
                    const start = row.getAttribute('data-avail_' + d + '_start') || '';
                    const end = row.getAttribute('data-avail_' + d + '_end') || '';
                    if (on && String(on).trim() !== ''){
                        anyAvail = true;
                        html += `<div><strong>${label}:</strong> ${start || '-'} — ${end || '-'}</div>`;
                    }
                });
                if (!anyAvail) html += '-';
                html += `</dd>`;

                html += '</dl>';
                body.innerHTML = html;
                modal.style.display = 'flex';
                modal.setAttribute('aria-hidden','false');
                const closeBtn = modal.querySelector('.modal-close'); if (closeBtn) closeBtn.focus();
            };

            window.closeUserModal = function(){ const modal = document.getElementById('user-modal-backdrop'); if (!modal) return; modal.style.display = 'none'; modal.setAttribute('aria-hidden','true'); };
            document.addEventListener('keydown', function(e){ if (e.key === 'Escape') { try { window.closeUserModal && window.closeUserModal(); } catch(e){} } });
            document.addEventListener('click', function(e){ const backdrop = document.getElementById('user-modal-backdrop'); if (!backdrop) return; if (e.target === backdrop) window.closeUserModal(); });
        })();

        /* -------------------- Export dropdowns (CSV / XLSX) -------------------- */
        (function initExportDropdowns(){
            // Toggle dropdown menus
            function closeAllExportMenus(){
                document.querySelectorAll('.export-dropdown .export-menu').forEach(m=>{ m.style.display = 'none'; m.setAttribute('aria-hidden','true'); });
                document.querySelectorAll('.export-dropdown .export-toggle').forEach(b=>b.setAttribute('aria-expanded','false'));
            }

            document.addEventListener('click', function(e){
                // close menus when clicking outside
                const toggle = e.target.closest('.export-toggle');
                if (toggle){
                    const dropdown = toggle.closest('.export-dropdown');
                    const menu = dropdown.querySelector('.export-menu');
                    const isOpen = menu.style.display === 'block';
                    closeAllExportMenus();
                    if (!isOpen){ menu.style.display = 'block'; menu.setAttribute('aria-hidden','false'); toggle.setAttribute('aria-expanded','true'); }
                    return;
                }

                // clicking on export-item inside a form card
                const item = e.target.closest('.export-item');
                if (item){
                    const fmt = item.getAttribute('data-format');
                    const formId = item.getAttribute('data-form-id');
                    const clearUser = item.getAttribute('data-clear-user');
                    if (formId){
                        const form = document.getElementById(formId);
                        if (form){
                            // optionally clear user_id hidden fields inside the form
                            if (clearUser && String(clearUser) !== '0'){
                                const userIdEls = form.querySelectorAll('input[name="user_id"], input[id$="user-id-presences"], input[id$="user-id-hours"]');
                                userIdEls.forEach(u => u.value = '');
                            }
                            let reportInput = form.querySelector('input[name="report"]');
                            if (!reportInput){ reportInput = document.createElement('input'); reportInput.type = 'hidden'; reportInput.name = 'report'; form.appendChild(reportInput); }
                            reportInput.value = fmt;
                            form.submit();
                        }
                    }
                    closeAllExportMenus();
                    return;
                }

                // click on header links (.export-link) will follow href naturally; close menus otherwise
                closeAllExportMenus();
            });

            /* -------------------- Confirmation modal wiring (generic) -------------------- */
            (function initConfirmActions(){
                try {
                    const confirmBackdrop = document.getElementById('confirm-modal-backdrop');
                    const confirmBody = document.getElementById('confirm-modal-body');
                    const confirmOk = document.getElementById('confirm-ok');
                    const confirmCancel = document.getElementById('confirm-cancel');
                    if (!confirmBackdrop || !confirmBody || !confirmOk) return;

                    let pendingForm = null;

                    function openConfirm(message, form){
                        pendingForm = form || null;
                        confirmBody.textContent = message || 'Confirma a ação?';
                        confirmBackdrop.style.display = 'flex';
                        confirmBackdrop.setAttribute('aria-hidden', 'false');
                        // focus confirm button for accessibility
                        setTimeout(()=> confirmOk.focus(), 40);
                    }

                    function closeConfirm(){
                        pendingForm = null;
                        confirmBackdrop.style.display = 'none';
                        confirmBackdrop.setAttribute('aria-hidden', 'true');
                    }

                    // attach click handlers for all forms with .confirm-action
                    document.querySelectorAll('form.confirm-action').forEach(f => {
                        f.addEventListener('submit', function(e){
                            // if form already has data-confirmed, allow submit
                            if (f.dataset.confirmed === '1') return;
                            e.preventDefault();
                            // message can come from data-confirm-message attribute or default
                            const msg = f.getAttribute('data-confirm-message') || (f.classList.contains('toggle-active-form') ? 'Tem certeza que deseja alterar o estado deste usuário?' : 'Tem certeza que deseja prosseguir?');
                            openConfirm(msg, f);
                        });
                    });

                    // confirm OK -> submit the pending form (mark confirmed to avoid infinite loop)
                    confirmOk.addEventListener('click', function(){
                        if (!pendingForm) { closeConfirm(); return; }

                        // If this is the toggle-active form, submit via AJAX and update UI in-place
                        if (pendingForm.classList.contains('toggle-active-form')){
                            const form = pendingForm;
                            // prepare body (send form fields if any)
                            const body = new URLSearchParams(new FormData(form)).toString();
                            fetch(form.action, {
                                method: 'POST',
                                headers: {
                                    'X-Requested-With': 'XMLHttpRequest',
                                    'Content-Type': 'application/x-www-form-urlencoded'
                                },
                                body: body,
                                credentials: 'same-origin'
                            }).then(async r => {
                                // Try to parse JSON safely; if content is not JSON, fall back to text
                                let parsed = null;
                                const ct = (r.headers.get && r.headers.get('content-type')) || '';
                                if (ct.indexOf('application/json') !== -1) {
                                    try { parsed = await r.json(); } catch(e) { parsed = null; }
                                } else {
                                    try {
                                        const txt = await r.text();
                                        try { parsed = JSON.parse(txt); } catch(e) { parsed = txt; }
                                    } catch(e){ parsed = null; }
                                }
                                if (!r.ok) {
                                    // Normalized error object for downstream handling
                                    throw parsed || { message: 'Erro ao atualizar usuário', status: r.status };
                                }
                                return parsed;
                            }).then(json => {
                                // expected {status:'ok', new_state: 0|1}
                                if (json && json.status === 'ok'){
                                    // find the enclosing table row
                                    const row = form.closest('tr');
                                    if (row){
                                        row.dataset.estado_user = String(json.new_state);
                                        // update button label in the form
                                        const btn = form.querySelector('button[type="submit"]');
                                        if (btn){
                                            if (json.new_state === 1){
                                                btn.textContent = 'Desativar';
                                                btn.classList.remove('btn-success'); btn.classList.add('btn-danger');
                                                btn.title = 'Desativar usuário';
                                            } else {
                                                btn.textContent = 'Ativar';
                                                btn.classList.remove('btn-danger'); btn.classList.add('btn-success');
                                                btn.title = 'Ativar usuário';
                                            }
                                        }
                                    }
                                    closeConfirm();
                                    showToast('Estado do usuário atualizado', 'success');
                                } else {
                                    closeConfirm();
                                    const msg = (json && (json.message || json.msg)) || 'Erro ao atualizar usuário';
                                    showToast(msg, 'error');
                                }
                            }).catch(err => {
                                closeConfirm();
                                try {
                                    // err may be a string, object with message, or parsed JSON
                                    let msg = 'Erro ao atualizar usuário';
                                    if (!err) msg = 'Erro ao atualizar usuário';
                                    else if (typeof err === 'string') msg = err;
                                    else if (err.message) msg = err.message;
                                    else if (err.msg) msg = err.msg;
                                    else if (err.message === undefined && err.status) msg = err.status + ' - Erro ao atualizar usuário';
                                    showToast(msg, 'error');
                                } catch(e){}
                            });

                            return;
                        }

                        // fallback: submit normally
                        pendingForm.dataset.confirmed = '1';
                        pendingForm.submit();
                    });

                    // cancel
                    confirmCancel && confirmCancel.addEventListener('click', function(){ closeConfirm(); });
                    // close when clicking backdrop outside modal
                    confirmBackdrop.addEventListener('click', function(e){ if (e.target === confirmBackdrop) closeConfirm(); });
                    // escape to close
                    document.addEventListener('keydown', function(e){ if (e.key === 'Escape') closeConfirm(); });

                    // expose globally so inline onclick="closeConfirmModal()" in templates also works
                    window.closeConfirmModal = closeConfirm;
                    window.closeConfirm = closeConfirm;
                } catch (e){ console.error('initConfirmActions error', e); }
            })();

            // close on Escape
            document.addEventListener('keydown', function(e){ if (e.key === 'Escape') closeAllExportMenus(); });
        })();
    });
})();
