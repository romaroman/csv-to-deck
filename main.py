import time
from utils import get_logger
import requests
from bs4 import BeautifulSoup

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


def get_sentence(tag):
    return tag.get_text().replace("\n", "").replace("\r", "")


def extract_translation(tag):
    return ' '.join(tag.get_text().split(' ')[:-2])


def filter_sentence_tags(tags):
    for tag in tags:
        if len(tag.get_text().split(' ')) > 4:
            return tag


def get_soup(word):
    status_code = None
    sleep_time = 10
    time.sleep(5)
    while status_code != 200:
        if sleep_time == 50:
            return None

        if status_code:
            time.sleep(sleep_time)
            sleep_time += 10
            logger.debug(f"Got {status_code}. Waiting for {sleep_time} seconds.")

        word_parts = word.split(' ')
        if word_parts[0] in ['der', 'das', 'dir']:
            req_text = '+'.join(word_parts[1:])
        else:
            req_text = word.replace(' ', '+')
        req = requests.get(LINGUEE_URL.format(req_text))

        status_code = req.status_code
        if status_code != 200:
            logger.warning(f"Faced with request status code {status_code}")

    return BeautifulSoup(req.text, features="lxml")


def scrapp_info(word):

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

    result = [german_entry, german_sample_sentence, ' ', english_meaning, english_secondary_meanings,
              rough_english_sentence]
    logger.info(f"Scrapped\t{' | '.join(result)}")
    return result


def main():
    file = open('words.txt', 'r+')
    words = file.read().split('\n')
    csv = open('result.csv', 'w+')
    for word in words:
        info = scrapp_info(word)
        if info:
            csv.write(",".join(info) + '\n')
    file.close()
    csv.close()


if __name__ == '__main__':
    main()
