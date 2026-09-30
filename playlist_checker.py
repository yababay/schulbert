from yargy import Parser, rule, or_
from yargy.predicates import gram
from yargy.pipelines import morph_pipeline
from yargy.interpretation import fact

# 1. МАТЕМАТИЧЕСКИЕ ВЫЧИСЛЕНИЯ (PYTHON)
# Простой плоский справочник базовых значений (в начальной форме)

SINGLE_PART_THOUSANDS_VALUES = {
    'тысяча': 1000, 'тысячный': 1000, 
    'двухтысячный': 2000, 'трехтысячный': 3000, 'четырехтысячный': 4000, 'пятитысячный': 5000, 
    'шеститысячный': 6000, 'семитысячный': 7000, 'восьмитысячный': 8000, 'девятитысячный': 9000,
}

PLAIN_NUMBER_VALUES = {
    'ноль': 0, 'один': 1, 'два': 2, 
    'одна': 1, 'две': 2, 'три': 3, 'четыре': 4, 'пять': 5, 'шесть': 6, 'семь': 7, 'восемь': 8, 'девять': 9,
    'десять': 10, 'одиннадцать': 11, 'двенадцать': 12, 'тринадцать': 13, 'четырнадцать': 14, 'пятнадцать': 15,
    'шестнадцать': 16, 'семнадцать': 17, 'восемнадцать': 18, 'девятнадцать': 19,
    'двадцать': 20, 'тридцать': 30, 'сорок': 40, 'пятьдесят': 50, 'шестьдесят': 60, 'семьдесят': 70, 'восемьдесят': 80, 'девяносто': 90,
    'сто': 100, 'двести': 200, 'триста': 300, 'четыреста': 400, 'пятьсот': 500, 'шестьсот': 600, 'семьсот': 700, 'восемьсот': 800, 'девятьсот': 900,
}

ADJECTIVE_NUMBER_VALUES = {
    'один': 1, # странно, но это так
    'первый': 1, 'второй': 2, 'третий': 3, 'четвертый': 4, 'пятый': 5, 'шестой': 6, 'седьмой': 7, 'восьмой': 8, 'девятый': 9,
    'десятый': 10, 'одиннадцатый': 11, 'двенадцатый': 12, 'тринадцатый': 13, 'четырнадцатый': 14, 'пятнадцатый': 15,
    'шестнадцатый': 16, 'семнадцатый': 17, 'восемнадцатый': 18, 'девятнадцатый': 19,
    'двадцатый': 20, 'тридцатый': 30, 'сороковой': 40, 'пятидесятый': 50,
    'шестидесятый': 60, 'семидесятый': 70, 'восьмидесятый': 80, 'девяностый': 90,
    'сотый': 100, 'двухсотый': 200, 'трехсотый': 300, 'четырехсотый': 400, 'пятисотый': 500,
    'шестисотый': 600, 'семисотый': 700, 'восьмисотый': 800, 'девятисотый': 900
}

ALL_NUMBER_VALUES = PLAIN_NUMBER_VALUES | ADJECTIVE_NUMBER_VALUES

# 2. ЛЕКСИЧЕСКИЙ АНАЛИЗ (YARGY)

# Нам не нужно перечислять сотни слов. gram('NUMR') находит ЛЮБЫЕ числительные в любых грамматических формах.
NUMBER_WORD = gram('NUMR')

PLAIN_SUM_MARKERS = or_ (
    NUMBER_WORD.repeatable(max=3),
    rule(
        NUMBER_WORD.repeatable(max=2).optional(),
        morph_pipeline(list(ADJECTIVE_NUMBER_VALUES.keys()))
    )
)

PLAYLIST_MARKERS = morph_pipeline(['плейлист', 'плэй', 'лист'])

THAUSAND_MARKERS = or_(
    rule(
        morph_pipeline(list(SINGLE_PART_THOUSANDS_VALUES.keys())),
    ),
    rule(
        NUMBER_WORD,
        morph_pipeline(['тысяча', 'тысяч'])
    )
)

PlaylistPhrase = fact(
    'PlaylistPhrase',
    [
        'is_playlist',
        'thousands',
        'plain_sum'
    ]
)

PLAYLIST_RULE = rule(
    PLAYLIST_MARKERS.interpretation(PlaylistPhrase.is_playlist),
    or_ (
        rule(
            THAUSAND_MARKERS.interpretation(PlaylistPhrase.thousands),
            PLAIN_SUM_MARKERS.repeatable(max=3).interpretation(PlaylistPhrase.plain_sum)
        ),
        rule(
            PLAIN_SUM_MARKERS.repeatable(max=3).interpretation(PlaylistPhrase.plain_sum)
        ),
        rule(
            THAUSAND_MARKERS.interpretation(PlaylistPhrase.thousands),
        ),
    )
).interpretation(PlaylistPhrase)

# Инициализируем оригинальный парсер yargy
playlist_parser = Parser(PLAYLIST_RULE)

def split_phrase(text):
    clean_text = " ".join(text.lower().split())
    
    match = playlist_parser.find(clean_text)

    if not match:
        raise ValueError('Phrase is not found')

    return match.fact
def check_playlist_phrase(text):
    """
    Главная точка входа для конвейера. 
    Возвращает номер плейлиста (int) или None, если маркер плейлиста не обнаружен.
    """
    try:
        # Проверяем, есть ли вообще маркеры плейлиста в тексте, чтобы не гонять парсер зря
        if not any(m in text.lower() for m in ['плейлист', 'плэй', 'лист']):
            return None

        phrase = split_phrase(text)
        total_sum = 0

        if phrase.thousands:
            words = phrase.thousands.split(' ')
            valuable = words[0]
            if len(words) == 1:
                total_sum = SINGLE_PART_THOUSANDS_VALUES.get(valuable, 0)
            else:
                total_sum = ALL_NUMBER_VALUES.get(valuable, 0) * 1000
                
        if not phrase.plain_sum:
            return int(total_sum) if total_sum > 0 else None

        words = phrase.plain_sum.split(' ')   
        for word in words:
            value = ALL_NUMBER_VALUES.get(word, 0)
            total_sum += value

        return int(total_sum) if total_sum > 0 else None
    except Exception:
        return None

import unittest

class TestCheckPlaylistPhrase(unittest.TestCase):

    """
    Корректность парсинга
    """

    def test_splitting_1(self):
        phrase = split_phrase('загрузи плэй лист один')
        self.assertEqual(phrase.thousands, None)
        self.assertEqual(phrase.plain_sum, 'один')
        phrase = split_phrase('загрузи плэй лист первый')
        self.assertEqual(phrase.thousands, None)
        self.assertEqual(phrase.plain_sum, 'первый')

    def test_splitting_2(self):
        phrase = split_phrase('загрузи плэй лист два')
        self.assertEqual(phrase.thousands, None)
        self.assertEqual(phrase.plain_sum, 'два')
        phrase = split_phrase('загрузи плэй лист второй')
        self.assertEqual(phrase.thousands, None)
        self.assertEqual(phrase.plain_sum, 'второй')

    def test_splitting_777(self):
        phrase = split_phrase('загрузи плэй лист семьсот семьдесят семь')
        self.assertEqual(phrase.thousands, None)
        self.assertEqual(phrase.plain_sum, 'семьсот семьдесят семь')

    def test_splitting_1000(self):

        phrase = split_phrase('загрузи плэй лист тысяча')
        self.assertTrue(phrase.thousands.startswith('тысяч'))
        self.assertIsNone(phrase.plain_sum)

        phrase = split_phrase('загрузи плэй лист тысячный')
        self.assertTrue(phrase.thousands.startswith('тысяч'))
        self.assertIsNone(phrase.plain_sum)

    def test_splitting_2777(self):
        phrase = split_phrase('загрузи плэй лист две тысячи семьсот семьдесят семь')
        self.assertEqual(phrase.thousands, 'две тысячи')

    def test_splitting_error(self):
        text = 'хорошая погода, не правда ли'
        self.assertRaises(ValueError, split_phrase, text)
    
    """
    Преобразование текста в число.
    """

    def check_prefixes(self, postfix, value):
        request_prefix_1 = "загрузи плейлист"
        request_prefix_2 = "загрузи плэй лист"
        self.assertEqual(check_playlist_phrase(request_prefix_1 + " " + postfix), value)
        self.assertEqual(check_playlist_phrase(request_prefix_1 + " " + postfix), value)

    def test_t2n_2777(self):
        self.assertEqual(check_playlist_phrase('загрузи плэй лист две тысячи семьсот семьдесят семь'), 2777)

    def test_t2n_1(self):
        self.check_prefixes('один', 1)
        self.check_prefixes('первый', 1)

    def test_t2n_2(self):
        self.check_prefixes('два', 2)
        self.check_prefixes('второй', 2)

    def test_t2n_11(self):
        self.check_prefixes('одиннадцать', 11)
        self.check_prefixes('одиннадцатый', 11)

    def test_t2n_50(self):
        self.check_prefixes('пятьдесят', 50)
        self.check_prefixes('пятидесятый', 50)

    def test_t2n_500(self):
        self.check_prefixes('пятьсот', 500)
        self.check_prefixes('пятисотый', 500)

    def test_t2n_2000(self):
        self.check_prefixes('две тысячи', 2000)
        self.check_prefixes('двухтысячный', 2000)

    def test_t2n_3001(self):
        self.check_prefixes('три тысячи один', 3001)
        self.check_prefixes('три тысячи первый', 3001)

    def test_t2n_4010(self):
        self.check_prefixes('четыре тысячи десять', 4010)
        self.check_prefixes('четыре тысячи десятый', 4010)

    def test_t2n_5500(self):
        self.check_prefixes('пять тысяч пятьсот', 5500)
        self.check_prefixes('пять тысяч пятисотый', 5500)

    def test_t2n_7719(self):
        self.check_prefixes('семь тысяч семьсот девятнадцать', 7719)
        self.check_prefixes('семь тысяч семьсот девятнадцатый', 7719)

    def test_t2n_8800(self):
        self.check_prefixes('восемь тысяч восемьсот', 8800)
        self.check_prefixes('восемь тысяч восьмисотый', 8800)

    def test_t2n_8880(self):
        self.check_prefixes('восемь тысяч восемьсот восемьдесят', 8880)
        self.check_prefixes('восемь тысяч восемьсот восьмидесятый', 8880)

    def test_t2n_8883(self):
        self.check_prefixes('восемь тысяч восемьсот восемьдесят три', 8883)
        self.check_prefixes('восемь тысяч восемьсот восемьдесят третий', 8883)

    def test_t2n_9019(self):
        self.check_prefixes('девять тысяч девятнадцать', 9019)
        self.check_prefixes('девять тысяч девятнадцатый', 9019)

    def test_t2n_9900(self):
        self.check_prefixes('девять тысяч девятьсот', 9900)
        self.check_prefixes('девять тысяч девятисотый', 9900)

    def test_t2n_9990(self):
        self.check_prefixes('девять тысяч девятьсот девяносто', 9990)
        self.check_prefixes('девять тысяч девятьсот девяностый', 9990)

    def test_t2n_9999(self):
        self.check_prefixes('девять тысяч девятьсот девяносто девять', 9999)
        self.check_prefixes('девять тысяч девятьсот девяносто девятый', 9999)

if __name__ == "__main__":
    unittest.main()
