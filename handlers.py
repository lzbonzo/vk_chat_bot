#!/usr/bin/python3
# -*- coding: utf-8 -*-
import re
from datetime import datetime

from generate_ticket import TicketFiller
from settings import FLIGHTS


re_city = re.compile(r'\b([a-zA-Zа-яА-Я\s-]{4})[a-zA-Zа-яА-Я\s-]{0,40}\b')
re_date = re.compile(r'[0-3][0-9]-[01][0-9]-20[2-9][0-9]')
re_phone = re.compile(r'\b(\+7|8\d{10})\b')


def handle_maker_from_str_to_list(func):
    def handle(text, context):
        for word in text.split():
            if func(word, context):
                return True
    return handle


def handle_city_name(text, context, direction):
    match = re.findall(re_city, text)
    if match:
        cities = set()
        for city in FLIGHTS.values():
            for city_to in city.keys():
                cities.add(city_to)
        context['cities'] = ', '.join(cities)
        for city in cities:
            if match[0].capitalize() in city:
                context[direction] = city
                return True
    else:
        return False


@handle_maker_from_str_to_list
def handle_city_from(text, context):
    if handle_city_name(text, context, 'From'):
        return True


@handle_maker_from_str_to_list
def handle_city_to(text, context):
    if handle_city_name(text, context, 'to'):
        if context['to'] not in FLIGHTS[context['From']]:
            context['continue'] = False
            return False
        return True


def handle_date(text, context):
    match = re.findall(re_date, text)
    if match:
        flight_date = datetime.strptime(match[0], '%d-%m-%Y').date()
        current_date = datetime.today().date()
        if flight_date < current_date:
            return False
        context['date'] = match[0]
        flights = dispatcher(context)
        if not flights:
            context['continue'] = False
            return False
        context['flights_messages'] = flights
        return True


def dispatcher(context):
    date = context['date']
    date = datetime.strptime(date, '%d-%m-%Y').date()
    From = context['From']
    to = context['to']
    context['flights'] = {}
    messages = ''
    for flight in FLIGHTS[From][to]:
        flight_date = datetime.strptime(flight[0], '%d-%m-%Y').date()
        if flight_date >= date:
            context['flights'][flight[2]] = {}
            context['flights'][flight[2]]['date'] = flight[0]
            context['flights'][flight[2]]['time'] = flight[1]
            messages += f'Рейс: {flight[2]}. Дата: {flight[0]}. Время вылета: {flight[1]}\n'
    return messages


def handle_flights(text, context):
    match = re.findall(r'(\d{4})', text)
    if match:
        for key in context['flights'].keys():
            if match[0] in key:
                context['flight'] = key
                context['date'] = context['flights'][key]['date']
                context['time'] = context['flights'][key]['time']
                return True
    else:
        return False


def handle_seats(text, context):
    match = re.findall(r'([1-5])', text)
    if match:
        context['seats'] = match[0]
        return True
    else:
        return False


def handle_comment(text, context):
    context['comment'] = text
    return True


@handle_maker_from_str_to_list
def handle_data(text, context):
    if text.lower() in ["да", "ага", "угу", "йес", "ок", "lf", "yes", "так точно"]:
        return True
    if text.lower() in ["нет", "неа", "no", "nein", "отнюдь", "не", "не точно", ]:
        context['continue'] = False
    return False


def handle_phone(text, context):
    match = re.findall(re_phone, text)
    if match:
        context['phone'] = match[0]
        return True
    else:
        return False


def generate_ticket_handler(user_id, context):
    return TicketFiller(user_id, context).make()
