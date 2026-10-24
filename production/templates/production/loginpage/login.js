const submit = async (event) => {
    event.preventDefault();
    const form = event.target;
    const formData = new FormData(form);
    console.log('Submitting email:', formData.get('email'));
    try {
        const response = await fetch(form.action, {
            method: 'POST',
            body: formData,
            headers: { 'X-Requested-With': 'XMLHttpRequest' }
        });
        const data = await response.json();
        console.log('Response:', data);
        if (data.success) {
            window.location.href = data.redirect || '/production/';
        } else {
            console.log(`error message: ${data.error || 'Login failed'}`);
            let alertBox = document.getElementById('loginFlashAlert');
            if (!alertBox) {
                alertBox = document.createElement('div');
                alertBox.id = 'loginFlashAlert';
                alertBox.className = 'flash-alert flash-danger';
                form.parentNode.insertBefore(alertBox, form);
            }
            alertBox.innerHTML = '<i class="fas fa-exclamation-circle"></i><span>' + (data.error || 'Login failed') + '</span>';
            alertBox.style.display = 'flex';
        }
    } catch (error) {
        console.log(`error message: ${error.message}`);
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
});
