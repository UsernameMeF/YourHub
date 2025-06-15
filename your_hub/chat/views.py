import datetime
import json
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Count, OuterRef, Subquery, Max
from django.db import models
from django.http import JsonResponse, HttpResponseBadRequest 
from django.views.decorators.http import require_POST
from django.db import transaction 

# Chats
from .models import ChatRoom, ChatMessage, ChatAttachment
from django.contrib.auth import get_user_model

# Импортируем Channel Layer
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

# Groups
from .models import GroupChat, GroupChatMessage, GroupChatAttachment
from .forms import GroupChatCreateForm

# Create your views here.
User = get_user_model()

def get_chat_models_and_instance(room_type, room_id):
    print(f"DEBUG: get_chat_models_and_instance called with type={room_type}, id={room_id}")
    if room_type == 'private':
        try:
            chat_instance = ChatRoom.objects.get(id=room_id)
            print(f"DEBUG: ChatRoom found: {chat_instance.id}")
            return ChatRoom, ChatMessage, ChatAttachment, 'private', chat_instance
        except ChatRoom.DoesNotExist:
            print(f"DEBUG: ChatRoom with ID {room_id} not found.")
            return None, None, None, None, None
    elif room_type == 'group':
        try:
            chat_instance = GroupChat.objects.get(id=room_id)
            print(f"DEBUG: GroupChat found: {chat_instance.id}")
            return GroupChat, GroupChatMessage, GroupChatAttachment, 'group', chat_instance
        except GroupChat.DoesNotExist:
            print(f"DEBUG: GroupChat with ID {room_id} not found.")
            return None, None, None, None, None
    else:
        return None, None, None, None, None


@login_required
def chat_list_view(request):
    chat_rooms = ChatRoom.objects.filter(participants=request.user).order_by('-created_at')

    group_rooms = GroupChat.objects.filter(participants=request.user).distinct().order_by('-created_at')

    today_date = datetime.date.today()

    for room in chat_rooms:
        room.last_message = ChatMessage.objects.filter(chat_room=room).order_by('-timestamp').first()

    for group_room in group_rooms:
        group_room.last_message = GroupChatMessage.objects.filter(group_chat=group_room).order_by('-timestamp').first()


    context = {
        'chat_rooms': chat_rooms,
        'group_chats': group_rooms, 
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
def group_chat_room_view(request, group_chat_id):
    """
    Отображает страницу конкретного группового чата.
    """
    group_chat = get_object_or_404(
        GroupChat.objects.filter(participants=request.user)
                       .prefetch_related('participants')
                       .select_related('owner'),
        id=group_chat_id
    )

    messages_in_group = GroupChatMessage.objects.filter(group_chat=group_chat) \
                                        .select_related('sender') \
                                        .prefetch_related('attachments', 'read_by') \
                                        .order_by('timestamp')

    with transaction.atomic():
        unread_messages_for_user = messages_in_group.exclude(sender=request.user) \
                                                    .exclude(read_by=request.user)
        for message in unread_messages_for_user:
            message.read_by.add(request.user)

    context = {
        'group_chat': group_chat,
        'messages': messages_in_group,
        'today_date': datetime.date.today(),
    }
    return render(request, 'chat/group_room.html', context) 

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
@require_POST
def upload_attachment(request, room_type, room_id):
    message_content = request.POST.get('message_content', '').strip()
    uploaded_files = request.FILES.getlist('files')


    ChatModel, MessageModel, AttachmentModel, actual_room_type, chat_instance = get_chat_models_and_instance(room_type, room_id)

    if not ChatModel:
        return JsonResponse({'error': 'Чат не найден.'}, status=404)

    if actual_room_type != room_type:
        return JsonResponse({'error': 'Несоответствие типа чата.'}, status=400)


    try:
        if not chat_instance.participants.filter(id=request.user.id).exists():
            return JsonResponse({'error': 'Вы не являетесь участником этого чата.'}, status=403)

        with transaction.atomic():
            if room_type == 'private':
                chat_message = MessageModel.objects.create(
                    chat_room=chat_instance,
                    sender=request.user,
                    content=message_content
                )
            elif room_type == 'group':
                chat_message = MessageModel.objects.create(
                    group_chat=chat_instance,
                    sender=request.user,
                    content=message_content
                )
            attachments_data = []
            for uploaded_file in uploaded_files:
                file_type = 'document'
                if uploaded_file.content_type.startswith('image'):
                    file_type = 'image'
                elif uploaded_file.content_type.startswith('video'):
                    file_type = 'video'

                attachment_instance = AttachmentModel.objects.create(
                    message=chat_message,
                    file=uploaded_file,
                    file_type=file_type,
                    original_filename=uploaded_file.name
                )
                attachments_data.append({
                    'file_url': attachment_instance.file.url,
                    'file_type': attachment_instance.file_type,
                    'original_filename': attachment_instance.original_filename,
                })

        channel_layer = get_channel_layer()
        room_group_name = f'{room_type}_chat_{room_id}'

        message_data = {
            'type': 'chat_message',
            'message': chat_message.content,
            'sender_username': request.user.username,
            'timestamp': chat_message.timestamp.strftime('%d.%m.%Y %H:%M'),
            'message_id': chat_message.id,
            'attachments': attachments_data,
            'is_edited': chat_message.is_edited,
            'sender_avatar_url': request.user.profile.avatar.url if hasattr(request.user, 'profile') and request.user.profile.avatar else '',
            'sender_id': request.user.id,
        }

        async_to_sync(channel_layer.group_send)(
            room_group_name,
            message_data
        )

        return JsonResponse({'status': 'success', 'message_id': chat_message.id, 'attachments': attachments_data})

    except Exception as e:
        print(f"Ошибка при загрузке вложения: {e}")
        return JsonResponse({'error': f'Произошла ошибка при загрузке: {str(e)}'}, status=500)


@login_required
def load_more_messages(request, room_type, room_id):
    ChatModel, MessageModel, AttachmentModel, actual_room_type, chat_instance = get_chat_models_and_instance(room_type, room_id)

    if not ChatModel:
        return JsonResponse({'error': 'Чат не найден.'}, status=404)

    if actual_room_type != room_type:
        return JsonResponse({'error': 'Несоответствие типа чата.'}, status=400)

    try:
        if not chat_instance.participants.filter(id=request.user.id).exists():
            return JsonResponse({'error': 'Вы не являетесь участником этого чата.'}, status=403)

        before_message_id = request.GET.get('before_message_id')
        messages_per_load = 50

        if room_type == 'private':
            messages_query = MessageModel.objects.filter(chat_room=chat_instance).order_by('-timestamp').select_related('sender').prefetch_related('attachments')
        elif room_type == 'group':
            messages_query = MessageModel.objects.filter(group_chat=chat_instance).order_by('-timestamp').select_related('sender').prefetch_related('attachments')
        else:
            return JsonResponse({'error': 'Неизвестный тип чата.'}, status=400)

        if before_message_id:
            messages_query = messages_query.filter(id__lt=before_message_id)

        messages = messages_query[:messages_per_load]
        messages = list(reversed(messages))

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
                'timestamp': message.timestamp.strftime('%d.%m.%Y %H:%M'),
                'attachments': attachments_data,
                'is_edited': message.is_edited,
                'is_current_user': message.sender == request.user
            })


        if room_type == 'private':
            has_more = MessageModel.objects.filter(chat_room=chat_instance, id__lt=before_message_id).exists() 
        elif room_type == 'group':
            has_more = MessageModel.objects.filter(group_chat=chat_instance, id__lt=before_message_id).exists() 
        else:
            has_more = False

        return JsonResponse({
            'messages': messages_data,
            'has_more': has_more,
            'current_user_id': request.user.id
        })

    except Exception as e:
        print(f"Ошибка при загрузке старых сообщений: {e}")
        return JsonResponse({'error': f'Произошла ошибка: {str(e)}'}, status=500)


@login_required
@require_POST
def edit_message(request, room_type, room_id, message_id):
    print(f"DEBUG: Entering edit_message view for room_type={room_type}, room_id={room_id}, message_id={message_id}")

    ChatModel, MessageModel, AttachmentModel, actual_room_type, chat_instance = get_chat_models_and_instance(room_type, room_id)
    
    print(f"DEBUG: From get_chat_models_and_instance: ChatModel={ChatModel.__name__ if ChatModel else None}, MessageModel={MessageModel.__name__ if MessageModel else None}, actual_room_type={actual_room_type}, chat_instance={chat_instance}")

    if not ChatModel or not chat_instance:
        print("DEBUG: ChatModel or chat_instance is None. Returning 404 (Чат не найден).")
        return JsonResponse({'error': 'Чат не найден.'}, status=404)

    if actual_room_type != room_type:
        print(f"DEBUG: Room type mismatch: actual={actual_room_type}, expected={room_type}. Returning 400.")
        return JsonResponse({'error': 'Несоответствие типа чата.'}, status=400)

    try:
        if room_type == 'private':
            print(f"DEBUG: Attempting to get private message {message_id} from chat {chat_instance.id} for user {request.user.id}.")
            message = get_object_or_404(MessageModel, id=message_id, sender=request.user, chat_room=chat_instance)
            print(f"DEBUG: Private message {message_id} found by get_object_or_404.")
        elif room_type == 'group':
            print(f"DEBUG: Attempting to get group message {message_id} from chat {chat_instance.id} for user {request.user.id}.")
            message = get_object_or_404(MessageModel, id=message_id, sender=request.user, group_chat=chat_instance)
            print(f"DEBUG: Group message {message_id} found by get_object_or_404.")
        else:
            print(f"DEBUG: Unknown chat type: {room_type}. Returning 400.")
            return JsonResponse({'error': 'Неизвестный тип чата.'}, status=400)

        new_content = request.POST.get('message_content', '').strip()
        existing_attachment_ids_str = request.POST.get('existing_attachments', '[]')
        
        print(f"DEBUG: new_content='{new_content}', existing_attachment_ids_str='{existing_attachment_ids_str}'")

        try:
            existing_attachment_ids = json.loads(existing_attachment_ids_str)
        except json.JSONDecodeError:
            print("DEBUG: JSONDecodeError for existing_attachments.")
            return JsonResponse({'error': 'Некорректный JSON-формат для existing_attachments.'}, status=400)

        new_files = request.FILES.getlist('new_files')
        print(f"DEBUG: new_files count: {len(new_files)}")

        if not new_content and not new_files and not existing_attachment_ids:
            print("DEBUG: Message content, new files, and existing attachments are all empty. Returning 400.")
            return JsonResponse({'error': 'Сообщение не может быть пустым и без вложений.'}, status=400)

        with transaction.atomic():
            message.content = new_content
            message.is_edited = True
            message.save()
            print(f"DEBUG: Message {message_id} content updated.")

            attachments_to_delete = message.attachments.exclude(id__in=existing_attachment_ids)
            for attachment in attachments_to_delete:
                print(f"DEBUG: Deleting attachment {attachment.id} ({attachment.original_filename}).")
                attachment.delete()

            for f in new_files:
                AttachmentModel.objects.create(message=message, file=f, original_filename=f.name)
                print(f"DEBUG: Created new attachment {f.name}.")

            channel_layer = get_channel_layer()
            room_group_name = f'{room_type}_chat_{room_id}'
            print(f"DEBUG: Sending message_edited to channel layer group: {room_group_name}")

            updated_attachments_data = []
            for att in message.attachments.all():
                updated_attachments_data.append({
                    'id': str(att.id),
                    'file_url': att.file.url,
                    'original_filename': att.original_filename,
                    'file_type': att.file_type
                })
            print(f"DEBUG: updated_attachments_data: {updated_attachments_data}")


            async_to_sync(channel_layer.group_send)(
                room_group_name,
                {
                    'type': 'message_edited',
                    'message_id': str(message.id),
                    'new_content': new_content,
                    'attachments': updated_attachments_data
                }
            )
            print("DEBUG: Channel layer group_send completed.")

        print("DEBUG: edit_message function finished successfully. Returning success JsonResponse.")
        return JsonResponse({
            'status': 'success',
            'message_id': message.id,
            'new_content': new_content,
            'attachments': updated_attachments_data
        })
    except MessageModel.DoesNotExist:
        print(f"DEBUG: Caught MessageModel.DoesNotExist for message {message_id}. Returning 403.")
        return JsonResponse({'error': 'Сообщение не найдено или у вас нет прав на его редактирование.'}, status=403)
    except Exception as e:
        print(f"DEBUG: General error in edit_message: {e}. Returning 500.")
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_POST
def delete_message(request, room_type, room_id, message_id): 
    ChatModel, MessageModel, AttachmentModel, actual_room_type, chat_instance = get_chat_models_and_instance(room_type, room_id)

    if not ChatModel:
        return JsonResponse({'error': 'Чат не найден.'}, status=404)

    if actual_room_type != room_type:
        return JsonResponse({'error': 'Несоответствие типа чата.'}, status=400)

    try:
        if room_type == 'private':
            message = get_object_or_404(MessageModel, id=message_id, sender=request.user, chat_room=chat_instance)
        elif room_type == 'group':
            message = get_object_or_404(MessageModel, id=message_id, sender=request.user, group_chat=chat_instance)
        else:
            return JsonResponse({'error': 'Неизвестный тип чата.'}, status=400)

        with transaction.atomic():
            message_id_str = str(message.id)
            room_id_for_ws = chat_instance.id 
            message.delete()

            channel_layer = get_channel_layer()
            room_group_name = f'{room_type}_chat_{room_id_for_ws}'

            async_to_sync(channel_layer.group_send)(
                room_group_name,
                {
                    'type': 'message_deleted',
                    'message_id': message_id_str
                }
            )
        return JsonResponse({'status': 'success', 'message_id': message_id_str})
    except MessageModel.DoesNotExist:
        return JsonResponse({'error': 'Сообщение не найдено или у вас нет прав на его удаление.'}, status=403)
    except Exception as e:
        print(f"Ошибка при удалении сообщения: {e}")
        return JsonResponse({'error': str(e)}, status=500)


# Groups
@login_required
@require_POST
def create_group_chat_ajax(request):
    """
    Обрабатывает AJAX-запрос для создания нового группового чата.
    """
    form = GroupChatCreateForm(request.POST, request_user=request.user)

    if form.is_valid():
        name = form.cleaned_data['name']
        participants_to_add = form.cleaned_data['participants']

        try:
            with transaction.atomic():
                group_chat = GroupChat.objects.create(
                    name=name,
                    owner=request.user
                )
                group_chat.participants.set(participants_to_add)
                group_chat.save()

            return JsonResponse({
                'status': 'success',
                'group_chat_id': group_chat.id,
                'group_chat_name': group_chat.name
            })

        except Exception as e:
            return JsonResponse({'error': 'Произошла ошибка при создании группового чата.'}, status=500)
    else:
        errors = {field: [str(err) for err in form.errors[field]] for field in form.errors}
        return JsonResponse({'error': 'Некорректные данные формы.', 'details': errors}, status=400)


@login_required
def create_group_chat_view(request):
    if request.method == 'POST':
        form = GroupChatCreateForm(request.POST, request_user=request.user)
        if form.is_valid():
            name = form.cleaned_data['name']
            description = form.cleaned_data['description']
            participants = form.cleaned_data['participants']

            with transaction.atomic():
                # Создаем групповой чат
                group_chat = GroupChat.objects.create(
                    name=name,
                    description=description, 
                    owner=request.user 
                )

                group_chat.participants.set(participants) 

            return redirect('chat:group_chat_room', group_chat_id=group_chat.id)
        else:
            pass 
    else:
        form = GroupChatCreateForm(request_user=request.user)
    print("DEBUG: Rendering create_group_chat.html") 
    return render(request, 'chat/create_group_chat.html', {'form': form})