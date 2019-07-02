import time
from helpers import get_logger
import requests
from bs4 import BeautifulSoup
from wiktionaryparser import WiktionaryParser
import re

columns = [
    'GermanEntry',
    'GermanSampleSentence',
    'Image',
    'EnglishMeaning',
    'SecondaryEnglishMeaning',
    'RoughEnglishSentence'
]
LINGUEE_URL = 'https://www.linguee.com/english-german/search?source=german&query={}'
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


def filter_word(word):
    articles = ['der', 'das', 'dir', 'die', 'dem', 'den', 'diese', 'diesem']
    prepositions = ['aus', 'für', 'bis', 'in', 'vor', 'an', 'mit', 'über', 'unter', 'nach', 'seit', 'von', 'zu', 'bei',
                    'nach', 'um']

    return ' '.join([part for part in word.split(' ') if part not in articles + prepositions])


def word_to_request(word, destination='Linguee'):
    return word.replace(
        ' ',
        {
            'Linguee': '+',
            'Wiktionary': '_'
        }[destination]
    )


def get_soup(word):
    delay, o_delay = 0, 3
    status_code = None

    while status_code != 200:
        if delay == 30:
            return None

        if status_code:
            delay += o_delay
            time.sleep(delay)
            logger.debug(f"Got {status_code}. Waiting for {delay} seconds.")

        request_text = word_to_request(word, destination='Linguee')
        request = requests.get(LINGUEE_URL.format(request_text))

        status_code = request.status_code
        if status_code != 200:
            logger.warning(f"Faced with request status code {status_code}")

    return BeautifulSoup(request.text, features="lxml")


def scrap_linguee(word):
    soup = get_soup(word)
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

    return [german_entry, german_sample_sentence, ' ', english_meaning, english_secondary_meanings, rough_english_sentence]


def scrap_wiktionary(word):
    time.sleep(2)
    german_entry = word
    german_sample_sentence, rough_english_sentence, english_meaning, english_secondary_meanings = [''] * 4


    # CHANGE IT!
    request_text = word_to_request(word, destination='Wiktionary')
    variants = [
        request_text,
        request_text.capitalize(),
        request_text.lower(),
    ]
    definitions = []

    for variant in variants:
        definitions = wiktionary_parser.fetch(variant, 'german')[0]['definitions']
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
                    sentences = list(filter(lambda x: len(x.split(' ')) > 2,  example.split('.')))

                    if len(sentences) == 2:
                        german_sample_sentence, rough_english_sentence = sentences[0] + '.', sentences[1] + '.'
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

    return [german_entry, german_sample_sentence, ' ', english_meaning, english_secondary_meanings, rough_english_sentence]


def main(write_failed):
    words_file = open('words.txt', 'r+')
    words = words_file.read().split('\n')
    words_file.close()

    failed_words = []

    csv = open('result.csv', 'w+')
    for word in words:
        # info = scrap_linguee(filter_word(word))
        info = scrap_wiktionary(filter_word(word))
        if info:
            csv.write(",".join(info) + '\n')
            logger.info(f"Scrapped from Wiktionary\t{' | '.join(info)}")
        else:
            logger.warning(f"Skipped word\t{word}")
            failed_words.append(word)
    csv.close()

    if write_failed:
        failed = open('failed.txt', 'w+')
        for failed_word in failed_words:
            failed.write(failed_word + '\n')
        failed.close()


if __name__ == '__main__':
    main(write_failed=True)
