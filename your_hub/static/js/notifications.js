// static/js/notifications.js

document.addEventListener('DOMContentLoaded', function() {
    console.log("notifications.js loaded.");

    // Проверяем, авторизован ли пользователь.
    // Это можно сделать, передавая переменную из Django шаблона
    // или проверяя наличие элемента на странице, который виден только авторизованным.
    // Предполагаем, что есть какой-то элемент или переменная, указывающая на авторизацию.
    // Например, можно добавить <meta name="user-authenticated" content="true"> в head base.html
    // и проверять его наличие.
    const isAuthenticated = document.querySelector('meta[name="user-authenticated"]') !== null;
    const currentUserIdMeta = document.querySelector('meta[name="user-id"]');
    const currentUserId = currentUserIdMeta ? parseInt(currentUserIdMeta.content) : null;

    if (!isAuthenticated) {
        console.log("User not authenticated, skipping WebSocket connection for notifications.");
        return; // Не пытаемся подключиться, если пользователь не авторизован
    }

    const notificationSocket = new WebSocket(
        'ws://127.0.0.1:8001/ws/notifications/' // Явно указываем IP и порт Daphne
    );

    notificationSocket.onopen = function(e) {
        console.log("Notification WebSocket connected successfully!");
    };

    notificationSocket.onmessage = function(e) {
        const data = JSON.parse(e.data);
        console.log("Received notification from WebSocket:", data);
    
        if (data.type === 'new_notification' && data.notification) {
            const notification = data.notification;
            console.log("Processing new notification:", notification);
    
            // 1. Проигрывание звука (если разрешено настройками и нужно)
            if (notification.play_sound && notification.sound_file) {
                const audio = new Audio(`/static/sounds/${notification.sound_file}`);
                audio.volume = notification.volume || 0.7;
                audio.play().catch(error => {
                    console.error("Error playing sound:", error);
                });
            }
    
            // 2. Обновление счетчика непрочитанных уведомлений на иконке
            const notificationCountElement = document.getElementById('notification-count');
            const notificationCountElement2 = document.getElementById('notification-count_2');
            if (notificationCountElement) {
                let currentCount = parseInt(notificationCountElement.textContent) || 0;
                notificationCountElement.textContent = currentCount + 1;
                notificationCountElement.style.display = 'inline-block'; // Показать, если был скрыт
            }
            if (notificationCountElement2) {
                let currentCount = parseInt(notificationCountElement2.textContent) || 0;
                notificationCountElement2.textContent = currentCount + 1;
                notificationCountElement2.style.display = 'inline-block'; // Показать, если был скрыт
            }
    
            // 3. Динамическое добавление уведомления на страницу, если пользователь находится на странице уведомлений
            const notificationListUl = document.querySelector('.notification-list');
            if (notificationListUl) { // Проверяем, существует ли на странице элемент списка уведомлений
                if (notification.id) { // Убедимся, что ID уведомления пришел
                    fetch(`/notifications/api/notification/${notification.id}/`)
                        .then(response => response.json())
                        .then(apiData => {
                            if (apiData.status === 'success' && apiData.notification_html) {
                                notificationListUl.insertAdjacentHTML('afterbegin', apiData.notification_html);
                                // Удалить сообщение "У вас пока нет уведомлений.", если оно было
                                const noNotificationsMessage = document.querySelector('.no-notifications-message');
                                if (noNotificationsMessage) {
                                    noNotificationsMessage.style.display = 'none';
                                }
                                // Перепривязать обработчики событий для новой кнопки "прочитано"
                                attachMarkAsReadListeners(); 
                            } else {
                                console.error('Failed to fetch new notification HTML:', apiData.message);
                            }
                        })
                        .catch(error => console.error('Error fetching new notification HTML:', error));
                } else {
                    console.warn("Received new notification via WebSocket without an ID. Cannot dynamically load HTML.");
                }
            }
        }
    };
    

    notificationSocket.onclose = function(e) {
        console.error('Notification WebSocket closed unexpectedly:', e);
        // Попытка переподключения через некоторое время
        setTimeout(function() {
            console.log("Attempting to reconnect Notification WebSocket...");
            // Можно добавить логику для предотвращения бесконечных попыток при постоянной ошибке
            // Например, увеличивать таймаут или ограничить количество попыток
            new WebSocket('ws://' + window.location.host + '/ws/notifications/');
        }, 3000); // Попытка переподключения через 3 секунды
    };

    notificationSocket.onerror = function(err) {
        console.error('Notification WebSocket error:', err);
    };
});

// Пример функции для отображения Toast-уведомлений (можете использовать свою библиотеку, например, Toastify-JS)
function showToastNotification(message, url) {
    // В реальной реализации вы бы использовали библиотеку типа Toastify-JS, SweetAlert, Bootstrap Toasts и т.п.
    console.log(`Toast: ${message} - URL: ${url}`);
    // Например, если у вас Toastify-JS
    /*
    Toastify({
        text: message,
        duration: 5000,
        close: true,
        gravity: "top",
        position: "right",
        backgroundColor: "linear-gradient(to right, #00b09b, #96c93d)",
        onClick: function(){
            if (url) window.location.href = url;
        }
    }).showToast();
    */
}