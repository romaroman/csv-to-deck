import scrappers
import argparse
import helpers


def init_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument("square", type=int,
                        help="display a square of a given number")
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="increase output verbosity")
    # separator default = ';'
    # timeout default = 0
    # source default = reverso
    # input
    # output
    # write failed files = False
    # log to file default = False
    return parser


def main(write_failed):
    words_file = open('failed_words.txt', 'r+', encoding='utf8')
    failed = open('failed.txt', 'w+', encoding='utf8')
    csv = open('result.csv', 'w+', encoding='utf8')

    words = words_file.read().split('\n')
    for word in words:
        # info = scrap_linguee(word)
        # info = scrap_wiktionary(word)
        # info = scrap_dictcc(word)
        info = scrappers.scrap_reverso(word)
        if info:
            csv.write(";".join([x.replace(';', '') for x in info]) + '\n')
            logger.info(f"Scrapped from Wiktionary\t{' | '.join(info)}")
        else:
            logger.warning(f"Skipped word\t{word}")
            if write_failed:
                failed.write(word + '\n')

    csv.close()
    failed.close()
    words_file.close()


if __name__ == '__main__':
    parser = init_parser()

    logger = helpers.get_logger(__name__, )

    main(args)