import time
import re
from collections import Counter
from urllib.parse import quote
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

LOGIN_URL = (
    "https://www.dell.com/di/idp/dwa/authorize?response_type=id_token"
    "&client_id=657d850a-459b-4b56-ab6d-361e7181b981"
    "&redirect_uri=https%3a%2f%2fwww.dell.com%2fdci%2ffp%2fdi%2fv3%2ffp%2fsession%2fauthorize%3fclient_id%3d3a4eea6a-4a4e-4f2e-be4a-adc5d51a357a%26redirect_uri%3dhttps%253a%252f%252fwww.dell.com%252fsupport%252fkbdoc%252fen-us%26ContextId%3d2323a4792b1442b8968b7b8d360ef634"
    "&tag=cid=3a4eea6a-4a4e-4f2e-be4a-adc5d51a357a"
    "&state=fp"
    "&scope=openid"
    "&code_challenge=E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM"
    "&code_challenge_method=S256"
    "&nonce=e4b5eeb0-e5e7-4b22-a220-7d1b4d818777"
    "&contextid=2323a4792b1442b8968b7b8d360ef634"
)

def extract_programs_from_log(log_path):
    # This regex should match your log's program fields
    prog_regex = re.compile(r"\s(\S+?)(?:\[\d+\])?:")
    programs = []
    with open(log_path, 'r', encoding='utf-8') as f:
        for line in f:
            match = prog_regex.search(line)
            if match:
                programs.append(match.group(1))
    return programs

def get_most_frequent_program(log_path):
    programs = extract_programs_from_log(log_path)
    if not programs:
        return None
    counter = Counter(programs)
    return counter.most_common(1)[0][0]

def main():
    log_path = "../test_complex.log"  # Change to your log file
    most_common_program = get_most_frequent_program(log_path)
    if not most_common_program:
        print("No program found in log.")
        return
    print(f"Most frequent program in log: {most_common_program}")

    search_term = quote(f"query to {most_common_program} failed")
    search_url = f"https://www.dell.com/support/search/en-us#q={search_term}&sort=relevancy&f:langFacet=[en]"

    options = Options()
    # options.add_argument("--headless=new")
    driver = webdriver.Chrome(options=options)

    print(f"Opening Dell SSO login page: {LOGIN_URL}")
    driver.get(LOGIN_URL)
    input("Complete Dell SSO login in the browser. Once logged in (any page), press Enter here...")

    print(f"Redirecting to search page as authenticated user: {search_url}")
    driver.get(search_url)
    print("Waiting for search results to load...")
    time.sleep(8)

    print("You are now on the search page as a logged-in user.")

    # driver.quit()

if __name__ == "__main__":
    main()