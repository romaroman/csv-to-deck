import time
from google.cloud import translate_v3beta1 as translate
from helpers import get_logger
import requests
from bs4 import BeautifulSoup
from wiktionaryparser import WiktionaryParser
import re
import os


os.environ['GOOGLE_APPLICATION_CREDENTIALS']='.google/default-ce-d2e59ab3fd13.json'
translate_client = translate.TranslationServiceClient()
logger = get_logger(__name__)
wiktionary_parser = WiktionaryParser()
wiktionary_parser.set_default_language('english')


def get_sentence(tag):
    return tag.get_text().replace("\n", "").replace("\r", "")


def extract_translation(tag):
    return ' '.join(tag.get_text().split(' ')[:-2])


def filter_sentence_tags(tags):
    for tag in tags:
        if len(tag.get_text().split(' ')) > 4:
            return tag


def filter_word(word, filter_parts=None):
    if filter_parts is None:
        filter_parts = ['articles']
    parts = {
        'articles': ['der', 'das', 'dir', 'die', 'dem', 'den', 'diese', 'diesem'],
        'prepositions': ['aus', 'für', 'bis', 'in', 'vor', 'an', 'mit', 'über', 'unter', 'nach', 'seit', 'von', 'zu', 'bei', 'nach', 'um']
    }
    filter_set = set()
    for part, words in parts.items():
        if part in filter_parts:
            filter_set.update(words)
    return ' '.join([part for part in word.split(' ') if part not in filter_set])


def format_sentence(sentence):
    return re.sub(r'[;\-"«»\[\]]', '', sentence.strip()) + '.'


def get_soup(word, url, symbol=None):
    delay, o_delay = 0, 2
    status_code = None
    headers = {
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Ubuntu Chromium/75.0.3770.90 Chrome/75.0.3770.90 Safari/537.36'
    }

    while status_code != 200:
        if delay == o_delay * 10:
            return None

        if status_code:
            delay += o_delay
            time.sleep(delay)
            logger.debug(f"Got {status_code}. Waiting for {delay} seconds.")

        if symbol:
            word = word.replace(' ', symbol)
        request = requests.get(url=url.format(word), headers=headers)

        status_code = request.status_code
        if status_code != 200:
            logger.warning(f"Faced with request status code {status_code}")

    return BeautifulSoup(request.text, features="html5lib")


def scrap_dictcc(word):
    dictcc_url = 'https://www.dict.cc/german-english/{}.html'
    soup = get_soup(word, dictcc_url, '+')
    german_entry = word
    german_sample_sentence, rough_english_sentence, english_meaning, english_secondary_meanings = [''] * 4
    return [german_entry, german_sample_sentence, ' ', english_meaning, english_secondary_meanings,
            rough_english_sentence]


def strip_tag(tag):
    return tag.text.strip()


def scrap_reverso(word):
    german_entry = word
    german_sample_sentence, rough_english_sentence, english_meaning, english_secondary_meanings = [''] * 4

    reverso_url = 'https://context.reverso.net/translation/german-english/{}'
    request_text = word.replace(' ', '+')

    variants = list(dict.fromkeys(
        [
            filter_word(word, ['articles']).replace(' ', '+'),
            filter_word(word, ['articles', 'prepositions']).replace(' ', '+'),
            request_text,
            request_text.capitalize(),
            request_text.lower(),
        ]
    ).keys())

    warning_message = f"Couldn't find appropriate variant for {word} with Reverso.Context. Tried {', '.join(variants)}"

    while True:
        variant = variants.pop(0)
        soup = BeautifulSoup(requests.get(reverso_url.format(variant), headers={
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Ubuntu Chromium/75.0.3770.90 Chrome/75.0.3770.90 Safari/537.36'
        }).text, "lxml")

        button = soup.find("button", {"data-index": "0"})
        if not button:
            english_meanings_tags = soup.findAll("div", {"class": "translation ltr dict no-pos"})
            if len(english_meanings_tags) == 0 and len(variants) == 0:
                logger.warning(warning_message)
                return None
        else:
            attribute = button.attrs['data-pos'].replace('.', '')
            first_meaning_tag = soup.find("a", {"class": f"translation ltr dict first {attribute}"})
            other_meanings_tags = soup.findAll("a", {"class": f"translation ltr dict {attribute}"})
            other_meanings_tags += soup.findAll("a", {"class": "translation ltr dict no-pos"})
            if not first_meaning_tag:
                english_meanings_tags = other_meanings_tags
            else:
                english_meanings_tags = [first_meaning_tag] + other_meanings_tags

        if len(english_meanings_tags) > 0:
            break

        elif len(english_meanings_tags) == 0 and len(variants) == 0:
            logger.warning(warning_message)
            return None

    german_sample_sentences_tags = soup.findAll("div", {"class": "src ltr"})
    rough_english_sentences_tags = soup.findAll("div", {"class": "trg ltr"})

    if len(german_sample_sentences_tags) == 0 or len(rough_english_sentences_tags) == 0 or len(english_meanings_tags) == 0:
        logger.warning(warning_message)
        return None

    for german_sample_sentence_tag, rough_english_sentence_tag in zip(german_sample_sentences_tags, rough_english_sentences_tags):
        german_sample_sentence = strip_tag(german_sample_sentence_tag)
        rough_english_sentence = strip_tag(rough_english_sentence_tag)
        if len(german_sample_sentence.split(' ')) >= 3 and len(rough_english_sentence.split(' ')) >= 3:
            break

    english_meanings = [strip_tag(english_meaning_tag) for english_meaning_tag in english_meanings_tags]

    english_meaning = english_meanings[0]
    english_secondary_meanings = ', '.join(english_meanings[1:5])

    return [german_entry, german_sample_sentence, ' ', english_meaning, english_secondary_meanings, rough_english_sentence]


def scrap_linguee(word):
    linguee_url = 'https://www.linguee.com/english-german/search?source=german&query={}'
    soup = get_soup(filter_word(word), linguee_url, '+')
    german_entry = word

    german_sentence_tags = soup.findAll("span", {"class": "tag_s"})
    english_sentence_tags = soup.findAll("span", {"class": "tag_t"})
    english_meaning_tags = list(reversed(soup.findAll("span", {"class": "tag_trans"})))

    if not german_sentence_tags or not english_sentence_tags or not english_meaning_tags:
        return None

    german_sample_sentence = get_sentence(filter_sentence_tags(german_sentence_tags))
    rough_english_sentence = get_sentence(filter_sentence_tags(english_sentence_tags))

    translation_limit = 4
    english_meanings = []
    while translation_limit != 0 and english_meaning_tags:
        english_meanings.append(extract_translation(english_meaning_tags.pop()))
        translation_limit -= 1

    english_meaning = english_meanings[0]
    english_secondary_meanings = ', '.join(english_meanings[1:])

    return [german_entry, german_sample_sentence, ' ', english_meaning, english_secondary_meanings,
            rough_english_sentence]


def scrap_wiktionary(word):
    german_entry = word
    german_sample_sentence, rough_english_sentence, english_meaning, english_secondary_meanings = [''] * 4

    request_text = word.replace(' ', '_')
    variants = [
        request_text,
        request_text.capitalize(),
        request_text.lower(),
    ]

    definitions = []
    for variant in variants:
        fetch = wiktionary_parser.fetch(variant, 'german')
        if len(fetch) > 0:
            definitions = fetch[0]['definitions']
            if len(definitions) > 0:
                break

    if len(definitions) == 0:
        return None

    fetched_sentences, fetched_meanings = False, False
    english_meanings = []

    for definition in definitions:
        if not fetched_sentences:
            if 'examples' in definition.keys():
                examples = definition['examples']
                for example in examples:
                    sentences = list(filter(lambda x: len(x.split(' ')) > 2, example.split('.')))

                    if len(sentences) == 2:
                        german_sample_sentence, rough_english_sentence = format_sentence(sentences[0]), format_sentence(
                            sentences[1])
                        fetched_sentences = True
                        break

        if not fetched_meanings:
            if 'text' in definition.keys():
                possible_meanings = definition['text'][1:]
                for possible_meaning in possible_meanings:
                    if fetched_meanings:
                        break
                    meanings = re.split(r'[,;\-!?]', (re.sub(r'\([^)]*\)', '', possible_meaning)))
                    for meaning in meanings:
                        clean_meaning = re.sub(r'([^\s\w]|_)+', '', meaning).strip()
                        if clean_meaning not in english_meanings:
                            english_meanings.append(clean_meaning)
                            if len(english_meanings) == 4:
                                fetched_meanings = True
                                break

        if fetched_sentences and fetched_meanings:
            break

    english_meaning, english_secondary_meanings = english_meanings[0], ', '.join(english_meanings[1:])

    return [german_entry, german_sample_sentence, ' ', english_meaning, english_secondary_meanings,
            rough_english_sentence]


def translate_with_google_api(entry):
    result = translate_client.translate_text([entry], target_language_code='en')
    return result


if __name__ == '__main__':
    print(translate_with_google_api('gehen'))