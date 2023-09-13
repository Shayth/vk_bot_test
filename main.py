import vk_api
from vk_api.longpoll import VkLongPoll, VkEventType
from vk_api.keyboard import VkKeyboard, VkKeyboardColor
from vk_api.utils import get_random_id
from config import vk_token


def load_from_db():
    data_db = []
    with open('user_data.txt', 'r') as file:
        for line in file:
            data_db.append(line.strip())
    return data_db


def check_data(data_db, user_id):
    found_items = False
    for item in data_db:
        parts = item.split(':')
        if len(parts) == 2:
            item_id, item_city = parts
            item_int_id = int(item_id)
            if item_int_id == user_id:
                found_items = True
    return found_items


def success_confirm(user_id, user_name, session_api):
    session_api.messages.send(
        user_id=user_id,
        message=f'{user_name}, город успешно зарегистрирован!',
        random_id=get_random_id(),
    )


def save_data_db(user_id, user_city):
    with open('user_data.txt', 'w') as file:
        file.write(f'{user_id}:{user_city}')
    file.close()


def fix_city(longpoll, session_api, user_id, user_name):
    session_api.messages.send(
        user_id=user_id,
        message=f'{user_name}, укажите ваш город',
        random_id=get_random_id(),
    )
    for event in longpoll.listen():
        if event.type == VkEventType.MESSAGE_NEW and event.to_me:
            if event.text != '':
                user_city = event.text
                save_data_db(user_id, user_city)
                success_confirm(user_id, user_name, session_api)
                main_keyboard(session_api, user_id)
                break


def main_keyboard(session_api, user_id):
    main_keyboard = VkKeyboard(one_time=True)
    main_keyboard.add_button('Погода', color=VkKeyboardColor.SECONDARY)
    main_keyboard.add_button('Пробка', color=VkKeyboardColor.SECONDARY)
    main_keyboard.add_button('Афиша', color=VkKeyboardColor.SECONDARY)
    main_keyboard.add_button('Валюта', color=VkKeyboardColor.SECONDARY)
    session_api.messages.send(
        user_id=user_id,
        message='Доступные кнопки:',
        random_id=get_random_id(),
        keyboard=main_keyboard.get_keyboard(),
    )


def main():
    # init vk_api

    data_db = load_from_db()
    vk_session = vk_api.VkApi(token=vk_token)
    session_api = vk_session.get_api()
    longpoll = VkLongPoll(vk_session)

    for event in longpoll.listen():
        if event.type == VkEventType.MESSAGE_NEW and event.to_me:
            # Get data by vk_api

            user_id = event.user_id
            user_info = vk_session.method('users.get', {'user_ids': user_id, 'fields': 'city'})
            user = user_info[0]
            user_name = user['first_name']
            user_city = user['city']['title'] if 'city' in user else 'Город не указан'
            message = event.text

            # Start message

            if message == "Начать":
                found_items = check_data(data_db, user_id)
                if found_items is True:
                    main_keyboard(session_api, user_id)
                else:
                    # Check user info by keyboard

                    if user_city != 'Город не указан':
                        keyboard_start_check = VkKeyboard(one_time=True)
                        keyboard_start_check.add_button('Да', color=VkKeyboardColor.POSITIVE)
                        keyboard_start_check.add_button('Неправильный город', color=VkKeyboardColor.NEGATIVE)
                        start_check_message = f'{user_name}, ваш город {user_city}?'
                        session_api.messages.send(
                            user_id=user_id,
                            message=start_check_message,
                            random_id=get_random_id(),
                            keyboard=keyboard_start_check.get_keyboard(),
                        )
                    else:
                        fix_city(longpoll, session_api, user_id, user_name)

            # City correct

            if message == 'Да':
                save_data_db(user_id, user_city)
                success_confirm(user_id, user_name, session_api)
                main_keyboard(session_api, user_id)

            # City incorrect

            if message == 'Неправильный город':
                fix_city(longpoll, session_api, user_id, user_name)

            if message == 'Погода':
                main_keyboard(session_api, user_id)

            if message == 'Пробка':
                main_keyboard(session_api, user_id)

            if message == 'Афиша':
                main_keyboard(session_api, user_id)

            if message == 'Валюта':
                main_keyboard(session_api, user_id)


if __name__ == '__main__':
    main()
