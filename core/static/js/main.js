 document.addEventListener('DOMContentLoaded', function() {
    // スプラッシュスクリーンの制御
    const splashScreen = document.getElementById('splash-screen');
    if (splashScreen) {
        const splashDuration = 2000;
        setTimeout(() => {
            splashScreen.classList.add('hidden');
            setTimeout(() => {
                splashScreen.style.display = 'none';
            }, 800);
        }, splashDuration);
    }

    // ハンバーガーメニューの制御
    const hamburgerIcon = document.querySelector('.hamburger-icon');
    const menuItems = document.getElementById('menu-items');
    
    if (hamburgerIcon && menuItems) {
        hamburgerIcon.addEventListener('click', function() {
            if (menuItems.style.display === "block") {
                menuItems.style.display = "none";
            } else {
                menuItems.style.display = "block";
            }
        });
    }

    // パスワード表示切り替え
    const togglePasswordButtons = document.querySelectorAll('.toggle-password');
    togglePasswordButtons.forEach(button => {
        button.addEventListener('click', function() {
            const fieldId = this.getAttribute('data-target');
            const passwordField = document.getElementById(fieldId);
            if (passwordField) {
                if (passwordField.type === "password") {
                    passwordField.type = "text";
                    this.textContent = "非表示";
                } else {
                    passwordField.type = "password";
                    this.textContent = "表示";
                }
            }
        });
    });

    // 管理画面: 行クリックで遷移 (tr[data-href])
    const clickableRows = document.querySelectorAll('tr[data-href]');
    clickableRows.forEach(row => {
        row.style.cursor = 'pointer'; // CSSで設定がない場合の保険
        row.addEventListener('click', (e) => {
            // リンクやボタンがクリックされた場合は遷移しない
            if (!e.target.closest('a') && !e.target.closest('button') && !e.target.closest('input')) {
                location.href = row.dataset.href;
            }
        });
    });

    // 確認ダイアログ (class="js-confirm" data-confirm-message="...")
    const confirmButtons = document.querySelectorAll('.js-confirm');
    confirmButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            const message = this.getAttribute('data-confirm-message') || '本当に実行しますか？';
            if (!confirm(message)) {
                e.preventDefault();
            }
        });
    });
});
