function playSfx() {
    const clickSfx = document.getElementById('click-sfx');
    if (!clickSfx) return;
    clickSfx.currentTime = 0;
    clickSfx.play().catch(e => {
        console.warn("Audio playback delayed until user interaction.");
    });
}

document.addEventListener('click', (e) => {
    if (e.target.closest('button, a, .btn, .action-btn, .nav-links a')) {
        playSfx();
    }
}, true);

document.addEventListener('mousedown', () => {
    const clickSfx = document.getElementById('click-sfx');
    if (clickSfx) clickSfx.load();
}, {
    once: true
});

document.querySelectorAll('.flash-msg').forEach(el => {
    setTimeout(() => {
        el.style.opacity = '0';
        el.style.transform = 'translateX(20px)';
        el.style.transition = 'all 0.4s ease';
        setTimeout(() => el.remove(), 400);
    }, 4000);
});

function initPasswordStrength(inputId, barId, labelId) {
    const inp = document.getElementById(inputId);
    const bar = document.getElementById(barId);
    const lbl = document.getElementById(labelId);
    if (!inp || !bar) return;

    const levels = [
        { label: 'Very Weak', color: '#ef4444', pct: 10 },
        { label: 'Weak', color: '#f97316', pct: 30 },
        { label: 'Fair', color: '#eab308', pct: 55 },
        { label: 'Strong', color: '#22c55e', pct: 80 },
        { label: 'Very Strong', color: '#4ade80', pct: 100 }
    ];

    inp.addEventListener('input', () => {
        const v = inp.value;
        let score = 0;
        if (v.length >= 8) score++;
        if (v.length >= 12) score++;
        if (/[A-Z]/.test(v)) score++;
        if (/[0-9]/.test(v)) score++;
        if (/[^A-Za-z0-9]/.test(v)) score++;

        const lvl = levels[Math.min(score, 4)];
        bar.style.width = lvl.pct + '%';
        bar.style.background = lvl.color;
        if (lbl) {
            lbl.textContent = v ? lvl.label : '';
            lbl.style.color = lvl.color;
        }
    });
}
initPasswordStrength('password', 'strength-bar', 'strength-label');
initPasswordStrength('aes-password', 'aes-strength-bar', 'aes-strength-label');

function setupDragDrop(zoneId, inputId, onFile) {
    const zone = document.getElementById(zoneId);
    const input = document.getElementById(inputId);
    if (!zone || !input) return;

    zone.addEventListener('click', () => input.click());
    zone.addEventListener('dragover', e => {
        e.preventDefault();
        zone.classList.add('dragover');
    });
    zone.addEventListener('dragleave', () => zone.classList.remove('dragover'));
    zone.addEventListener('drop', e => {
        e.preventDefault();
        zone.classList.remove('dragover');
        if (e.dataTransfer.files.length) onFile(e.dataTransfer.files[0]);
    });
    input.addEventListener('change', e => {
        if (e.target.files.length) onFile(e.target.files[0]);
    });
}

(function initHidePage() {
    if (!document.getElementById('hide-form')) return;

    let coverFile = null;
    const coverInput = document.getElementById('cover-file-input');
    const updateCoverAccept = () => {
        const mode = document.querySelector('input[name="cover_mode"]:checked')?.value;
        const inst = document.getElementById('cover-instructions');
        if (mode === '2D') {
            coverInput.accept = 'image/*';
            if (inst) inst.textContent = 'Supported: PNG, JPG, BMP, WebP';
        } else {
            coverInput.accept = '.obj,.npy,.npz,.bin,.ply,.stl,.glb,.fbx';
            if (inst) inst.textContent = 'Supported: .obj, .npy, .bin, .ply, .glb, .fbx';
        }
    };
    document.querySelectorAll('input[name="cover_mode"]').forEach(r => {
        r.addEventListener('change', updateCoverAccept);
    });
    updateCoverAccept();

    setupDragDrop('cover-drop-zone', 'cover-file-input', f => {
        const mode = document.querySelector('input[name="cover_mode"]:checked')?.value;
        const ext = f.name.split('.').pop().toLowerCase();
        const imgExts = ['png', 'jpg', 'jpeg', 'bmp', 'webp'];
        const ext3d = ['obj', 'npy', 'npz', 'bin', 'ply', 'stl', 'glb', 'fbx'];
        const isImg = f.type.match(/image\/.*/) || imgExts.includes(ext);
        const is3d = ext3d.includes(ext);

        if (mode === '2D' && !isImg) {
            showToast('Please select a valid IMAGE file for 2D mode.', 'error');
            return;
        }
        if (mode === '3D' && !is3d) {
            showToast('Please select a valid 3D file for 3D mode.', 'error');
            return;
        }
        if (!isImg && !is3d) {
            showToast('Unsupported file format.', 'error');
            return;
        }

        coverFile = f;
        document.getElementById('cover-filename').textContent = f.name;

        if (isImg) {
            const reader = new FileReader();
            reader.onload = e => document.getElementById('cover-preview').src = e.target.result;
            reader.readAsDataURL(f);
        } else {
            document.getElementById('cover-preview').src =
                'data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="80" height="80" viewBox="0 0 24 24" fill="none" stroke="%236366f1" stroke-width="2"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/></svg>';
        }
        show('cover-step-2');
        hide('cover-drop-zone');
        hide('hide-result');
    });

    document.getElementById('clear-cover')?.addEventListener('click', () => {
        coverFile = null;
        document.getElementById('cover-file-input').value = '';
        show('cover-drop-zone');
        hide('cover-step-2');
        hide('hide-result');
    });

    setupDragDrop('secret-img-drop-zone', 'secret-image-input', f => {
        if (!f.type.match(/image\/.*/)) {
            showToast('Please select a valid image.', 'error');
            return;
        }
        const reader = new FileReader();
        reader.onload = e => document.getElementById('secret-img-preview').src = e.target.result;
        reader.readAsDataURL(f);
        document.getElementById('secret-img-filename').textContent = f.name;
        show('secret-img-step-2');
        hide('secret-img-drop-zone');
    });

    document.getElementById('clear-secret-img')?.addEventListener('click', () => {
        document.getElementById('secret-image-input').value = '';
        show('secret-img-drop-zone');
        hide('secret-img-step-2');
    });

    document.querySelectorAll('input[name="secret_type"]').forEach(r => {
        r.addEventListener('change', () => {
            const t = r.value;
            toggleEl('secret-text-area', t === 'text');
            toggleEl('secret-image-area', t === 'image');
            toggleEl('secret-3d-area', t === '3d');
        });
    });

    const _zone3d = document.getElementById('secret-3d-drop-zone');
    if (_zone3d) {
        function _pick3dFile() {
            const tmp = document.createElement('input');
            tmp.type = 'file';
            tmp.onchange = e => {
                const f = e.target.files[0];
                if (!f) return;
                window._secret3dFile = f;
                document.getElementById('secret-3d-filename').textContent =  f.name;
                _zone3d.style.borderColor = 'var(--accent)';
            };
            tmp.click();
        }
        _zone3d.addEventListener('click', _pick3dFile);
        _zone3d.addEventListener('dragover', e => {
            e.preventDefault();
            _zone3d.classList.add('dragover');
        });
        _zone3d.addEventListener('dragleave', () => _zone3d.classList.remove('dragover'));
        _zone3d.addEventListener('drop', e => {
            e.preventDefault();
            _zone3d.classList.remove('dragover');
            const f = e.dataTransfer.files[0];
            if (!f) return;
            window._secret3dFile = f;
            document.getElementById('secret-3d-filename').textContent =  f.name;
            _zone3d.style.borderColor = 'var(--accent)';
        });
    }

    document.getElementById('btn-hide')?.addEventListener('click', async () => {
        if (!coverFile) {
            showToast('Please upload a cover image.', 'error');
            return;
        }
        const password = document.getElementById('aes-password')?.value.trim();
        let strong = /^(?=.*[A-Z])(?=.*[0-9])(?=.*[@$!%*?&]).{8,}$/;
        if (!strong.test(password)) {
            showToast('Use strong password (8+ chars, uppercase, number, special char)', 'error');
            return;
        }

        const secretType = document.querySelector('input[name="secret_type"]:checked')?.value || 'text';
        const coverMode = document.querySelector('input[name="cover_mode"]:checked')?.value || 'Universal';

        const fd = new FormData();
        fd.append('cover_image', coverFile);
        fd.append('password', password);
        fd.append('secret_type', secretType);
        fd.append('cover_mode', coverMode);

        if (secretType === 'text') {
            const txt = document.getElementById('secret-text')?.value.trim();
            if (!txt) {
                showToast('Please enter a secret message.', 'error');
                return;
            }
            fd.append('secret_text', txt);
        } else if (secretType === 'image') {
            const f = document.getElementById('secret-image-input')?.files[0];
            if (!f) {
                showToast('Please select a secret image.', 'error');
                return;
            }
            fd.append('secret_image', f);
        } else if (secretType === '3d') {
            const f = window._secret3dFile || document.getElementById('secret-3d-input')?.files[0];
            if (!f) {
                showToast('Please select or drop a 3D data file.', 'error');
                return;
            }
            fd.append('secret_3d', f);
        }

        setLoading('btn-hide', true);
        try {
            const resp = await fetch('/hide/process', {
                method: 'POST',
                body: fd
            });
            const data = await resp.json();
            if (data.error) {
                showToast(data.error, 'error');
                return;
            }

            document.getElementById('result-stego-img').src = data.stego_image || '';
            document.getElementById('metric-cover-size').textContent = data.cover_size || '—';
            document.getElementById('metric-secret-size').textContent = data.secret_size || '—';
            document.getElementById('metric-psnr').textContent = data.psnr ? (data.psnr + ' dB') : '—';
            document.getElementById('metric-ssim').textContent = data.ssim || '—';
            document.getElementById('metric-robust').textContent = data.robustness || '—';
            document.getElementById('model-badge-text').textContent = data.model_used || '—';

            const dlImg = document.getElementById('download-stego');
            const dl3d = document.getElementById('download-stego-3d');

            if (data.cover_type === 'image') {
                dlImg.href = data.stego_image;
                dlImg.download = data.stego_filename || 'stego.png';
                dlImg.style.display = 'inline-flex';
                dl3d.style.display = 'none';
            } else {
                window._stego3dUrl = data.stego_3d_url;
                window._stego3dFilename = data.stego_filename || ('stego.' + data.stego_ext);
                dlImg.style.display = 'none';
                dl3d.style.display = 'inline-flex';
                document.getElementById('result-stego-img').style.display = 'none';
            }
            show('hide-result');
            document.getElementById('hide-result').scrollIntoView({ behavior: 'smooth' });
        } catch (e) {
            showToast('Network error: ' + e.message, 'error');
        } finally {
            setLoading('btn-hide', false);
        }
    });

    document.getElementById('aes-password')?.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') document.getElementById('btn-hide')?.click();
    });
    document.getElementById('secret-text')?.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && e.ctrlKey) document.getElementById('btn-hide')?.click();
    });
})();

(function initExtractPage() {
    if (!document.getElementById('extract-form')) return;

    let stegoFile = null;

    setupDragDrop('stego-drop-zone', 'stego-file-input', f => {
        stegoFile = f;
        document.getElementById('stego-filename').textContent = f.name;
        const reader = new FileReader();
        reader.onload = e => document.getElementById('stego-preview').src = e.target.result;
        reader.readAsDataURL(f);
        show('stego-step-2');
        hide('stego-drop-zone');
        hide('extract-result');
    });

    document.getElementById('clear-stego')?.addEventListener('click', () => {
        stegoFile = null;
        document.getElementById('stego-file-input').value = '';
        show('stego-drop-zone');
        hide('stego-step-2');
        hide('extract-result');
    });

    document.getElementById('btn-extract')?.addEventListener('click', async () => {
        if (!stegoFile) {
            showToast('Please upload a stego image.', 'error');
            return;
        }
        const password = document.getElementById('extract-password')?.value.trim();
        let strong = /^(?=.*[A-Z])(?=.*[0-9])(?=.*[@$!%*?&]).{8,}$/;
        if (!strong.test(password)) {
            showToast('❌ Use strong password (8+ chars, uppercase, number, special char)', 'error');
            return;
        }

        const fd = new FormData();
        fd.append('stego_image', stegoFile);
        fd.append('password', password);

        setLoading('btn-extract', true);
        try {
            const resp = await fetch('/extract/process', {
                method: 'POST',
                body: fd
            });
            const data = await resp.json();
            if (data.error) {
                showToast(data.error, 'error');
                return;
            }

            const result = data.result;
            const textOut = document.getElementById('decoded-message');
            const imgOut = document.getElementById('decoded-image');

            hide('result-type-text');
            hide('result-type-image');
            hide('result-type-3d');

            if (result.type === 'text') {
                textOut.textContent = result.content;
                show('result-type-text');
            } else if (result.type === 'image') {
                imgOut.src = result.content;
                show('result-type-image');
            } else {
                document.getElementById('decoded-3d-info').textContent = result.content;
                window._3dData = { url: result.download_url, ext: result.ext };
                show('result-type-3d');
            }
            show('extract-result');
            document.getElementById('extract-result').scrollIntoView({ behavior: 'smooth' });
        } catch (e) {
            showToast('Network error: ' + e.message, 'error');
        } finally {
            setLoading('btn-extract', false);
        }
    });

    document.getElementById('extract-password')?.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') document.getElementById('btn-extract')?.click();
    });
})();

function show(id) { document.getElementById(id)?.classList.remove('hidden'); }
function hide(id) { document.getElementById(id)?.classList.add('hidden'); }
function toggleEl(id, vis) { vis ? show(id) : hide(id); }

function setLoading(btnId, loading) {
    const btn = document.getElementById(btnId);
    if (!btn) return;
    if (loading) {
        btn._original = btn.innerHTML;
        btn.innerHTML = '<span class="spinner"></span><span>Processing…</span>';
        btn.disabled = true;
    } else {
        btn.innerHTML = btn._original || btn.innerHTML;
        btn.disabled = false;
    }
}

function showToast(msg, type = 'info') {
    const alertContainer = document.getElementById('stego-alert-container');
    if (alertContainer) {
        alertContainer.innerHTML = '';
        
        const alertEl = document.createElement('div');
        alertEl.className = `stego-alert ${type}`;
        
        let iconHtml = '';
        if (type === 'error') {
            iconHtml = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#ef4444" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="flex-shrink:0;"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line></svg>`;
        } else if (type === 'success') {
            iconHtml = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#39FF14" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="flex-shrink:0;"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline></svg>`;
        } else {
            iconHtml = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#00f3ff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="flex-shrink:0;"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="16" x2="12" y2="12"></line><line x1="12" y1="8" x2="12.01" y2="8"></line></svg>`;
        }
        
        alertEl.innerHTML = `
            <div class="stego-alert-content">
                ${iconHtml}
                <span>${msg}</span>
            </div>
            <button type="button" class="stego-alert-close" aria-label="Dismiss alert">&times;</button>
        `;
        
        const dismissAlert = (e) => {
            if (!alertEl.contains(e.target)) {
                cleanupAndRemove();
            }
        };

        const cleanupAndRemove = () => {
            alertEl.style.opacity = '0';
            alertEl.style.transform = 'translateY(-10px)';
            setTimeout(() => {
                alertEl.remove();
            }, 300);
            document.removeEventListener('click', dismissAlert);
        };

        alertEl.querySelector('.stego-alert-close').addEventListener('click', () => {
            cleanupAndRemove();
        });
        
        alertContainer.appendChild(alertEl);
        
        setTimeout(() => {
            if (alertEl.parentNode) {
                cleanupAndRemove();
            }
        }, 3000);
        
        setTimeout(() => {
            document.addEventListener('click', dismissAlert);
        }, 100);
        
        return;
    }

    let container = document.querySelector('.flash-container');
    if (!container) {
        container = document.createElement('div');
        container.className = 'flash-container';
        container.style.cssText = 'position:fixed; top:20px; right:20px; z-index:99999; display:flex; flex-direction:column; gap:10px; max-width:320px;';
        document.body.appendChild(container);
    }

    const color     = type === 'error'   ? '#ef4444'
                    : type === 'success' ? '#39FF14'
                    : '#00f3ff';
    const bg        = type === 'error'   ? 'rgba(239, 68, 68, 0.1)'
                    : type === 'success' ? 'rgba(57, 255, 20, 0.1)'
                    : 'rgba(0, 243, 255, 0.1)';

    const el = document.createElement('div');
    el.style.cssText = `
        background: ${bg};
        border-left: 4px solid ${color};
        border-radius: 6px;
        padding: 12px 16px;
        color: rgba(255,255,255,0.9);
        font-size: 0.85rem;
        letter-spacing: normal;
        backdrop-filter: blur(8px);
        box-shadow: 0 4px 16px rgba(0,0,0,0.4);
        opacity: 1;
        transition: opacity 0.4s ease, transform 0.4s ease;
        transform: translateX(0);
        font-family: system-ui, -apple-system, sans-serif;
        line-height: 1.4;
    `;
    el.textContent = msg;
    container.appendChild(el);

    setTimeout(() => {
        el.style.opacity = '0';
        el.style.transform = 'translateX(20px)';
        setTimeout(() => el.remove(), 400);
    }, 4000);
}


document.getElementById('btn-share')?.addEventListener('click', async () => {
    const shareUrl = document.getElementById('download-stego')?.href || document.getElementById('result-stego-img')?.src;
    if (!shareUrl) { showToast('No stego image found.', 'error'); return; }

    document.getElementById('share-menu-popup')?.remove();
    const menu = document.createElement('div');
    menu.id = 'share-menu-popup';
    Object.assign(menu.style, {
        position:'fixed', bottom:'80px', right:'24px', zIndex:'9999',
        background:'#0d1117', border:'1px solid rgba(0,243,255,0.25)',
        borderRadius:'14px', padding:'10px', display:'flex',
        flexDirection:'column', gap:'8px',
        boxShadow:'0 8px 32px rgba(0,0,0,0.6)', minWidth:'230px'
    });

    function makeBtn(iconHtml, label, badge, hoverColor, clickFn) {
        const btn = document.createElement('button');
        Object.assign(btn.style, {
            display:'flex', alignItems:'center', gap:'10px',
            padding:'10px 14px', borderRadius:'10px', border:'none',
            background:'rgba(255,255,255,0.05)', color:'#fff',
            cursor:'pointer', fontSize:'0.9rem', width:'100%', textAlign:'left'
        });
        btn.innerHTML = iconHtml + '<span>' + label + '</span><small style="color:rgba(255,255,255,0.4);margin-left:auto">' + badge + '</small>';
        btn.onmouseenter = () => btn.style.background = hoverColor;
        btn.onmouseleave = () => btn.style.background = 'rgba(255,255,255,0.05)';
        btn.onclick = clickFn;
        return btn;
    }

    const tgIcon = '<svg width="20" height="20" viewBox="0 0 24 24" fill="#29b6f6"><path d="M9.78 18.65l.28-4.23 7.68-6.92c.34-.31-.07-.46-.52-.19L7.74 13.3 3.64 12c-.88-.25-.89-.86.2-1.3l15.97-6.16c.73-.33 1.43.18 1.15 1.3l-2.72 12.81c-.19.91-.74 1.13-1.5.71L12.6 16.3l-1.99 1.93c-.23.23-.42.42-.83.42z"/></svg>';
    menu.appendChild(makeBtn(tgIcon, 'Telegram', 'Lossless', 'rgba(41,182,246,0.15)', () => {
        window.open('https://t.me/share/url?url=' + encodeURIComponent(window.location.origin), '_blank');
        showToast('Send PNG as Document (not photo) in Telegram!', 'info');
        menu.remove();
    }));

    const mailIcon = '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#4ade80" stroke-width="2"><rect x="2" y="4" width="20" height="16" rx="2"/><polyline points="2,4 12,13 22,4"/></svg>';
    menu.appendChild(makeBtn(mailIcon, 'Email', 'Lossless', 'rgba(74,222,128,0.1)', () => {
        const s = encodeURIComponent('Secret - AI Steganography');
        const b = encodeURIComponent('Secret hidden in attached PNG. Upload it to AI Steganography to reveal!');
        window.open('mailto:?subject=' + s + '&body=' + b, '_blank');
        showToast('Attach the downloaded PNG to your email!', 'info');
        menu.remove();
    }));

    const moreIcon = '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#a78bfa" stroke-width="2"><circle cx="18" cy="5" r="3"/><circle cx="6" cy="12" r="3"/><circle cx="18" cy="19" r="3"/><line x1="8.59" y1="13.51" x2="15.42" y2="17.49"/><line x1="15.41" y1="6.51" x2="8.59" y2="10.49"/></svg>';
    menu.appendChild(makeBtn(moreIcon, 'More Options', 'Mobile', 'rgba(167,139,250,0.1)', async () => {
        try {
            const resp = await fetch(shareUrl);
            const blob = await resp.blob();
            const file = new File([blob], 'stego_secret.png', { type: 'image/png' });
            if (navigator.canShare && navigator.canShare({ files: [file] })) {
                await navigator.share({ title: 'Hidden Secret Image', files: [file] });
                showToast('Shared!', 'success');
            } else {
                navigator.clipboard.writeText(window.location.href);
                showToast('App link copied!', 'info');
            }
        } catch (e) { showToast('Sharing cancelled.', 'info'); }
        menu.remove();
    }));

    document.body.appendChild(menu);
    setTimeout(() => {
        document.addEventListener('click', function closeMenu(e) {
            if (!menu.contains(e.target) && e.target.id !== 'btn-share') {
                menu.remove();
                document.removeEventListener('click', closeMenu);
            }
        });
    }, 100);
});

document.addEventListener("DOMContentLoaded", () => {
    const reveals = document.querySelectorAll('.reveal');
    setTimeout(() => {
        reveals.forEach((el, index) => {
            setTimeout(() => el.classList.add('active'), index * 150);
        });
    }, 100);

    initInteractiveStars();
});

function initInteractiveStars() {
    const canvas = document.getElementById('star-canvas');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    let stars = [];
    let scrollPos = 0;

    function resize() {
        canvas.width = window.innerWidth;
        canvas.height = window.innerHeight;
    }
    window.addEventListener('resize', resize);
    window.addEventListener('scroll', () => {
        scrollPos = window.scrollY;
    });
    resize();

    class Star {
        constructor() {
            this.reset();
            this.x = Math.random() * canvas.width;
        }
        reset() {
            this.x = canvas.width + 50;
            this.initialY = (canvas.height * 0.35) + (Math.random() * (canvas.height * 0.3));
            this.y = this.initialY;
            const speedType = Math.random();
            if (speedType > 0.6) {
                this.speed = Math.random() * 8 + 4;
                this.length = Math.random() * 45 + 25;
                this.size = 1.3;
                this.isBright = true;
            } else {
                this.speed = Math.random() * 2 + 0.5;
                this.length = Math.random() * 8 + 4;
                this.size = 0.6;
                this.isBright = false;
            }
        }
        update() {
            this.x -= this.speed;
            this.y = this.initialY - (scrollPos * 0.5);
            let fadeOut = 1 - (scrollPos / 600);
            if (fadeOut < 0) fadeOut = 0;
            let centerOpacity = 1 - (Math.abs(this.y - canvas.height / 2) / (canvas.height / 2.5));
            this.currentOpacity = centerOpacity * fadeOut;
            if (this.x < -100) this.reset();
        }
        draw() {
            if (this.currentOpacity <= 0) return;
            if (this.isBright) {
                ctx.shadowBlur = 12;
                ctx.shadowColor = '#39FF14';
            }
            ctx.strokeStyle = `rgba(57, 255, 20, ${this.currentOpacity})`;
            ctx.lineWidth = this.size;
            ctx.lineCap = 'round';
            ctx.beginPath();
            ctx.moveTo(this.x, this.y);
            ctx.lineTo(this.x + this.length, this.y);
            ctx.stroke();
            ctx.shadowBlur = 0;
        }
    }
    for (let i = 0; i < 25; i++) stars.push(new Star());

    function animate() {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        stars.forEach(star => {
            star.update();
            star.draw();
        });
        requestAnimationFrame(animate);
    }
    animate();
}

function downloadStego3D() {
    const url = window._stego3dUrl;
    const fname = window._stego3dFilename || 'stego_3d.bin';
    if (!url) {
        showToast('No stego 3D data available.', 'error');
        return;
    }
    const a = document.createElement('a');
    a.href = url;
    a.download = fname;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    showToast('3D stego file downloaded!', 'info');
}