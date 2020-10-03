#!/usr/bin/python3
# -*- coding: utf-8 -*-
import requests
import vk_api
from pony.orm import db_session
from vk_api.bot_longpoll import VkBotEventType, VkBotLongPoll
import random
import logging
import handlers
from models import UserState, Registration

try:
    import settings
except ImportError:
    exit('Do cp settings.py.default settings.py and set token!')

log = logging.getLogger('bot')


def configure_logging():
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(logging.Formatter('%(levelname)s %(message)s'))
    stream_handler.setLevel(logging.INFO)
    log.addHandler(stream_handler)

    file_handler = logging.FileHandler('bot.log')
    file_handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s', datefmt='%d-%m-%Y %H:%M'))
    file_handler.setLevel(logging.DEBUG)
    log.addHandler(file_handler)

    log.setLevel(logging.DEBUG)


class Bot:
    """
    Echo bot для vk.com
    Use python3.8
    """

    def __init__(self, bot_token, group_id):
        """

        :param bot_token: group id из группы vk
        :param group_id: секретный токен
        """
        self.group_id = group_id
        self.token = bot_token
        self.vk = vk_api.VkApi(token=bot_token)
        self.long_poller = VkBotLongPoll(self.vk, self.group_id)
        self.api = self.vk.get_api()

    def run(self):
        """
        Запуск бота
        """
        for event in self.long_poller.listen():
            try:
                self.on_event(event)
            except Exception:
                log.exception('Ошибка в обработке события')

    @db_session
    def on_event(self, event):
        """
        Привествие пользователя после отправки им сообщения
        :param event: VkBotMessageEvent object
        :return: None
        """
        if event.type != VkBotEventType.MESSAGE_NEW:
            log.info('Мы пока не умеем обрабатывать события такого типа %s', event.type)
            return
        user_id = str(event.message.peer_id)
        text = event.message.text
        state = UserState.get(user_id=user_id)

        self.search_intent(text, user_id, state)

    def send_text(self, text_to_send, user_id):
        # Определение имени пользователя
        user_data = self.api.users.get(user_ids=user_id)
        user = user_data[0]['first_name']
        log.debug('Отправляем сообщение пользователю')
        self.api.messages.send(
            message=f'{user}, {text_to_send}',
            random_id=random.randint(0, 2 ** 20),
            peer_id=user_id)  # 'from_id': 8762922  peer_id': 8762922

    def send_image(self, image, user_id):
        upload_url = self.api.photos.getMessagesUploadServer()['upload_url']
        upload_data = requests.post(url=upload_url, files={'photo': ('image.png', image, 'image/png')}).json()
        image_data = self.api.photos.saveMessagesPhoto(**upload_data)
        owner_id = image_data[0]['owner_id']
        media_id = image_data[0]['id']
        attachment = f'photo{owner_id}_{media_id}'
        self.api.messages.send(
            attachment=attachment,
            random_id=random.randint(0, 2 ** 20),
            peer_id=user_id)
        log.info('Отправлен билет пользователю.')

    def send_step(self, step, user_id, context):
        if 'text' in step:
            self.send_text(step['text'].format(**context), user_id)
        if 'image' in step:
            handler = getattr(handlers, step['image'])
            image = handler(user_id, context)
            self.send_image(image, user_id)

    def search_intent(self, text, user_id, state):
        for intent in settings.INTENTS:
            log.debug(f'User gets {intent}')
            if any(token in text.lower() for token in intent['tokens']):
                if state is not None:
                    state.delete()
                if intent['answer']:
                    self.send_text(intent['answer'], user_id)
                else:
                    self.start_scenario(user_id, intent['scenario'])
                break
        else:
            if state is not None:
                self.continue_scenario(text, state, user_id)
            else:
                self.send_text(settings.DEFAULT_ANSWER, user_id)

    def start_scenario(self, user_id, scenario_name):
        scenario = settings.SCENARIOS[scenario_name]
        first_step = scenario['first_step']
        step = scenario['steps'][first_step]
        self.send_step(step, user_id, context={})
        UserState(user_id=user_id, scenario_name=scenario_name, step_name=first_step, context={})


    def continue_scenario(self, text, state, user_id):
        steps = settings.SCENARIOS[state.scenario_name]['steps']
        step = steps[state.step_name]
        handler = getattr(handlers, step['handler'])
        if handler(text=text, context=state.context):
            # next step
            next_step = steps[step['next_step']]
            self.send_step(next_step, user_id, state.context)
            if next_step['next_step']:
                # switch to next step
                state.step_name = step['next_step']
            else:
                # finish
                Registration(
                    user_id=user_id,
                    From=state.context['From'],
                    to=state.context['to'],
                    date=state.context['date'],
                    flight=state.context['flight'],
                    seats=state.context['seats'],
                    comment=state.context['comment'],
                    phone=state.context['phone'],
                )
                log.info('Забронированы билеты из города {From} в город {to} на {date}'.format(**state.context))
                state.delete()
        elif 'continue' in state.context:
            # failure finish
            text_to_send = step['finish'].format(**state.context)
            self.send_text(text_to_send, user_id)
            state.delete()
            log.info('Пользователь завершил сценарий, не купив билет')
        else:
            # retry current step
            text_to_send = step['failure_text'].format(**state.context)
            self.send_text(text_to_send, user_id)


if __name__ == '__main__':
    configure_logging()
    bot = Bot(settings.TOKEN, settings.GROUP_ID)
    bot.run()
