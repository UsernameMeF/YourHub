document.addEventListener('DOMContentLoaded', function() {
    const MAX_TOTAL_IMAGES = 5;
    const form = document.querySelector('form');
    const imageInputsWrapper = document.getElementById('image-inputs-wrapper');
    const addNewImageButton = document.getElementById('add-new-image-button');
    const existingImagesPreview = document.getElementById('existing-images-preview');
    const existingImageIdsToDeleteInput = document.getElementById('existing-image-ids-to-delete');

    let newFiles = [];
    let existingImages = [];
    let idsToDelete = [];

    if (existingImagesPreview && existingImageIdsToDeleteInput) {
        const postImagesJsonElement = document.getElementById('initial-images-data');
        if (postImagesJsonElement) {
            try {
                existingImages = JSON.parse(postImagesJsonElement.textContent || '[]');
            } catch (e) {
                console.error("Error parsing existing images JSON:", e);
            }
        }

        if (existingImageIdsToDeleteInput.value) {
            idsToDelete = existingImageIdsToDeleteInput.value.split(',').filter(id => id.trim());
        }

        existingImages = existingImages.filter(img => !idsToDelete.includes(String(img.id)));
    }

    function updateAddNewImageButtonVisibility() {
        const totalCurrentImages = newFiles.length + existingImages.length;
        if (totalCurrentImages >= MAX_TOTAL_IMAGES) {
            addNewImageButton.style.display = 'none';
        } else {
            addNewImageButton.style.display = 'inline-block';
        }
    }

    function createPreviewElement(src, type, id = null, file = null) {
        const previewWrapper = document.createElement('div');
        previewWrapper.classList.add('image-preview-item');

        const img = document.createElement('img');
        img.src = src;
        previewWrapper.appendChild(img);

        const removeButton = document.createElement('button');
        removeButton.type = 'button';
        removeButton.classList.add('remove-image-button');
        removeButton.innerHTML = '&times;';

        removeButton.addEventListener('click', function() {
            if (type === 'existing' && id !== null) {
                if (!idsToDelete.includes(String(id))) {
                    idsToDelete.push(String(id));
                }
                existingImageIdsToDeleteInput.value = idsToDelete.join(',');
                existingImages = existingImages.filter(img => img.id !== id);
            } else if (type === 'new' && file !== null) {
                newFiles = newFiles.filter(f => f !== file);
            }
            previewWrapper.remove();
            updateAddNewImageButtonVisibility();
            updateFileInputsForSubmit();
        });

        previewWrapper.appendChild(removeButton);

        if (type === 'existing' && existingImagesPreview) {
            existingImagesPreview.appendChild(previewWrapper);
        } else {
            imageInputsWrapper.appendChild(previewWrapper);
        }
    }

    function updateFileInputsForSubmit() {
        form.querySelectorAll('input[name="images"][type="file"]').forEach(input => input.remove());

        if (newFiles.length > 0) {
            const tempInput = document.createElement('input');
            tempInput.type = 'file';
            tempInput.name = 'images';
            tempInput.multiple = true;
            tempInput.style.display = 'none';

            const dataTransfer = new DataTransfer();
            newFiles.forEach(file => dataTransfer.items.add(file));
            tempInput.files = dataTransfer.files;

            form.appendChild(tempInput);
        }
    }

    if (addNewImageButton) {
        addNewImageButton.addEventListener('click', function() {
            if (newFiles.length + existingImages.length < MAX_TOTAL_IMAGES) {
                const fileInput = document.createElement('input');
                fileInput.type = 'file';
                fileInput.accept = 'image/*';
                fileInput.style.display = 'none';

                fileInput.addEventListener('change', function(event) {
                    const files = Array.from(event.target.files);
                    files.forEach(file => {
                        const fileSizeMB = file.size / (1024 * 1024);
                        if (fileSizeMB > 5) {
                            alert('Файл ' + file.name + ' слишком большой (макс. 5 МБ).');
                            return;
                        }
                        if (!['image/jpeg', 'image/png', 'image/gif', 'image/webp'].includes(file.type)) {
                            alert('Файл ' + file.name + ' имеет неподдерживаемый тип.');
                            return;
                        }

                        if (newFiles.length + existingImages.length < MAX_TOTAL_IMAGES) {
                            newFiles.push(file);
                            const reader = new FileReader();
                            reader.onload = function(e) {
                                createPreviewElement(e.target.result, 'new', null, file);
                                updateAddNewImageButtonVisibility();
                            };
                            reader.readAsDataURL(file);
                        } else {
                            alert(`Достигнут лимит в ${MAX_TOTAL_IMAGES} изображений.`);
                        }
                    });
                    event.target.value = '';
                });

                fileInput.click();
            } else {
                alert(`Достигнут лимит в ${MAX_TOTAL_IMAGES} изображений.`);
            }
        });
    }

    existingImages.forEach(img => createPreviewElement(img.image, 'existing', img.id));
    updateAddNewImageButtonVisibility();

    form.addEventListener('submit', function(event) {
        updateFileInputsForSubmit();
    });
});
