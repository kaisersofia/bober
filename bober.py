import telebot
import database as db
import buttons as bt


# Создаем объект бота
bot = telebot.TeleBot('8021954444:AAFcPEEFEqcI0CdPfAkY2TH3d-sFo82qZDU')
# ID администратора
admin_id = 657942829
# Временные данные
admins = {}
users = {}


# Обработка команды /start
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    products = db.get_pr_buttons()
    if db.check_user(user_id):
        bot.send_message(user_id, f'Здравствуйте, @{message.from_user.username}!',
                         reply_markup=telebot.types.ReplyKeyboardRemove())
        bot.send_message(user_id, 'Выберите пункт меню:', reply_markup=bt.main_menu(products))
    else:
        bot.send_message(user_id, 'Привет! Давайте начнем регистрацию!\n'
                                  'Введите ваше Имя!', reply_markup=telebot.types.ReplyKeyboardRemove())
        # Переход на этап получения имени
        bot.register_next_step_handler(message, get_name)


# Этап получения имени
def get_name(message):
    user_id = message.from_user.id
    user_name = message.text
    bot.send_message(user_id, 'Отлично! Теперь отправьте свой номер через кнопку!',
                     reply_markup=bt.number_button())
    # Переход на этап получения номера
    bot.register_next_step_handler(message, get_number, user_name)


# Этап действия над товаром
@bot.callback_query_handler(lambda call: call.data in ['increment', 'decrement', 'to_cart', 'back'])
def choose_count(call):
    if call.data == 'increment':
        bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                      reply_markup=bt.choice_pr_buttons(db.get_exact_pr(users[call.message.chat.id]['pr_name'])[4],
                                                                        'increment', users[call.message.chat.id]['pr_amount']))
        users[call.message.chat.id]['pr_amount'] += 1
    elif call.data == 'decrement':
        bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                      reply_markup=bt.choice_pr_buttons(
                                          db.get_exact_pr(users[call.message.chat.id]['pr_name'])[4],
                                          'decrement', users[call.message.chat.id]['pr_amount']))
        users[call.message.chat.id]['pr_amount'] -= 1
    elif call.data == 'to_cart':
        pr_name = db.get_exact_pr(users[call.message.chat.id]['pr_name'])[1]
        db.add_to_cart(call.message.chat.id, pr_name, users[call.message.chat.id]['pr_amount'])
        bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
        bot.send_message(call.message.chat.id, 'Товар помещен в корзину!',
                         reply_markup=bt.main_menu(db.get_pr_buttons()))
    elif call.data == 'back':
        bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
        bot.send_message(call.message.chat.id, 'Возвращаю вас обратно в меню',
                         reply_markup=bt.main_menu(db.get_pr_buttons()))


# Этап работы с корзиной
@bot.callback_query_handler(lambda call: call.data in ['cart', 'order', 'clear'])
def cart_handle(call):
    text = 'Ваша корзина: \n\n'
    if call.data == 'clear':
        db.clear_cart(call.message.chat.id)
        bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
        bot.send_message(call.message.chat.id, 'Корзина очищена!', reply_markup=bt.main_menu(db.get_pr_buttons()))
    elif call.data == 'order':
        text = text.replace('Ваша корзина: ', 'Новый заказ!')
        user_cart = db.show_cart(call.message.chat.id)
        total = 0.0
        for i in user_cart:
            text += (f'Товар: {i[1]}\n'
                     f'Количество: {i[2]}\n\n')
            total = db.get_exact_price(i[1])[0] * i[2]
        text += f'Итого: {round(total, 1)}\n'
        bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
        bot.send_message(call.message.chat.id, 'Отправьте локацию для доставки товара!',
                         reply_markup=bt.location_button())
        # Переход на этап получения локации
        bot.register_next_step_handler(call.message, get_user_location, text)
    elif call.data == 'cart':
        user_cart = db.show_cart(call.message.chat.id)
        total = 0.0
        for i in user_cart:
            text += (f'Товар: {i[1]}\n'
                     f'Количество: {i[2]}\n\n')
            total = db.get_exact_price(i[1])[0] * i[2]
        text += f'Итого: {round(total, 1)}'
        bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
        bot.send_message(call.message.chat.id, text, reply_markup=bt.cart_buttons())



# Этап получения локации
def get_user_location(message, text):
    user_id = message.from_user.id
    # Проверяем, отправлена ли локация по кнопке
    if message.location:
        text += f'Клиент @{message.from_user.username}'
        bot.send_message(admin_id, text)
        bot.send_location(admin_id, latitude=message.location.latitude, longitude=message.location.longitude)
        db.make_order(user_id)
        db.clear_cart(user_id)
        bot.send_message(user_id, 'Ваш заказ оформлен! Скоро с вами свяжутся специалисты!',
                         reply_markup=telebot.types.ReplyKeyboardRemove())
        bot.send_message(user_id, 'Выберите пункт меню:', reply_markup=bt.main_menu(db.get_pr_buttons()))
    else:
        bot.send_message(user_id, 'Отправьте локацию по кнопке!')
        # Возвращение на этап получения локации
        bot.register_next_step_handler(message, get_user_location, text)


# Этап получения номера
def get_number(message, user_name):
    user_id = message.from_user.id
    # Проверяем, отправлен ли номер по кнопке
    if message.contact:
        user_number = message.contact.phone_number
        db.register(user_id, user_name, user_number)
        bot.send_message(user_id, 'Вы успешно зарегистрированы!',
                         reply_markup=telebot.types.ReplyKeyboardRemove())
        products = db.get_pr_buttons()
        bot.send_message(user_id, 'Выберите пункт меню:',
                         reply_markup=bt.main_menu(products))
    else:
        bot.send_message(user_id, 'Отправьте номер через кнопку ниже!')
        # Возвращение на этап получения номера
        bot.register_next_step_handler(message, get_number, user_name)


@bot.callback_query_handler(lambda call: int(call.data) in [i[0] for i in db.get_all_pr()])
def choose_pr_count(call):
    bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
    pr_info = db.get_exact_pr(int(call.data))
    bot.send_photo(call.message.chat.id, photo=pr_info[5],
                   caption=f'{pr_info[1]}\n\n'
                           f'Описание: {pr_info[2]}\n'
                           f'Количество: {pr_info[4]}\n'
                           f'Цена: {pr_info[3]}', reply_markup=bt.choice_pr_buttons(pr_info[4]))
    users[call.message.chat.id] = {'pr_name': call.data, 'pr_amount': 1}


## Админ панель ##
# Обработчик команды /admin
@bot.message_handler(commands=['admin'])
def start_admin(message):
    if message.from_user.id == admin_id:
        bot.send_message(admin_id, 'Добро пожаловать в админ-панель!',
                         reply_markup=bt.admin_menu())
        # Переход на этап выбора
        bot.register_next_step_handler(message, admin_choice)
    else:
        bot.send_message(message.from_user.id, 'Вы не администратор!')


# Этап выбора
def admin_choice(message):
    if message.text == 'Добавить продукт':
        bot.send_message(admin_id, 'Начнем добавления продукта\n'
                                   'Введите название, описание, цену, количество и фото товара через запятую\n'
                                   'Пример:\n'
                                   'Картошка, Классный клубень, 4999.99, 1000, https://kartoshka.jpg\n\n'
                                   'Для отправки фотографии, воспользуйтесь https://postimages.org/, '
                                   'загрузите фото товара и впишите прямую на нее ссылку',
                         reply_markup=telebot.types.ReplyKeyboardRemove())
        # Переход на этап получения товара
        bot.register_next_step_handler(message, get_product)
    elif message.text == 'Удалить продукт':
        if db.check_pr():
            products = db.get_all_pr()
            bot.send_message(admin_id, 'Выберите товар для удаления',
                             reply_markup=bt.admin_pr(products))
            # Переход на этап получения товара для удаления
            bot.register_next_step_handler(message, get_product_to_del)
        else:
            bot.send_message(admin_id, 'Товаров в базе нет!')
            # Возврат на этап выбора
            bot.register_next_step_handler(message, admin_choice)
    elif message.text == 'Изменить продукт':
        if db.check_pr():
            products = db.get_all_pr()
            bot.send_message(admin_id, 'Выберите товар для изменения',
                             reply_markup=bt.admin_pr(products))
            # Переход на этап получения товара для изменения
            bot.register_next_step_handler(message, get_product_to_chng)
        else:
            bot.send_message(admin_id, 'Товаров в базе нет!')
            # Возврат на этап выбора
            bot.register_next_step_handler(message, admin_choice)
    elif message.text == 'Перейти в главное меню':
        products = db.get_pr_buttons()
        bot.send_message(admin_id, 'Перенаправляю вас обратно в меню',
                         reply_markup=telebot.types.ReplyKeyboardRemove())
        bot.send_message(admin_id, 'Выберите пункт меню:',
                         reply_markup=bt.main_menu(products))


# Этап получения товара на добавление
def get_product(message):
    pr_attrs = message.text.split(', ')
    db.pr_to_db(pr_attrs[0], pr_attrs[1], pr_attrs[2], pr_attrs[3], pr_attrs[4])
    bot.send_message(admin_id, f'Продукт {pr_attrs[0]} успешно добавлен! Что-то ещё?',
                     reply_markup=bt.admin_menu())
    # Возвращение на этап выбора
    bot.register_next_step_handler(message, admin_choice)


# Этап получения товара на удаление
def get_product_to_del(message):
    pr_to_del = message.text
    bot.send_message(admin_id, 'Вы уверены?', reply_markup=bt.confirm_buttons())
    # Переход на этап подтверждения
    bot.register_next_step_handler(message, confirm_delete, pr_to_del)


# Этап получения товара на изменение
def get_product_to_chng(message):
    admins[message.from_user.id] = message.text
    bot.send_message(admin_id, 'Какой аттрибут вы хотите изменить?',
                     reply_markup=bt.change_buttons())


@bot.callback_query_handler(lambda call: call.data in ['name', 'description', 'price', 'count', 'photo'])
def change_attr(call):
    if call.data == 'name':
        bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
        bot.send_message(admin_id, 'Введите новое название товара')
        attr = call.data
        # Переход на этап получения подтверждения
        bot.register_next_step_handler(call, confirm_change, attr)
    elif call.data == 'description':
        bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
        bot.send_message(admin_id, 'Введите новое описание товара')
        attr = call.data
        # Переход на этап получения подтверждения
        bot.register_next_step_handler(call, confirm_change, attr)
    elif call.data == 'price':
        bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
        bot.send_message(admin_id, 'Введите новую цену товара')
        attr = call.data
        # Переход на этап получения подтверждения
        bot.register_next_step_handler(call, confirm_change, attr)
    elif call.data == 'count':
        bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
        bot.send_message(admin_id, 'Введите кол-во прибытия товара')
        attr = call.data
        # Переход на этап получения подтверждения
        bot.register_next_step_handler(call, confirm_change, attr)
    elif call.data == 'photo':
        bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
        bot.send_message(admin_id, 'Введите новую ссылку товара')
        attr = call.data
        # Переход на этап получения подтверждения
        bot.register_next_step_handler(call, confirm_change, attr)


# Этап подтверждения
def confirm_change(message, attr):
    bot.send_message(admin_id, 'Вы уверены?',
                     reply_markup=bt.confirm_buttons())
    new_value = message.text
    # Переход на этап изменения
    bot.register_next_step_handler(message, confirm_change_attr, attr, new_value)


# Этап подтверждения удаления
def confirm_delete(message, pr_to_del):
    if message.text == 'Да':
        db.del_product(pr_to_del)
        bot.send_message(admin_id, 'Товар успешно удален!', reply_markup=bt.admin_menu())
        # Переход на этап выбора
        bot.register_next_step_handler(message, admin_choice)
    elif message.text == 'Нет':
        bot.send_message(admin_id, 'Возвращаю вас обратно', reply_markup=bt.admin_menu())
        # Переход на этап выбора
        bot.register_next_step_handler(message, admin_choice)


# Этап подтверждения изменения
def confirm_change_attr(message, attr, new_value):
    if message.text == 'Да':
        if attr == 'price':
            db.change_pr_attr(admins[message.from_user.id], float(new_value), attr)
        else:
            db.change_pr_attr(admins[message.from_user.id], new_value, attr)
        bot.send_message(admin_id, 'Изменение прошло успешно!', reply_markup=bt.admin_menu())
        # Переход на этап выбора
        bot.register_next_step_handler(message, admin_choice)
    elif message.text == 'Нет':
        bot.send_message(admin_id, 'Возвращаю вас обратно', reply_markup=bt.admin_menu())
        # Переход на этап выбора
        bot.register_next_step_handler(message, admin_choice)


bot.polling()
