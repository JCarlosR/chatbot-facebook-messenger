# encoding: utf-8
import webapp2
import json
import logging
from google.appengine.api import urlfetch
from bot import Bot
import yaml
from user_events import UserEventsDao

VERIFY_TOKEN = "facebook_verification_token"
ACCESS_TOKEN = "EAAaefMWG2akBAAZAX0Xg50SVmMYjOUVY3OILcqjUjjxeFHZAfKVAVoDJZBS0Xa9QetaOAdhBmyDGWYTmQH96vwmSllqTviBpsGsS7zeLNQcL67UtDZCJSc0MZBmO9ZBtZCqlDWQZCClH6ClN8s49XFd57ZCpwktH6aciNYZCPu7xYEhgZDZD"

class MainPage(webapp2.RequestHandler):
    def __init__(self, request=None, response=None):
        super(MainPage, self).__init__(request, response)
        logging.info("Instanciando bot")
        tree = yaml.load(open('tree.yaml'))
        logging.info("Tree: %r", tree)
        self.bot = Bot(send_message, UserEventsDao(), tree)
        # dao = UserEventsDao()
        # dao.add_user_event("123", "user", "abc")
        # dao.add_user_event("123", "bot", "def")
        # dao.add_user_event("123", "user", "ghi")
        # dao.add_user_event("123", "bot", "jkl")
        # dao.add_user_event("123", "user", "mnñ")
        # data = dao.get_user_events("123")
        # logging.info("eventos: %r", data)
        # dao.remove_user_events("123")

    def get(self):
        self.response.headers['Content-Type'] = 'text/plain'
        mode = self.request.get("hub.mode")
        if mode == "subscribe":
            challenge = self.request.get("hub.challenge")
            verify_token = self.request.get("hub.verify_token")
            if verify_token == VERIFY_TOKEN:
                self.response.write(challenge)
        else:
            self.response.write("Ok")
            # self.bot.handle(0, "message_text")

    def post(self):
        logging.info("Data obtenida desde Messenger: %s", self.request.body)
        data = json.loads(self.request.body)

        if data["object"] == "page":

            for entry in data["entry"]:
                for messaging_event in entry["messaging"]:
                    sender_id = messaging_event["sender"]["id"]
                    recipient_id = messaging_event["recipient"]["id"]

                    if messaging_event.get("message"):
                        is_admin = False
                        message = messaging_event['message']
                        if message.get('is_echo'):
                            if message.get('app_id'): # bot
                                continue
                            else: # admin
                                # el bot se debe desactivar
                                is_admin = True

                        message_text = message.get('text', '')
                        logging.info("Message: %s", message_text)
                        
                        # bot handle
                        if is_admin:
                            user_id = recipient_id
                        else:                        
                            user_id = sender_id

                        self.bot.handle(user_id, message_text, is_admin)

                    if messaging_event.get("postback"):
                        message_text = messaging_event['postback']['payload']
                        # bot handle                        
                        self.bot.handle(sender_id, message_text)                        
                        logging.info("Post-back: %s", message_text)

def send_message(recipient_id, message_text, possible_answers):

    headers = {
        "Content-Type": "application/json"
    }

    # max buttons quantity: 3
    # max recommended answer length: 20
    valid_possible_answers = possible_answers is not None and len(possible_answers) <= 3
    if valid_possible_answers:
        message = get_postback_buttons_message(message_text, possible_answers)
    elif message_text.startswith('https'):
        message = get_url_buttons_message(message_text)
    else:
        message = {"text": message_text}

    raw_data = {
        "recipient": {
            "id": recipient_id
        },
        "message": message
    }
    data = json.dumps(raw_data)

    logging.info("Enviando mensaje a %r: %s", recipient_id, message_text)

    r = urlfetch.fetch("https://graph.facebook.com/v2.6/me/messages?access_token=%s" % ACCESS_TOKEN,
                       method=urlfetch.POST, headers=headers, payload=data)
    if r.status_code != 200:
        logging.error("Error %r enviando mensaje: %s", r.status_code, r.content)

def get_postback_buttons_message(message_text, possible_answers):
    buttons = []
    for answer in possible_answers:
        buttons.append({
            "type": "postback",
            "title": answer,
            "payload": answer           
        })

    return get_buttons_template(message_text, buttons)

def get_url_buttons_message(message_text):
    # urls = message_text.split()
    elements = []
    elements.append({
        "url": message_text
    })
    return get_open_graph_template(elements)


def get_buttons_template(message_text, buttons):
    return {
        "attachment": {
            "type": "template",
            "payload": {
                "template_type": "button",
                "text": message_text,
                "buttons": buttons
            }
        }
    }

def get_open_graph_template(elements):
    return {
        "attachment": {
            "type": "template",
            "payload": {
                "template_type": "open_graph",
                "elements": elements
            }
        }
    }    

class PrivacyPolicyPage(webapp2.RequestHandler):
    def get(self):
        self.response.headers['Content-Type'] = 'text/html'        
        htmlContent = open('privacy_policy.html').read()
        self.response.write(htmlContent)


app = webapp2.WSGIApplication([
    ('/', MainPage),
    ('/privacy-policy', PrivacyPolicyPage)
], debug=True)
