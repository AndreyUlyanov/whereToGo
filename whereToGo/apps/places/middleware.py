from string import ascii_letters, digits


def string_checking(string):
    for char in string:
        if char not in ascii_letters and char not in digits:
            return False
    return True
