from getpass import getpass
import configparser
import os


if not os.path.exists('bot_data'):
    os.mkdir('bot_data')
if not os.path.exists('bot_data/config.ini'):
    config = configparser.ConfigParser()
    config['Telegram Bot'] = {}
    config['Telegram Bot']['token'] = input('\t[+] Пожалуйста, введите токен от бота (полученный от @BotFather): ').strip()
    config['MySQL'] = {}
    config['MySQL']['host'] = input('\t[+] Пожалуйста, введите хост вашего mysql сервера (если mysql server развернут у вас на ПК - введите "localhost"): ').strip()
    config['MySQL']['port'] = input('\t[+] Пожалуйста, введите порт вашего mysql сервера: ').strip()
    config['MySQL']['user'] = input('\t[+] Пожалуйста, введите юзернейм пользователя с полными правами к дампнутой базе данных (кроме GRANT OPTION): ').strip()
    config['MySQL']['password'] = getpass(prompt='\t[+] Пожалуйста, введите пароль от аккаунта mysql (который вы ввели ранее): ').strip()
    config['MySQL']['db_name'] = input('\t[+] Пожалуйста, введите название дампнутой базы данных: ').strip()
    with open('bot_data/config.ini', 'w', encoding='utf-8') as configure:
        config.write(configure)
    print(f'\u001b[31m!!!Если вдруг вы ввели неверные данные - просто удалите файл /bot_data/config.ini и перезапустите бота!!!')
if not os.path.exists('logs/'):
    os.mkdir('logs/')


def get_settings():
    config = configparser.ConfigParser()
    config.read('bot_data/config.ini')
    return dict(config)

