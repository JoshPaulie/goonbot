from .generic import trim_punctuation


def wrong_youre(text: str):
    words = [trim_punctuation(word.lower()) for word in text.split()]
    for indx, word in enumerate(words):
        if word == "your":
            if words[indx + 1].endswith("ing"):
                return True
            if words[indx + 1] in ["a", "the"]:
                return True
    return False
