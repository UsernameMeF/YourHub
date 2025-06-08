import datetime
import json
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Count, OuterRef, Subquery, Max
from django.db import models
from django.http import JsonResponse, HttpResponseBadRequest # Импортируем JsonResponse и HttpResponseBadRequest
from django.views.decorators.http import require_POST # Для ограничения метода POST
from django.db import transaction # Для атомарности операций с БД

from .models import ChatRoom, ChatMessage, ChatAttachment
from django.contrib.auth import get_user_model

# Импортируем Channel Layer
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

# Create your views here.
User = get_user_model()


@login_required
def chat_list_view(request):
    chat_rooms = ChatRoom.objects.filter(participants=request.user).order_by('-created_at')

    for room in chat_rooms:
        room.last_message = ChatMessage.objects.filter(chat_room=room).order_by('-timestamp').first()

    context = {
        'chat_rooms': chat_rooms,
        'today_date': datetime.date.today(),
    }
    return render(request, 'chat/chat_list.html', context)


@login_required
def chat_room_view(request, room_id):
    chat_room = get_object_or_404(ChatRoom, id=room_id)

    if not chat_room.participants.filter(id=request.user.id).exists():
        return redirect('chat:chat_list')

    messages_initial_load = 50

    messages = chat_room.messages.order_by('-timestamp')[:messages_initial_load].select_related('sender').prefetch_related('attachments')
    messages = reversed(list(messages))

    context = {
        'chat_room': chat_room,
        'messages': messages,
        'current_user': request.user,
    }
    return render(request, 'chat/chat_room.html', context)


@login_required
def get_or_create_private_chat(request, other_user_id):
    """
    Находит или создает приватный чат между текущим пользователем и другим пользователем.
    Перенаправляет на страницу этого чата.
    """
    other_user = get_object_or_404(User, id=other_user_id)

    if request.user.id == other_user.id:
        print(f"DEBUG: Пользователь {request.user.username} пытается создать чат с самим собой. Перенаправление.")
        return redirect('users:profile', pk=request.user.id) # Проверьте это имя URL

    print(f"DEBUG: Текущий пользователь: {request.user.username} (ID: {request.user.id})")
    print(f"DEBUG: Другой пользователь: {other_user.username} (ID: {other_user.id})")

    possible_chats = ChatRoom.objects.annotate(num_participants=models.Count('participants')).filter(
        num_participants=2
    ).filter(
        participants=request.user
    ).filter(
        participants=other_user 
    )
    
    print(f"DEBUG: До поиска: QuerySet: {possible_chats.query}") 
    
    chat_room = possible_chats.first()

    if not chat_room:
        print("DEBUG: Существующий чат не найден. Создаю новый чат.")
        with transaction.atomic(): 
            chat_room = ChatRoom.objects.create()
            chat_room.participants.add(request.user, other_user)
            chat_room.save()
            print(f"DEBUG: Новый чат создан с ID: {chat_room.id}")
    else:
        print(f"DEBUG: Существующий чат найден. ID: {chat_room.id}")

    return redirect('chat:chat_room', room_id=chat_room.id)



@login_required
@require_POST # Разрешаем только POST-запросы
def upload_attachment(request):
    """
    Обрабатывает загрузку файлов (вложений) и текста сообщения.
    Создает ChatMessage и ChatAttachment объекты.
    Уведомляет Channel Layer о новом сообщении.
    """
    room_id = request.POST.get('chat_room_id')
    message_content = request.POST.get('message_content', '').strip()
    uploaded_files = request.FILES.getlist('files') # Получаем список загруженных файлов

    if not room_id:
        return HttpResponseBadRequest("Не указан ID чата.")
    if not message_content and not uploaded_files:
        return HttpResponseBadRequest("Сообщение не может быть пустым и без вложений.")
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Пользователь не аутентифицирован'}, status=401)


    try:
        chat_room = get_object_or_404(ChatRoom, id=room_id)

        # Проверка безопасности: убеждаемся, что пользователь является участником чата
        if not chat_room.participants.filter(id=request.user.id).exists():
            return JsonResponse({'error': 'Вы не являетесь участником этого чата.'}, status=403)

        # Используем транзакцию для атомарности: либо всё сохраняется, либо ничего
        with transaction.atomic():
            # 1. Создаем объект ChatMessage
            # Поле 'content' может быть пустым, если отправляются только вложения
            chat_message = ChatMessage.objects.create(
                chat_room=chat_room,
                sender=request.user,
                content=message_content
            )

            # 2. Обрабатываем и сохраняем каждое вложение
            attachments_data = [] # Для сбора информации о вложениях для отправки через WebSocket
            for uploaded_file in uploaded_files:
                file_type = 'document' # По умолчанию
                if uploaded_file.content_type.startswith('image'):
                    file_type = 'image'
                elif uploaded_file.content_type.startswith('video'):
                    file_type = 'video'

                chat_attachment = ChatAttachment.objects.create(
                    message=chat_message,
                    file=uploaded_file,
                    file_type=file_type,
                    original_filename=uploaded_file.name
                )
                # Добавляем данные о вложении для отправки через WebSocket
                attachments_data.append({
                    'file_url': chat_attachment.file.url,
                    'file_type': chat_attachment.file_type,
                    'original_filename': chat_attachment.original_filename,
                })

                # TODO:


        # 3. Уведомляем Channel Layer о новом сообщении
        channel_layer = get_channel_layer()
        room_group_name = f'chat_{room_id}'

        # Собираем данные для отправки в Channel Layer
        # Они должны быть сериализуемыми (JSON-совместимыми)
        message_data = {
            'type': 'chat_message', # Это имя метода в консьюмере
            'message': chat_message.content,
            'sender_username': request.user.username,
            'timestamp': chat_message.timestamp.strftime('%d.%m.%Y %H:%M'),
            'message_id': chat_message.id,
            'attachments': attachments_data, # Передаем информацию о вложениях
            'is_edited': chat_message.is_edited,
        }

        # Отправляем сообщение в группу через Channel Layer
        # async_to_sync позволяет вызвать асинхронную функцию из синхронного представления
        async_to_sync(channel_layer.group_send)(
            room_group_name,
            message_data
        )

        return JsonResponse({'status': 'success', 'message_id': chat_message.id, 'attachments': attachments_data})

    except ChatRoom.DoesNotExist:
        return JsonResponse({'error': 'Чат не найден.'}, status=404)
    except Exception as e:
        # Обработка других возможных ошибок
        print(f"Ошибка при загрузке вложения: {e}")
        return JsonResponse({'error': f'Произошла ошибка при загрузке: {str(e)}'}, status=500)


# НОВАЯ ФУНКЦИЯ ДЛЯ AJAX-ПАГИНАЦИИ
@login_required
def load_more_messages(request, room_id):
    """
    Загружает более старые сообщения для чата.
    Принимает room_id и before_message_id (ID самого старого сообщения на клиенте).
    Возвращает JSON с порцией старых сообщений.
    """
    try:
        chat_room = get_object_or_404(ChatRoom, id=room_id)

        # Проверка безопасности: убеждаемся, что пользователь является участником чата
        if not chat_room.participants.filter(id=request.user.id).exists():
            return JsonResponse({'error': 'Вы не являетесь участником этого чата.'}, status=403)

        before_message_id = request.GET.get('before_message_id')
        messages_per_load = 50 # Количество сообщений для загрузки за раз

        messages_query = chat_room.messages.order_by('-timestamp').select_related('sender').prefetch_related('attachments')

        if before_message_id:
            # Если указан before_message_id, загружаем сообщения старше этого ID
            messages_query = messages_query.filter(id__lt=before_message_id)

        # Ограничиваем количество загружаемых сообщений
        messages = messages_query[:messages_per_load]
        messages = list(reversed(messages)) # Реверсируем для правильного порядка (от старых к новым)

        # Сериализуем сообщения для отправки в JSON
        # Мы не можем просто сериализовать QuerySet напрямую, т.к. нам нужны данные из связанных моделей.
        # Поэтому формируем список словарей вручную.
        messages_data = []
        for message in messages:
            attachments_data = []
            for attachment in message.attachments.all():
                attachments_data.append({
                    'file_url': attachment.file.url,
                    'file_type': attachment.file_type,
                    'original_filename': attachment.original_filename,
                })

            messages_data.append({
                'id': message.id,
                'sender_id': message.sender.id,
                'sender_username': message.sender.username,
                'sender_avatar_url': message.sender.profile.avatar.url if hasattr(message.sender, 'profile') and message.sender.profile.avatar else '',
                'content': message.content,
                'timestamp': message.timestamp.strftime('%d.%m.%Y %H:%M'), # Форматируем дату для удобства JS
                'attachments': attachments_data,
                'is_edited': message.is_edited,
                'is_current_user': message.sender == request.user # Для определения, кто отправил сообщение на фронтенде
            })
        
        # Определяем, есть ли еще более старые сообщения
        has_more = chat_room.messages.filter(id__lt=before_message_id).count() > messages_per_load

        return JsonResponse({
            'messages': messages_data,
            'has_more': has_more,
            'current_user_id': request.user.id # Отдаем ID текущего пользователя для рендеринга на клиенте
        })

    except ChatRoom.DoesNotExist:
        return JsonResponse({'error': 'Чат не найден.'}, status=404)
    except Exception as e:
        print(f"Ошибка при загрузке старых сообщений: {e}")
        return JsonResponse({'error': f'Произошла ошибка: {str(e)}'}, status=500)


@login_required
@require_POST
def edit_message(request, room_id, message_id):
    """
    AJAX-эндпоинт для редактирования сообщения.
    """
    try:
        message = get_object_or_404(ChatMessage, id=message_id, sender=request.user)

        if message.chat_room.id != room_id:
            return JsonResponse({'error': 'Сообщение не принадлежит указанной комнате.'}, status=400)
            
        # ИЗМЕНЕНИЕ ЗДЕСЬ: Меняем 'content' на 'message_content'
        new_content = request.POST.get('message_content', '').strip()
        
        # ДОБАВЛЕНО: Обработка существующих и новых вложений
        existing_attachment_ids_str = request.POST.get('existing_attachments', '[]')
        existing_attachment_ids = json.loads(existing_attachment_ids_str)
        new_files = request.FILES.getlist('new_files') # Получаем список новых файлов

        if not new_content and not new_files and not existing_attachment_ids:
            return JsonResponse({'error': 'Сообщение не может быть пустым и без вложений.'}, status=400)

        with transaction.atomic():
            # Обновляем контент сообщения
            message.content = new_content
            message.is_edited = True
            message.save()

            # Удаляем вложения, которых нет в списке existing_attachment_ids
            # (то есть те, которые пользователь удалил из предпросмотра)
            attachments_to_delete = message.attachments.exclude(id__in=existing_attachment_ids)
            for attachment in attachments_to_delete:
                attachment.delete() # Это также удалит файл с диска, если у вас настроен model.delete()

            # Добавляем новые вложения
            for f in new_files:
                ChatAttachment.objects.create(message=message, file=f, original_filename=f.name)


            channel_layer = get_channel_layer()
            room_group_name = f'chat_{message.chat_room.id}'

            # Отправляем обновленные данные сообщения (включая вложения)
            # Чтобы клиент мог перерисовать сообщение с правильными вложениями
            # Вам понадобится сериализовать вложения для отправки через WebSocket
            updated_attachments_data = []
            for att in message.attachments.all():
                updated_attachments_data.append({
                    'id': str(att.id), # Важно, чтобы ID был строкой для JS
                    'file_url': att.file.url,
                    'original_filename': att.original_filename,
                    'file_type': att.file_type # Убедитесь, что у вас есть это поле или логика определения
                })

            async_to_sync(channel_layer.group_send)(
                room_group_name,
                {
                    'type': 'message_edited',
                    'message_id': str(message.id),
                    'new_content': new_content,
                    'attachments': updated_attachments_data # Передаем обновленные вложения
                }
            )
        
        # Возвращаем обновленные данные (включая URL вложений)
        return JsonResponse({
            'status': 'success', 
            'message_id': message.id, 
            'new_content': new_content,
            'attachments': updated_attachments_data
        })
    except ChatMessage.DoesNotExist:
        return JsonResponse({'error': 'Сообщение не найдено или у вас нет прав на его редактирование.'}, status=403)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Некорректный JSON-формат для existing_attachments.'}, status=400)
    except Exception as e:
        print(f"Ошибка при редактировании сообщения: {e}")
        return JsonResponse({'error': str(e)}, status=500)

@login_required
@require_POST
def delete_message(request, room_id, message_id):
    """
    AJAX-эндпоинт для удаления сообщения.
    """
    try:
        message = get_object_or_404(ChatMessage, id=message_id, sender=request.user)

        if message.chat_room.id != room_id:
            return JsonResponse({'error': 'Сообщение не принадлежит указанной комнате.'}, status=400)

        with transaction.atomic():
            message_id_str = str(message.id)
            room_id_for_ws = message.chat_room.id
            message.delete()

            channel_layer = get_channel_layer()
            room_group_name = f'chat_{room_id_for_ws}'
            async_to_sync(channel_layer.group_send)(
                room_group_name,
                {
                    'type': 'message_deleted',
                    'message_id': message_id_str
                }
            )
        return JsonResponse({'status': 'success', 'message_id': message_id_str})
    except ChatMessage.DoesNotExist:
        return JsonResponse({'error': 'Сообщение не найдено или у вас нет прав на его удаление.'}, status=403)
    except Exception as e:
        print(f"Ошибка при удалении сообщения: {e}")
        return JsonResponse({'error': str(e)}, status=500)