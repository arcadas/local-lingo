"""
CLI translator — uses the same business logic as the web app.
"""

import time

from . import config
from .service import get_model_catalog, translate_and_correct

# ANSI colors
RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
CYAN = "\033[36m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
MAGENTA = "\033[35m"
WHITE = "\033[97m"


def show_result(result, model: str, language_pair: str, elapsed: float) -> None:
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
    print(f"{DIM}Completed in {elapsed:.1f}s{RESET}")
    print(f"{BOLD}{CYAN}{'─' * width}{RESET}")
    print()


def main() -> None:
    catalog = get_model_catalog()
    if catalog.warning:
        print(f"{YELLOW}{catalog.warning}{RESET}")
    if not catalog.selected:
        return
    text = input("Please enter the text you want me to translate or correct: ")
    started = time.perf_counter()
    result = translate_and_correct(
        text, config.DEFAULT_LANGUAGE_PAIR, model=catalog.selected
    )
    elapsed = time.perf_counter() - started
    show_result(result, catalog.selected, config.DEFAULT_LANGUAGE_PAIR, elapsed)


if __name__ == "__main__":
    main()
