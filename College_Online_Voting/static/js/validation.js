// CIVITAS — Client-side Validation

document.addEventListener('DOMContentLoaded', () => {
    // Password match indicator
    const pw = document.getElementById('password');
    const cpw = document.getElementById('confirm_password');
    const msg = document.getElementById('password-match-msg');

    if (pw && cpw && msg) {
        const check = () => {
            if (!cpw.value) { msg.style.display = 'none'; return; }
            msg.style.display = 'block';
            if (pw.value === cpw.value) {
                msg.textContent = '✓ Passwords match';
                msg.style.color = 'var(--success)';
                cpw.style.borderColor = 'var(--success)';
            } else {
                msg.textContent = '✗ Passwords do not match';
                msg.style.color = 'var(--danger)';
                cpw.style.borderColor = 'var(--danger)';
            }
        };
        pw.addEventListener('input', check);
        cpw.addEventListener('input', check);
    }

    // Auto-dismiss alerts
    document.querySelectorAll('.alert').forEach(alert => {
        setTimeout(() => {
            alert.style.transition = 'opacity 0.5s';
            alert.style.opacity = '0';
            setTimeout(() => alert.remove(), 500);
        }, 6000);
    });

    // Form loading state
    document.querySelectorAll('form').forEach(form => {
        form.addEventListener('submit', e => {
            const btn = form.querySelector('button[type="submit"]');
            if (btn && !btn.disabled) {
                const original = btn.textContent;
                // Defer disabling to allow form submission to proceed
                setTimeout(() => {
                    btn.disabled = true;
                    btn.textContent = 'Processing…';
                }, 10);
                setTimeout(() => {
                    if (btn) {
                        btn.disabled = false;
                        btn.textContent = original;
                    }
                }, 8000);
            }
        });
    });
});