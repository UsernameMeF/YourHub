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

# Імпортуємо Channel Layer
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

# Groups
from .models import GroupChat, GroupChatMessage, GroupChatAttachment
from .forms import GroupChatCreateForm

# Create your views here.
User = get_user_model()

def get_chat_models_and_instance(room_type, room_id):
    print(f"DEBUG: get_chat_models_and_instance викликано з типом={room_type}, id={room_id}") # Translated
    if room_type == 'private':
        try:
            chat_instance = ChatRoom.objects.get(id=room_id)
            print(f"DEBUG: ChatRoom знайдено: {chat_instance.id}") # Translated
            return ChatRoom, ChatMessage, ChatAttachment, 'private', chat_instance
        except ChatRoom.DoesNotExist:
            print(f"DEBUG: ChatRoom з ID {room_id} не знайдено.") # Translated
            return None, None, None, None, None
    elif room_type == 'group':
        try:
            chat_instance = GroupChat.objects.get(id=room_id)
            print(f"DEBUG: GroupChat знайдено: {chat_instance.id}") # Translated
            return GroupChat, GroupChatMessage, GroupChatAttachment, 'group', chat_instance
        except GroupChat.DoesNotExist:
            print(f"DEBUG: GroupChat з ID {room_id} не знайдено.") # Translated
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
    Відображає сторінку конкретного групового чату.
    """ # Translated
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
    Знаходить або створює приватний чат між поточним користувачем та іншим користувачем.
    Перенаправляє на сторінку цього чату.
    """ # Translated
    other_user = get_object_or_404(User, id=other_user_id)

    if request.user.id == other_user.id:
        print(f"DEBUG: Користувач {request.user.username} намагається створити чат із самим собою. Перенаправлення.") # Translated
        return redirect('users:profile', pk=request.user.id) # Проверьте это имя URL # Translated


    possible_chats = ChatRoom.objects.annotate(num_participants=models.Count('participants')).filter(
        num_participants=2
    ).filter(
        participants=request.user
    ).filter(
        participants=other_user 
    )
    
    print(f"DEBUG: До пошуку: QuerySet: {possible_chats.query}") # Translated
    
    chat_room = possible_chats.first()

    if not chat_room:
        print("DEBUG: Існуючий чат не знайдено. Створюю новий чат.") # Translated
        with transaction.atomic(): 
            chat_room = ChatRoom.objects.create()
            chat_room.participants.add(request.user, other_user)
            chat_room.save()
            print(f"DEBUG: Новий чат створено з ID: {chat_room.id}") # Translated
    else:
        print(f"DEBUG: Існуючий чат знайдено. ID: {chat_room.id}") # Translated

    return redirect('chat:chat_room', room_id=chat_room.id)



@login_required
@require_POST
def upload_attachment(request, room_type, room_id):
    message_content = request.POST.get('message_content', '').strip()
    uploaded_files = request.FILES.getlist('files')


    ChatModel, MessageModel, AttachmentModel, actual_room_type, chat_instance = get_chat_models_and_instance(room_type, room_id)

    if not ChatModel:
        return JsonResponse({'error': 'Чат не знайдено.'}, status=404) # Translated

    if actual_room_type != room_type:
        return JsonResponse({'error': 'Невідповідність типу чату.'}, status=400) # Translated


    try:
        if not chat_instance.participants.filter(id=request.user.id).exists():
            return JsonResponse({'error': 'Ви не є учасником цього чату.'}, status=403) # Translated

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
        print(f"Помилка при завантаженні вкладення: {e}") # Translated
        return JsonResponse({'error': f'Сталася помилка при завантаженні: {str(e)}'}, status=500) # Translated


@login_required
def load_more_messages(request, room_type, room_id):
    ChatModel, MessageModel, AttachmentModel, actual_room_type, chat_instance = get_chat_models_and_instance(room_type, room_id)

    if not ChatModel:
        return JsonResponse({'error': 'Чат не знайдено.'}, status=404) # Translated

    if actual_room_type != room_type:
        return JsonResponse({'error': 'Невідповідність типу чату.'}, status=400) # Translated

    try:
        if not chat_instance.participants.filter(id=request.user.id).exists():
            return JsonResponse({'error': 'Ви не є учасником цього чату.'}, status=403) # Translated

        before_message_id = request.GET.get('before_message_id')
        messages_per_load = 50

        if room_type == 'private':
            messages_query = MessageModel.objects.filter(chat_room=chat_instance).order_by('-timestamp').select_related('sender').prefetch_related('attachments')
        elif room_type == 'group':
            messages_query = MessageModel.objects.filter(group_chat=chat_instance).order_by('-timestamp').select_related('sender').prefetch_related('attachments')
        else:
            return JsonResponse({'error': 'Невідомий тип чату.'}, status=400) # Translated

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
        print(f"Помилка при завантаженні старих повідомлень: {e}") # Translated
        return JsonResponse({'error': f'Сталася помилка: {str(e)}'}, status=500) # Translated


@login_required
@require_POST
def edit_message(request, room_type, room_id, message_id):
    print(f"DEBUG: Вхід у функцію edit_message для room_type={room_type}, room_id={room_id}, message_id={message_id}") # Translated

    ChatModel, MessageModel, AttachmentModel, actual_room_type, chat_instance = get_chat_models_and_instance(room_type, room_id)
    
    print(f"DEBUG: З get_chat_models_and_instance: ChatModel={ChatModel.__name__ if ChatModel else None}, MessageModel={MessageModel.__name__ if MessageModel else None}, actual_room_type={actual_room_type}, chat_instance={chat_instance}") # Translated

    if not ChatModel or not chat_instance:
        print("DEBUG: ChatModel або chat_instance є None. Повертаю 404 (Чат не знайдено).") # Translated
        return JsonResponse({'error': 'Чат не знайдено.'}, status=404) # Translated

    if actual_room_type != room_type:
        print(f"DEBUG: Невідповідність типу кімнати: фактичний={actual_room_type}, очікуваний={room_type}. Повертаю 400.") # Translated
        return JsonResponse({'error': 'Невідповідність типу чату.'}, status=400) # Translated

    try:
        if room_type == 'private':
            print(f"DEBUG: Спроба отримати приватне повідомлення {message_id} з чату {chat_instance.id} для користувача {request.user.id}.") # Translated
            message = get_object_or_404(MessageModel, id=message_id, sender=request.user, chat_room=chat_instance)
            print(f"DEBUG: Приватне повідомлення {message_id} знайдено за допомогою get_object_or_404.") # Translated
        elif room_type == 'group':
            print(f"DEBUG: Спроба отримати групове повідомлення {message_id} з чату {chat_instance.id} для користувача {request.user.id}.") # Translated
            message = get_object_or_404(MessageModel, id=message_id, sender=request.user, group_chat=chat_instance)
            print(f"DEBUG: Групове повідомлення {message_id} знайдено за допомогою get_object_or_404.") # Translated
        else:
            print(f"DEBUG: Невідомий тип чату: {room_type}. Повертаю 400.") # Translated
            return JsonResponse({'error': 'Невідомий тип чату.'}, status=400) # Translated

        new_content = request.POST.get('message_content', '').strip()
        existing_attachment_ids_str = request.POST.get('existing_attachments', '[]')
        
        print(f"DEBUG: new_content='{new_content}', existing_attachment_ids_str='{existing_attachment_ids_str}'") # Translated

        try:
            existing_attachment_ids = json.loads(existing_attachment_ids_str)
        except json.JSONDecodeError:
            print("DEBUG: JSONDecodeError для existing_attachments.") # Translated
            return JsonResponse({'error': 'Некоректний JSON-формат для existing_attachments.'}, status=400) # Translated

        new_files = request.FILES.getlist('new_files')
        print(f"DEBUG: new_files count: {len(new_files)}") # Translated

        if not new_content and not new_files and not existing_attachment_ids:
            print("DEBUG: Зміст повідомлення, нові файли та існуючі вкладення порожні. Повертаю 400.") # Translated
            return JsonResponse({'error': 'Повідомлення не може бути порожнім і без вкладень.'}, status=400) # Translated

        with transaction.atomic():
            message.content = new_content
            message.is_edited = True
            message.save()
            print(f"DEBUG: Зміст повідомлення {message_id} оновлено.") # Translated

            attachments_to_delete = message.attachments.exclude(id__in=existing_attachment_ids)
            for attachment in attachments_to_delete:
                print(f"DEBUG: Видалення вкладення {attachment.id} ({attachment.original_filename}).") # Translated
                attachment.delete()

            for f in new_files:
                AttachmentModel.objects.create(message=message, file=f, original_filename=f.name)
                print(f"DEBUG: Створено нове вкладення {f.name}.") # Translated

            channel_layer = get_channel_layer()
            room_group_name = f'{room_type}_chat_{room_id}'
            print(f"DEBUG: Надсилання message_edited до групи шарів каналу: {room_group_name}") # Translated

            updated_attachments_data = []
            for att in message.attachments.all():
                updated_attachments_data.append({
                    'id': str(att.id),
                    'file_url': att.file.url,
                    'original_filename': att.original_filename,
                    'file_type': att.file_type
                })
            print(f"DEBUG: updated_attachments_data: {updated_attachments_data}") # Translated


            async_to_sync(channel_layer.group_send)(
                room_group_name,
                {
                    'type': 'message_edited',
                    'message_id': str(message.id),
                    'new_content': new_content,
                    'attachments': updated_attachments_data
                }
            )
            print("DEBUG: Channel layer group_send завершено.") # Translated

        print("DEBUG: Функція edit_message успішно завершена. Повертаю JsonResponse про успіх.") # Translated
        return JsonResponse({
            'status': 'success',
            'message_id': message.id,
            'new_content': new_content,
            'attachments': updated_attachments_data
        })
    except MessageModel.DoesNotExist:
        print(f"DEBUG: Виявлено MessageModel.DoesNotExist для повідомлення {message_id}. Повертаю 403.") # Translated
        return JsonResponse({'error': 'Повідомлення не знайдено або у вас немає прав на його редагування.'}, status=403) # Translated
    except Exception as e:
        print(f"DEBUG: Загальна помилка в edit_message: {e}. Повертаю 500.") # Translated
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_POST
def delete_message(request, room_type, room_id, message_id): 
    ChatModel, MessageModel, AttachmentModel, actual_room_type, chat_instance = get_chat_models_and_instance(room_type, room_id)

    if not ChatModel:
        return JsonResponse({'error': 'Чат не знайдено.'}, status=404) # Translated

    if actual_room_type != room_type:
        return JsonResponse({'error': 'Невідповідність типу чату.'}, status=400) # Translated

    try:
        if room_type == 'private':
            message = get_object_or_404(MessageModel, id=message_id, sender=request.user, chat_room=chat_instance)
        elif room_type == 'group':
            message = get_object_or_404(MessageModel, id=message_id, sender=request.user, group_chat=chat_instance)
        else:
            return JsonResponse({'error': 'Невідомий тип чату.'}, status=400) # Translated

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
        return JsonResponse({'error': 'Повідомлення не знайдено або у вас немає прав на його видалення.'}, status=403) # Translated
    except Exception as e:
        print(f"Помилка при видаленні повідомлення: {e}") # Translated
        return JsonResponse({'error': str(e)}, status=500)


# Groups
@login_required
@require_POST
def create_group_chat_ajax(request):
    """
    Обробляє AJAX-запит для створення нового групового чату.
    """ # Translated
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
            return JsonResponse({'error': 'Сталася помилка при створенні групового чату.'}, status=500) # Translated
    else:
        errors = {field: [str(err) for err in form.errors[field]] for field in form.errors}
        return JsonResponse({'error': 'Некоректні дані форми.', 'details': errors}, status=400) # Translated


@login_required
def create_group_chat_view(request):
    if request.method == 'POST':
        form = GroupChatCreateForm(request.POST, request_user=request.user)
        if form.is_valid():
            name = form.cleaned_data['name']
            description = form.cleaned_data['description']
            participants = form.cleaned_data['participants']

            with transaction.atomic():
                # Створюємо груповий чат
                group_chat = GroupChat.objects.create( # Translated
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
    print("DEBUG: Відображення create_group_chat.html") # Translated
    return render(request, 'chat/create_group_chat.html', {'form': form})