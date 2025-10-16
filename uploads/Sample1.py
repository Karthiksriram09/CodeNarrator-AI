def check_palindrome(word):
    """Check if a word is a palindrome."""
    word = word.lower().replace(" ", "")
    if word == word[::-1]:
        return True
    else:
        return False

if __name__ == "__main__":
    test_word = "Madam"
    if check_palindrome(test_word):
        print(f"{test_word} is a palindrome!")
    else:
        print(f"{test_word} is not a palindrome.")
