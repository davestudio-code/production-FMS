let countdownTimer = null;

function startBlockCountdown(remainingSeconds, alertBox) {
    if (countdownTimer) clearInterval(countdownTimer);
    let currentSec = remainingSeconds;
    const update = () => {
        if (currentSec <= 0) {
            clearInterval(countdownTimer);
            alertBox.style.cssText = 'background: rgba(94, 114, 69, 0.15); border: 1.5px solid #5a7442; color: #354a24; padding: 12px 14px; border-radius: 8px; margin-bottom: 16px; display: flex; align-items: flex-start; gap: 10px;';
            alertBox.innerHTML = '<i class="fas fa-check-circle" style="font-size: 16px; margin-top: 3px; flex-shrink: 0;"></i><div><b style="display: block; font-size: 13.5px; margin-bottom: 3px;">Block Expired</b><span style="font-size: 12.5px; line-height: 1.4;">You may now try again.</span></div>';
            return;
        }
        alertBox.style.cssText = 'background: rgba(181, 143, 85, 0.15); border: 1.5px solid #8e622a; color: #8e622a; padding: 12px 14px; border-radius: 8px; margin-bottom: 16px; display: flex; align-items: flex-start; gap: 10px;';
        alertBox.innerHTML = '<i class="fas fa-clock" style="font-size: 16px; margin-top: 3px; flex-shrink: 0;"></i><div><b style="display: block; font-size: 13.5px; margin-bottom: 3px;">Temporary Security Block</b><span style="font-size: 12.5px; line-height: 1.4;">Too many failed attempts. Try again in ' + currentSec + 's.</span></div>';
        currentSec--;
    };
    update();
    countdownTimer = setInterval(update, 1000);
}

const submit = async (event) => {
    event.preventDefault();
    const form = event.target;
    const emailInput = form.querySelector('#loginEmail');
    const email = (emailInput ? emailInput.value : '').trim();
    const emailPattern = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;

    if (!email || !emailPattern.test(email)) {
        let alertBox = document.getElementById('loginFlashAlert');
        if (!alertBox) {
            alertBox = document.createElement('div');
            alertBox.id = 'loginFlashAlert';
            form.parentNode.insertBefore(alertBox, form);
        }
        if (countdownTimer) clearInterval(countdownTimer);
        alertBox.className = 'flash-alert flash-danger';
        alertBox.style.cssText = '';
        alertBox.innerHTML = '<i class="fas fa-exclamation-circle"></i><span>Please enter a valid email address.</span>';
        alertBox.style.display = 'flex';
        if (emailInput) {
            emailInput.focus();
        }
        return;
    }

    const submitBtn = form.querySelector('.btn-submit');
    const formData = new FormData(form);
    let isSuccess = false;
    if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<span>Please wait...</span><i class="fas fa-circle-notch fa-spin"></i>';
    }

    try {
        const response = await fetch(form.action, {
            method: 'POST',
            body: formData,
            headers: { 'X-Requested-With': 'XMLHttpRequest' }
        });
        const data = await response.json();
        if (data.success) {
            isSuccess = true;
            window.location.href = data.redirect || '/production/';
            return;
        }

        let alertBox = document.getElementById('loginFlashAlert');
        if (!alertBox) {
            alertBox = document.createElement('div');
            alertBox.id = 'loginFlashAlert';
            form.parentNode.insertBefore(alertBox, form);
        }

        const sec = data.security;
        if (sec && (sec.status === 'banned' || sec.action === 'banned')) {
            if (countdownTimer) clearInterval(countdownTimer);
            alertBox.style.cssText = 'background: rgba(186, 73, 58, 0.12); border: 1.5px solid #ba493a; color: #ba493a; padding: 12px 14px; border-radius: 8px; margin-bottom: 16px; display: flex; align-items: flex-start; gap: 10px;';
            alertBox.innerHTML = '<i class="fas fa-ban" style="font-size: 16px; margin-top: 3px; flex-shrink: 0;"></i><div><b style="display: block; font-size: 13.5px; margin-bottom: 3px;">Access Restricted &middot; IP Banned for 1 Day</b><span style="font-size: 12.5px; line-height: 1.4;">' + (data.error || 'Your IP address has been banned for 1 day.') + '</span></div>';
        } else if (sec && (sec.status === 'blocked' || sec.action === 'blocked')) {
            startBlockCountdown(sec.remaining_seconds || 60, alertBox);
        } else {
            if (countdownTimer) clearInterval(countdownTimer);
            alertBox.className = 'flash-alert flash-danger';
            alertBox.style.cssText = '';
            alertBox.innerHTML = '<i class="fas fa-exclamation-circle"></i><span>' + (data.error || 'Login failed') + '</span>';
        }
        alertBox.style.display = 'flex';
    } catch (error) {
        console.log(`error message: ${error.message}`);
    } finally {
        if (submitBtn && !isSuccess) {
            submitBtn.disabled = false;
            submitBtn.innerHTML = '<span>Login</span><i class="fas fa-arrow-right"></i>';
        }
    }
};

document.addEventListener('DOMContentLoaded', function () {
    const loginForm = document.getElementById('loginForm');
    if (loginForm) {
        loginForm.addEventListener('submit', submit);
    }

    const toggleBtn = document.getElementById('togglePasswordBtn');
    const pwdInput = document.getElementById('loginPassword');
    const eyeIcon = document.getElementById('togglePasswordIcon');

    if (toggleBtn && pwdInput && eyeIcon) {
        toggleBtn.addEventListener('click', function () {
            if (pwdInput.type === 'password') {
                pwdInput.type = 'text';
                eyeIcon.classList.remove('fa-eye');
                eyeIcon.classList.add('fa-eye-slash');
            } else {
                pwdInput.type = 'password';
                eyeIcon.classList.remove('fa-eye-slash');
                eyeIcon.classList.add('fa-eye');
            }
        });
    }

    const forgotLink = document.getElementById('forgotPasswordLink');
    if (forgotLink && loginForm) {
        forgotLink.addEventListener('click', function (e) {
            e.preventDefault();
            let alertBox = document.getElementById('loginFlashAlert');
            if (!alertBox) {
                alertBox = document.createElement('div');
                alertBox.id = 'loginFlashAlert';
                loginForm.parentNode.insertBefore(alertBox, loginForm);
            }
            if (countdownTimer) clearInterval(countdownTimer);
            alertBox.className = 'flash-alert flash-info';
            alertBox.style.cssText = 'background: rgba(94, 114, 69, 0.12); border: 1.5px solid #5a7442; color: #354a24; padding: 12px 14px; border-radius: 8px; margin-bottom: 16px; display: flex; align-items: flex-start; gap: 10px;';
            alertBox.innerHTML = '<i class="fas fa-info-circle" style="font-size: 16px; margin-top: 3px; flex-shrink: 0;"></i><div><b style="display: block; font-size: 13.5px; margin-bottom: 2px;">Password Recovery Notice</b><span style="font-size: 12.5px; line-height: 1.4;">Automated password recovery is currently under development. Please contact your IT or HR Administrator to reset your credentials.</span></div>';
        });
    }
});
