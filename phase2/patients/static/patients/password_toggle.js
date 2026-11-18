document.addEventListener('click', (event) => {
    const target = event.target instanceof Element
        ? event.target.closest('.password-visibility-toggle')
        : null;

    if (!(target instanceof HTMLButtonElement)) {
        return;
    }

    const passwordInput = document.getElementById(target.dataset.passwordToggle);
    if (!(passwordInput instanceof HTMLInputElement)) {
        return;
    }

    const showPassword = passwordInput.type === 'password';
    passwordInput.type = showPassword ? 'text' : 'password';
    target.textContent = showPassword ? 'Hide password' : 'Show password';
    target.setAttribute('aria-label', showPassword ? 'Hide password' : 'Show password');
    target.setAttribute('aria-pressed', String(showPassword));
});
