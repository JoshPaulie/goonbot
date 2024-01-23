from string import punctuation


def trim_punctuation(word: str) -> str:
    for symbol in punctuation:
        if word.startswith(symbol):
            word = word[1:]
            break

    for symbol in punctuation:
        if word.endswith(symbol):
            word = word[:-1]
            break
    return word
