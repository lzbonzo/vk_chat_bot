from copy import deepcopy
from unittest import TestCase
from unittest.mock import patch, Mock
from pony.orm import db_session, rollback
from vk_api.bot_longpoll import VkBotMessageEvent
from bot import Bot
import settings
import handlers
from generate_ticket import TicketFiller
from freezegun import freeze_time


def isolate_db(test_func):
    def wrapper(*args, **kwargs):
        with db_session:
            test_func(*args, **kwargs)
            rollback()
    return wrapper


class Test1(TestCase):
    INPUTS = [
        'Привет',
        'Хочу купить билет.',
        'Самара',
        'Москва',
        '20-09-2020',
        'FL-SB 2504',
        '5',
        'Хочу сидеть у окна',
        'Да',
        '89099091234'
    ]

    EXPECTED_OUTPUTS = [
        'Роман, ' + settings.INTENTS[1]['answer'],
        'Роман, ' + settings.SCENARIOS['buy_ticket']['steps']['step_1']['text'],
        'Роман, ' + settings.SCENARIOS['buy_ticket']['steps']['step_2']['text'],
        'Роман, ' + settings.SCENARIOS['buy_ticket']['steps']['step_3']['text'],
        'Роман, ' + settings.SCENARIOS['buy_ticket']['steps']['step_4']['text'].format(
            flights_messages='Рейс: FL-SB 2404. '
                             'Дата: 20-09-2020. '
                             'Время вылета: 08:00\n'
                             'Рейс: FL-SB 2504. '
                             'Дата: 25-09-2020. '
                             'Время вылета: 06:00\n'),
        'Роман, ' + settings.SCENARIOS['buy_ticket']['steps']['step_5']['text'],
        'Роман, ' + settings.SCENARIOS['buy_ticket']['steps']['step_6']['text'],
        'Роман, ' + settings.SCENARIOS['buy_ticket']['steps']['step_7']['text'].format(From='Самара', to='Москва',
                                                                                       date='25-09-2020',
                                                                                       flight='FL-SB 2504',
                                                                                       seats='5',
                                                                                       comment='Хочу сидеть у окна'),
        'Роман, ' + settings.SCENARIOS['buy_ticket']['steps']['step_8']['text'],
        'Роман, ' + settings.SCENARIOS['buy_ticket']['steps']['step_9']['text']
    ]
    RAW_EVENT = {
        'type': 'message_new',
        'object': {
            'message': {'date': 1599085013, 'from_id': 8762922, 'id': 169, 'out': 0, 'peer_id': 8762922,
                        'text': 'Some message from user', 'conversation_message_id': 170, 'fwd_messages': [],
                        'important': False,
                        'random_id': 0, 'attachments': [], 'is_hidden': False},
            'client_info': {'button_actions': ['text', 'vkpay', 'open_app', 'location', 'open_link'], 'keyboard': True,
                            'inline_keyboard': True, 'carousel': False, 'lang_id': 0}},
        'group_id': 166499281,
        'event_id': '7acac3ca2f9523bf33d92094323f0dd78e05bc71'}

    USER_DATA = [{'id': 8762922, 'first_name': 'Роман',
                  'last_name': 'Аллабердин', 'is_closed': False, 'can_access_closed': True}]

    INPUT_CONTEXT = {
        'From': 'Самара',
        'to': 'Москва',
        'date': '25-09-2020',
        'flight': 'FL-SB 2504',
        'flights': {'FL-SB 2504': {'date': '25-09-2020', 'time': '06:00'}},
        'seats': '5',
        'comment': 'Хочу сидеть у окна',
        'phone': '89099091234'
    }

    def test_run(self):
        count = 5
        obj = {}
        events = [obj] * count
        long_poller_mock = Mock(return_value=events)
        long_poller_listen_mock = Mock()
        long_poller_listen_mock.listen = long_poller_mock
        with patch('bot.vk_api.VkApi'):
            with patch('bot.VkBotLongPoll', return_value=long_poller_listen_mock):
                bot = Bot('', '')
                bot.on_event = Mock()
                bot.send_image = Mock()
                bot.run()
                bot.on_event.assert_called()
                bot.on_event.assert_any_call(obj)
                assert bot.on_event.call_count == count

    @isolate_db
    def test_run_ok(self):
        send_mock = Mock()
        api_mock = Mock()
        api_mock.messages.send = send_mock
        get_mock = Mock(return_value=self.USER_DATA)

        events = []
        for input_text in self.INPUTS:
            event = deepcopy(self.RAW_EVENT)
            event['object']['message']['text'] = input_text
            events.append(VkBotMessageEvent(event))

        long_poller_mock = Mock()
        long_poller_mock.listen = Mock(return_value=events)

        with patch('bot.VkBotLongPoll', return_value=long_poller_mock):
            bot = Bot('', '')
            bot.api = api_mock
            bot.api.users.get = get_mock
            bot.send_image = Mock()
            bot.run()
        assert send_mock.call_count == len(self.INPUTS)

        real_outputs = []

        for call in send_mock.call_args_list:
            args, kwargs = call
            real_outputs.append(kwargs['message'])
        assert real_outputs == self.EXPECTED_OUTPUTS

    def test_handle_city(self):
        context = {}
        is_city = handlers.handle_city_name('ньЮ-Йорке', context, 'From')
        assert is_city is True
        assert context['From'] == 'Нью-Йорк'

    @freeze_time("Sep 16th, 2020")
    def test_ticket_generation(self):
        with open('files/8762922@adorable.png', 'rb') as avatar_file:
            avatar_mock = Mock()
            avatar_mock.content = avatar_file.read()
        with patch('requests.get', return_value=avatar_mock):
            ticket_file = TicketFiller('8762922', self.INPUT_CONTEXT).make()
        with open('files/ticket_example.png', 'rb') as expected_file:
            expected_bytes = expected_file.read()
        assert ticket_file.read() == expected_bytes
