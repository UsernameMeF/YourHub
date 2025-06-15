// static/js/notifications.js

document.addEventListener('DOMContentLoaded', function() {
    console.log("notifications.js loaded.");

    const isAuthenticated = document.querySelector('meta[name="user-authenticated"]') !== null;
    const currentUserIdMeta = document.querySelector('meta[name="user-id"]');
    const currentUserId = currentUserIdMeta ? parseInt(currentUserIdMeta.content) : null;

    if (!isAuthenticated) {
        console.log("User not authenticated, skipping WebSocket connection for notifications.");
        return;
    }

    const notificationSocket = new WebSocket(
        'ws://127.0.0.1:8001/ws/notifications/'
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

            if (notification.play_sound && notification.sound_file) {
                const audio = new Audio(`/static/sounds/${notification.sound_file}`);
                audio.volume = notification.volume || 0.7;
                audio.play().catch(error => {
                    console.error("Error playing sound:", error);
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
        setTimeout(function() {
            console.log("Attempting to reconnect Notification WebSocket...");
            new WebSocket('ws://' + window.location.host + '/ws/notifications/');
        }, 3000);
    };

    notificationSocket.onerror = function(err) {
        console.error('Notification WebSocket error:', err);
    };
});

function showToastNotification(message, url) {
    console.log(`Toast: ${message} - URL: ${url}`);
}
