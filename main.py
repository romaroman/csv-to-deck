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

def scrapp_info(word):
    req = requests.get(LINGUEE_URL.format(word.replace(' ', '+')))

    soup = BeautifulSoup(req.text, features="lxml")
    german_entry = word
    german_sample_sentences = soup.findAll("div", {"class": "wrap"})
    german_sample_sentences[0].get_text().strip('\n').split('.')
    german_sample_sentence = []
    return []


def main():
    file = open('words2.txt', 'r+')
    words = file.read().split('\n')
    csv = open('result2.csv', 'w+')
    for word in words:
        info = ",".join(scrapp_info(word))
        csv.write(info + '\n')



if __name__ == '__main__':
    main()
