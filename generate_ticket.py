import os
from datetime import datetime
from io import BytesIO

import requests
from PIL import ImageDraw, ImageFont, Image


class TicketFiller:

    TEMPLATE_PATH = os.path.join('files', 'ticket_template.png')
    TICKET_EXAMPLE_PATH = os.path.join('files', 'ticket_example')
    FONT_PATH = os.path.join('files', 'Microsoft Sans Serif.ttf')
    FONT_SIZE = 40
    FONT_COMMENT_SIZE = 30

    BLACK = (0, 0, 0, 255)
    FLIGHT_OFFSET = (400, 468)
    FROM_OFFSET = (400, 518)
    TO_OFFSET = (400, 568)
    DATE_OFFSET = (400, 618)
    TIME_OFFSET = (700, 618)
    SEATS_OFFSET = (550, 665)
    COMMENT_OFFSET = (500, 718)
    PHONE_OFFSET = (450, 810)
    CURRENT_DATE_OFFSET = (550, 860)

    AVATAR_SIZE = 171
    AVATAR_OFFSET = (60, 344)

    def __init__(self, user_id, context):
        self.user_id = user_id
        self.from_ = context['From']
        self.to = context['to']
        self.date = context['date']
        self.flight = context['flight']
        self.time = context['flights'][self.flight]['time']
        self.seats = context['seats']
        self.comment = context['comment']
        self.phone = context['phone']

    def make(self):
        ticket = Image.open(self.TEMPLATE_PATH)
        draw = ImageDraw.Draw(ticket)
        font = ImageFont.truetype(self.FONT_PATH, size=self.FONT_SIZE)
        font_comment = ImageFont.truetype(self.FONT_PATH, size=self.FONT_COMMENT_SIZE)
        # Flight
        draw.text(self.FLIGHT_OFFSET, self.flight, font=font, fill='black')
        # From
        draw.text(self.FROM_OFFSET, self.from_, font=font, fill='black')
        # To
        draw.text(self.TO_OFFSET, self.to, font=font, fill='black')
        # Date
        draw.text(self.DATE_OFFSET, self.date, font=font, fill='black')
        # Time
        draw.text(self.TIME_OFFSET, self.time, font=font, fill='black')
        # Seats
        draw.text(self.SEATS_OFFSET, self.seats, font=font, fill='black')
        # Comment
        draw.text(self.COMMENT_OFFSET, self.comment, font=font_comment, fill='black')
        # Phone
        draw.text(self.PHONE_OFFSET, self.phone, font=font, fill='black')
        # current date
        current_date = datetime.now().strftime('%d-%m-%Y')
        draw.text(self.CURRENT_DATE_OFFSET, current_date, font=font, fill='black')
        self.avatar(ticket)
        temp_file = BytesIO()
        ticket.save(temp_file, 'png')
        temp_file.seek(0)
        return temp_file

    def avatar(self, ticket):
        response = requests.get(url=f'https://api.adorable.io/avatars/{self.AVATAR_SIZE}/{self.user_id}@adorable.png')
        avatar_file_like = BytesIO(response.content)
        avatar = Image.open(avatar_file_like)
        ticket.paste(avatar, self.AVATAR_OFFSET)
