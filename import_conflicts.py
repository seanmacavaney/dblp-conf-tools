import pandas as pd
import re
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
import argparse

def navigate_and_wait(driver, url):
    driver.get(url)
    WebDriverWait(driver, 60, poll_frequency=0.1).until(
        lambda d: d.execute_script("return document.readyState") == "complete"
    )
    # verify the new url
    assert driver.current_url == url, f"navigation to {url} failed"
    time.sleep(2) # wait for it to load property

def handle_login(browser):
    browser.get('https://easychair.org/account2/signin')

    time.sleep(2)
    while True:
        time.sleep(0.5)
        if browser.current_url.startswith('https://easychair.org/my2/welcome'):
            break

def start_browser(browser_choice):
    if browser_choice == 'firefox':
        return webdriver.Firefox()
    elif browser_choice == 'chrome':
        return webdriver.Chrome()
    elif browser_choice == 'safari':
        return webdriver.Safari()

def main():
    parser = argparse.ArgumentParser(description='Tool to import conflict data to EasyChair.')
    parser.add_argument('conflicts_csv', help='conflicts.csv file to import')
    parser.add_argument('easychair_track_url', help='Track URL in EasyChair (e.g., <https://easychair.org/conferences2/submissions?a=XXXXXXXX>)')
    parser.add_argument('--webdriver',required=False,default='firefox',type=str,help='Whether to use firefox, chrome or safari (default: firefox)')
    args = parser.parse_args()

    track_id_match = re.match(r'https://easychair\.org/conferences2/\w+\?a=(\d+)', args.easychair_track_url)
    assert track_id_match is not None, "Invalid EasyChair track URL (should look like <https://easychair.org/conferences2/submissions?a=XXXXXXXX>)"
    track_id = track_id_match.group(1)

    # read conflicts.csv
    conflicts = pd.read_csv(args.conflicts_csv, dtype=str)
    assert 'Member Name' in conflicts.columns and 'submission #' in conflicts.columns

    assert args.webdriver in ['firefox','chrome','safari'], "--webdriver can be firefox, chrome or safari"
    browser = start_browser(args.webdriver)
    try:
        handle_login(browser)
        navigate_and_wait(browser, f'https://easychair.org/conferences2/conflicts?a={track_id}')
        for submission_id, submission_conflicts in conflicts.groupby('submission #'):
            submission_conflicts = set(submission_conflicts["Member Name"].tolist())
            print(f'Submission #{submission_id}')
            conflict_link = browser.find_elements(By.XPATH, f"//a[@class='conflict' and contains(@onclick, \"'{submission_id}'\")]")
            if len(conflict_link) == 0:
                conflict_link = None
            else:
                conflict_link = conflict_link[0]
            if conflict_link is None:
                print('  !! Could not find this submission !!')
                print()
                continue
            # get the onclick attribute text
            submission_global_id = re.match(r'Conflict.add\((\d+),', conflict_link.get_attribute('onclick')).group(1)
            # find elements like <div id="@submission_global_id:\d+">
            existing_conflicts = browser.find_elements(By.XPATH, f"//div[@class='conflict' and starts-with(@id, \"{submission_global_id}:\")]")
            for existing_conflict in existing_conflicts:
                conflict_name = existing_conflict.text.split('(')[0].strip()
                if conflict_name in submission_conflicts:
                    submission_conflicts.discard(conflict_name)
                    print(f'  Already has conflict: {conflict_name}')
            if len(submission_conflicts) == 0:
                print()
                continue
            conflict_link.click()
            WebDriverWait(browser, 60, poll_frequency=0.1).until(lambda d: d.find_element(By.ID, 'add'))
            # find td: <table class=".addTable">...<td>#conflict</td>...</table>
            add_table = browser.find_element(By.CLASS_NAME, 'addTable')
            if add_table is None:
                print('  !! Could not find conflict table !!')
                print()
                continue
            tds = add_table.find_elements(By.XPATH, ".//td")
            any_added = False
            for td in tds:
                conflict = td.text.strip()
                if conflict in submission_conflicts:
                    td.click()
                    print(f'  Added conflict: {conflict}')
                    submission_conflicts.discard(conflict)
                    any_added = True
            if submission_conflicts:
                print(f'  !! Could not find conflicts: {submission_conflicts} !!')
            if any_added:
                add_conflicts_button = browser.find_element(By.XPATH, "//*[@id='add']//button[text()='Add conflicts']")
                add_conflicts_button.click()
            else:
                cancel_conflicts_button = browser.find_element(By.XPATH, "//*[@id='add']//button[text()='Cancel']")
                cancel_conflicts_button.click()
            print()
            time.sleep(0.5)
    finally:
        browser.quit()
    
if __name__ == '__main__':
    main()
