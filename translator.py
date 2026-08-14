"""
CLI translator — uses the same business logic as the web app.
"""

from translator_web import config
from translator_web.service import translate_and_correct

# ANSI colors
RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
CYAN = "\033[36m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
MAGENTA = "\033[35m"
WHITE = "\033[97m"


def show_result(result, model: str, language_pair: str) -> None:
    width = 60
    print()
    print(f"{BOLD}{CYAN}{'─' * width}{RESET}")
    print(f"{BOLD}{CYAN}{config.APP_NAME}{RESET} {DIM}({model} · {language_pair}){RESET}")
    print(f"{BOLD}{CYAN}{'─' * width}{RESET}")
    print(f"{DIM}Original{RESET}")
    print(f"  {WHITE}{result.provided}{RESET}")
    print()
    print(f"{YELLOW}Detected language{RESET}  {result.detected}{RESET}")
    print()
    print(f"{GREEN}Corrected{RESET}")
    print(f"  {BOLD}{GREEN}{result.corrected}{RESET}")
    print()
    print(f"{MAGENTA}Translation ({result.target}){RESET}")
    print(f"  {BOLD}{MAGENTA}{result.translation}{RESET}")
    if result.note:
        print()
        print(f"{DIM}{result.note}{RESET}")
    print(f"{BOLD}{CYAN}{'─' * width}{RESET}")
    print()


def main() -> None:
    text = input("Please enter the text you want me to translate or correct: ")
    result = translate_and_correct(text, config.DEFAULT_LANGUAGE_PAIR)
    show_result(result, config.MODEL, config.DEFAULT_LANGUAGE_PAIR)


if __name__ == "__main__":
    main()
