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
    let hasNextPage = notificationListUl.dataset.hasNext === 'True';
    let isLoading = false;

    function loadNotifications() {
        if (isLoading || !hasNextPage) {
            return;
        }
        isLoading = true;
        if (loadingSpinner) loadingSpinner.style.display = 'block';
        if (loadMoreButton) loadMoreButton.style.display = 'none';

        currentPage++;
        const url = `/notifications/?page=${currentPage}`;

        fetch(url, {
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
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
                attachMarkAsReadListeners();
            }
            if (!hasNextPage && loadMoreButton) {
                loadMoreButton.style.display = 'none';
            }
            if (!hasNextPage && loadingSpinner) {
                loadingSpinner.style.display = 'none';
            }
            if (notificationListUl.children.length === 0 && noNotificationsMessage) {
                noNotificationsMessage.style.display = 'block';
            } else if (notificationListUl.children.length > 0 && noNotificationsMessage) {
                noNotificationsMessage.style.display = 'none';
            }

        })
        .catch(error => {
            console.error('Error loading more notifications:', error);
            if (loadingSpinner) loadingSpinner.style.display = 'none';
            if (loadMoreButton && hasNextPage) loadMoreButton.style.display = 'block';
        })
        .finally(() => {
            isLoading = false;
            if (loadingSpinner) loadingSpinner.style.display = 'none';
        });
    }

    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting && hasNextPage && !isLoading) {
                loadNotifications();
            }
        });
    }, {
        root: null,
        rootMargin: '0px',
        threshold: 0.1
    });

    if (notificationListUl && notificationListUl.lastElementChild) {
        observer.observe(notificationListUl.lastElementChild);
    } else if (loadMoreButton) {
        if (hasNextPage) loadMoreButton.style.display = 'block';
    }

    if (loadMoreButton) {
        loadMoreButton.addEventListener('click', loadNotifications);
    }
});
