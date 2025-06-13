// static/js/notification_list_infinite_scroll.js

document.addEventListener('DOMContentLoaded', function() {
    const notificationListUl = document.querySelector('.notification-list');
    const loadingSpinner = document.getElementById('loading-spinner');
    const loadMoreButton = document.getElementById('load-more-button');
    const noNotificationsMessage = document.querySelector('.no-notifications-message');

    if (!notificationListUl) {
        console.log("Not on the notification list page, skipping infinite scroll setup.");
        return;
    }

    let currentPage = parseInt(notificationListUl.dataset.page) || 1;
    let hasNextPage = notificationListUl.dataset.hasNext === 'True'; // Преобразуем строку в булево
    let isLoading = false;

    // Функция для загрузки уведомлений
    function loadNotifications() {
        if (isLoading || !hasNextPage) {
            return;
        }
        isLoading = true;
        if (loadingSpinner) loadingSpinner.style.display = 'block';
        if (loadMoreButton) loadMoreButton.style.display = 'none';

        currentPage++;
        const url = `/notifications/?page=${currentPage}`; // Используем ваш текущий URL страницы уведомлений

        fetch(url, {
            headers: {
                'X-Requested-With': 'XMLHttpRequest' // Важно для Django, чтобы определить AJAX-запрос
            }
        })
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            if (notificationListUl) {
                notificationListUl.insertAdjacentHTML('beforeend', data.notifications_html);
                hasNextPage = data.has_next_page;
                // Перепривязываем слушатели для новых элементов
                attachMarkAsReadListeners(); 
            }
            if (!hasNextPage && loadMoreButton) {
                loadMoreButton.style.display = 'none';
            }
            if (!hasNextPage && loadingSpinner) {
                loadingSpinner.style.display = 'none';
            }
            // Если после загрузки новых уведомлений все еще нет ни одного, показываем сообщение
            if (notificationListUl.children.length === 0 && noNotificationsMessage) {
                noNotificationsMessage.style.display = 'block';
            } else if (notificationListUl.children.length > 0 && noNotificationsMessage) {
                 noNotificationsMessage.style.display = 'none';
            }

        })
        .catch(error => {
            console.error('Error loading more notifications:', error);
            if (loadingSpinner) loadingSpinner.style.display = 'none';
            if (loadMoreButton && hasNextPage) loadMoreButton.style.display = 'block'; // Показать кнопку при ошибке
        })
        .finally(() => {
            isLoading = false;
            if (loadingSpinner) loadingSpinner.style.display = 'none';
        });
    }

    // Intersection Observer для бесконечной прокрутки
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting && hasNextPage && !isLoading) {
                loadNotifications();
            }
        });
    }, {
        root: null, // viewport
        rootMargin: '0px',
        threshold: 0.1 // Когда 10% элемента видно
    });

    // Если есть уведомления, начинаем наблюдать за последним элементом
    if (notificationListUl && notificationListUl.lastElementChild) {
        observer.observe(notificationListUl.lastElementChild);
    } else if (loadMoreButton) {
        // Если нет уведомлений или observer не нужен, но есть кнопка, показываем ее, если есть следующая страница
        if (hasNextPage) loadMoreButton.style.display = 'block';
    }

    // Если нужна кнопка "Загрузить еще" как запасной вариант или основной:
    if (loadMoreButton) {
        loadMoreButton.addEventListener('click', loadNotifications);
    }

    // Перемещаем функции markNotificationAsRead и updateGlobalUnreadNotificationCount
    // сюда или убедитесь, что они доступны глобально
    // Я уже перенес их в notifications.js и сделал updateGlobalUnreadNotificationCount глобальной.
    // Убедитесь, что attachMarkAsReadListeners также вызывается в notifications.js и доступна здесь.
    // Если она в notifications.js, то она уже глобальна.
    // attachMarkAsReadListeners() - вызывается в notifications.js при DOMContentLoaded и после добавления новых уведомлений.
});