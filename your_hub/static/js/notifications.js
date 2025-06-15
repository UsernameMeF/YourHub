// static/js/notifications.js

document.addEventListener('DOMContentLoaded', function() {
    console.log("notifications.js завантажено."); // Translated

    const isAuthenticated = document.querySelector('meta[name="user-authenticated"]') !== null;
    const currentUserIdMeta = document.querySelector('meta[name="user-id"]');
    const currentUserId = currentUserIdMeta ? parseInt(currentUserIdMeta.content) : null;

    if (!isAuthenticated) {
        console.log("Користувач не автентифікований, пропускаємо з'єднання WebSocket для сповіщень."); // Translated
        return;
    }

    const notificationSocket = new WebSocket(
        'ws://127.0.0.1:8001/ws/notifications/'
    );

    notificationSocket.onopen = function(e) {
        console.log("WebSocket сповіщень успішно підключено!"); // Translated
    };

    notificationSocket.onmessage = function(e) {
        const data = JSON.parse(e.data);
        console.log("Отримано сповіщення від WebSocket:", data); // Translated

        if (data.type === 'new_notification' && data.notification) {
            const notification = data.notification;
            console.log("Обробка нового сповіщення:", notification); // Translated

            if (notification.play_sound && notification.sound_file) {
                const audio = new Audio(`/static/sounds/${notification.sound_file}`);
                audio.volume = notification.volume || 0.7;
                audio.play().catch(error => {
                    console.error("Помилка відтворення звуку:", error); // Translated
                });
            }

            const notificationCountElement = document.getElementById('notification-count');
            const notificationCountElement2 = document.getElementById('notification-count_2');
            if (notificationCountElement) {
                let currentCount = parseInt(notificationCountElement.textContent) || 0;
                notificationCountElement.textContent = currentCount + 1;
                notificationCountElement.style.display = 'inline-block';
            }
            if (notificationCountElement2) {
                let currentCount = parseInt(notificationCountElement2.textContent) || 0;
                notificationCountElement2.textContent = currentCount + 1;
                notificationCountElement2.style.display = 'inline-block';
            }

            const notificationListUl = document.querySelector('.notification-list');
            if (notificationListUl) {
                if (notification.id) {
                    fetch(`/notifications/api/notification/${notification.id}/`)
                        .then(response => response.json())
                        .then(apiData => {
                            if (apiData.status === 'success' && apiData.notification_html) {
                                notificationListUl.insertAdjacentHTML('afterbegin', apiData.notification_html);
                                const noNotificationsMessage = document.querySelector('.no-notifications-message');
                                if (noNotificationsMessage) {
                                    noNotificationsMessage.style.display = 'none';
                                }
                                // Припускаємо, що ця функція визначена в notification_list_infinite_scroll.js
                                // і відповідає за навішування обробників подій на нові елементи.
                                // Якщо її тут немає, вона буде undefined.
                                if (typeof attachMarkAsReadListeners === 'function') {
                                    attachMarkAsReadListeners(); 
                                }
                            } else {
                                console.error('Не вдалося отримати HTML нового сповіщення:', apiData.message); // Translated
                            }
                        })
                        .catch(error => console.error('Помилка отримання HTML нового сповіщення:', error)); // Translated
                } else {
                    console.warn("Отримано нове сповіщення через WebSocket без ID. Неможливо динамічно завантажити HTML."); // Translated
                }
            }
        }
    };

    notificationSocket.onclose = function(e) {
        console.error('WebSocket сповіщень неочікувано закрито:', e); // Translated
        setTimeout(function() {
            console.log("Спроба перепідключення WebSocket сповіщень..."); // Translated
            new WebSocket('ws://' + window.location.host + '/ws/notifications/');
        }, 3000);
    };

    notificationSocket.onerror = function(err) {
        console.error('Помилка WebSocket сповіщень:', err); // Translated
    };
});

function showToastNotification(message, url) {
    console.log(`Тост: ${message} - URL: ${url}`); // Translated
}