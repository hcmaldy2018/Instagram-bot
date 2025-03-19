import argparse
import json
import os
import sys
import time
import traceback
import requests
import random
import codecs
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.chrome.options import Options

# Set UTF-8 encoding for stdout
if sys.stdout.encoding != 'utf-8':
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
if sys.stderr.encoding != 'utf-8':
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

def parse_arguments():
    parser = argparse.ArgumentParser(description='Instagram Bot Test Script')
    parser.add_argument('--username', required=True, help='Instagram username')
    parser.add_argument('--password', required=True, help='Instagram password')
    parser.add_argument('--interactions', type=int, default=1, help='Number of interactions')
    parser.add_argument('--local-account', type=str, default='false', help='Whether to only interact with low engagement posts')
    return parser.parse_args()

def check_ollama():
    try:
        # Simple check if Ollama is running
        response = requests.get("http://localhost:11434/api/version", timeout=3)
        return response.status_code == 200
    except requests.exceptions.RequestException as e:
        print(f"Error checking Ollama: {str(e)}")
        return False

def generate_comment(caption=""):
    print(f"Generating comment for caption: {caption}")
    if not caption or caption == "No caption found":
        return "Nice! 🔥"
    
    try:
        print("Attempting to contact Ollama API...")
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "llama3",
                "prompt": f"Write a very short, natural, and engaging Instagram comment (max 20 chars) for this post with caption: '{caption}'. Keep it conversational and add an emoji if appropriate.",
                "stream": False
            },
            timeout=5
        )
        
        if response.status_code == 200:
            result = response.json()
            comment = result.get("response", "").strip()
            if comment:
                # Clean up the comment
                comment = comment.replace('"', '').replace("'", '').replace('\n', ' ').strip()
                comment = comment[:20]  # Limit length
                if not any(emoji in comment for emoji in ['😊', '🔥', '💯', '👍', '❤️', '✨']):
                    comment += ' 🔥'
                print(f"Ollama generated comment: {comment}")
                return comment
    except Exception as e:
        print(f"Ollama API error: {e}")
    
    # Simple hashtag-based fallback
    hashtags = [h[1:] for h in caption.split() if h.startswith('#')]
    if hashtags:
        return f"Love this {hashtags[0]}! 🔥"
    
    # Very simple fallback with random variations
    fallbacks = [
        "Amazing! 🔥",
        "Love it! ✨",
        "Great post! 💯",
        "Beautiful! 😊",
        "Fantastic! 👍"
    ]
    return random.choice(fallbacks)

def clean_comment(comment):
    """Clean and format the generated comment"""
    # Remove quotes and newlines
    comment = comment.replace('"', '').replace("'", '').replace('\n', ' ').strip()
    # Remove any markdown formatting that might have been generated
    comment = comment.replace('*', '').replace('_', '').replace('#', '')
    # Ensure it ends with an emoji if it doesn't have one
    if not any(char in comment for char in ['😊', '🔥', '💯', '👍', '❤️', '✨']):
        comment += ' 🔥'
    return comment

def generate_fallback_comment(caption):
    """Generate a fallback comment based on the caption content"""
    print("Generating fallback comment from caption")
    
    # Extract hashtags and words
    words = [w for w in caption.split() if not w.startswith('#')]
    hashtags = [h[1:] for h in caption.split() if h.startswith('#')]
    
    # List of emojis to randomly choose from
    emojis = ['🔥', '✨', '💯', '👍', '❤️', '😊']
    emoji = random.choice(emojis)
    
    if hashtags:
        # Use the first hashtag
        return f"Love this {hashtags[0]}! {emoji}"
    elif len(words) >= 2:
        # Use first two meaningful words
        meaningful_words = [w for w in words if len(w) > 3][:2]
        if meaningful_words:
            return f"Amazing {' '.join(meaningful_words)}! {emoji}"
    
    # Generic fallbacks with different variations
    generic_comments = [
        f"This is awesome! {emoji}",
        f"Love it! {emoji}",
        f"Great post! {emoji}",
        f"Fantastic! {emoji}",
        f"Beautiful! {emoji}"
    ]
    return random.choice(generic_comments)

def clean_text(text):
    """Clean text by removing problematic characters while preserving emojis"""
    try:
        # Try to encode as UTF-8 first
        return text.encode('utf-8', errors='ignore').decode('utf-8')
    except:
        # If that fails, try to remove only truly problematic characters
        return ''.join(char for char in text if ord(char) < 65536)

def main():
    try:
        args = parse_arguments()
        is_local_account = args.local_account.lower() == 'true'
        print(f"Starting bot test with username: {args.username}")
        
        # Check Ollama status at startup
        if not check_ollama():
            print("Warning: Ollama is not running. Will use fallback comment generation.")
        else:
            print("Ollama service is running and ready for comment generation.")
        
        if is_local_account:
            print("Local account mode: Will only interact with low engagement posts")
        sys.stdout.flush()
        
        # Set up Selenium
        print("Initializing ChromeDriver...")
        options = webdriver.ChromeOptions()
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Safari/605.1.15",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0"
        ]
        options.add_argument(f"user-agent={random.choice(user_agents)}")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--start-maximized")
        options.add_argument("--disable-save-password-bubble")
        service = Service("C:/Users/hcmal/insta_bot/chromedriver.exe")
        driver = webdriver.Chrome(service=service, options=options)
        print("Browser initialized successfully.")
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        driver.execute_script("Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']})")
        driver.execute_script("Object.defineProperty(navigator, 'platform', {get: () => 'Win32'})")
        driver.get("https://www.instagram.com/")
        print("Navigated to Instagram, waiting for page load...")
        time.sleep(7)

        # Robust login handling
        try:
            print("Attempting to log in...")
            username_field = WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.NAME, "username")))
            username_field.clear()
            username_field.send_keys(args.username)  # Using username from arguments
            print(f"Entered username from UI input")
            
            password_field = WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.NAME, "password")))
            password_field.clear()
            password_field.send_keys(args.password)  # Using password from arguments
            print("Entered password from UI input")
            
            password_field.send_keys(Keys.RETURN)
            print("Login attempt submitted, waiting for response...")
            sys.stdout.flush()
            time.sleep(10)
            
            # Check for login success with improved detection
            try:
                # Wait for either the Instagram logo or an article to appear
                WebDriverWait(driver, 30).until(
                    EC.presence_of_element_located((
                        By.XPATH,
                        "//*[contains(@aria-label, 'Instagram')] | //article | //div[@role='feed']"
                    ))
                )
                print("Login successful!")
                time.sleep(5)  # Additional wait after success confirmation
            except:
                try:
                    error_message = driver.find_element(By.XPATH, "//p[@id='slfErrorAlert'] | //div[contains(@class, 'error')]").text
                    print(f"Login failed: {error_message}")
                except:
                    print("Login failed: Unable to locate error message on page.")
                    with open("page_source.html", "w", encoding="utf-8") as f:
                        f.write(driver.page_source)
                    print("Page source saved to page_source.html for debugging. If a CAPTCHA or error message appears, solve it manually and press Enter to continue...")
                    input()

            # Handle pop-ups with improved stability
            max_attempts = 20
            for attempt in range(max_attempts):
                try:
                    # Updated selectors to handle Meta login info popup and other popups
                    pop_up_button = WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable((By.XPATH, 
                            "//div[@role='button' and contains(text(), 'Not now')] | " +
                            "//button[text()='Not Now'] | " +
                            "//button[normalize-space(text())='Not now'] | " +
                            "//div[contains(@class, '_a9--') and contains(@class, '_ap36')]//button[contains(text(), 'Not now')] | " +
                            "//div[contains(@class, 'x1i10hfl')]//div[text()='Not now']"
                        ))
                    )
                    time.sleep(2)  # Brief pause before clicking
                    driver.execute_script("arguments[0].click();", pop_up_button)
                    print(f"Attempt {attempt + 1}: Clicked 'Not now' button")
                    time.sleep(2)
                    
                    # Verify if popup was dismissed
                    try:
                        driver.find_element(By.XPATH, "//div[contains(text(), 'Save your login info')]")
                        print("Popup still present, retrying...")
                        continue
                    except:
                        print("Popup dismissed successfully")
                    break
                        
                except Exception as e:
                    print(f"Attempt {attempt + 1} failed: {str(e)}")
                    if attempt == max_attempts - 1:
                        print("Failed to handle popup after maximum attempts")
                        print("Saving page source for debugging...")
                        with open("page_source.html", "w", encoding="utf-8") as f:
                            f.write(driver.page_source)
                        print("Please close the popup manually and press Enter to continue...")
                        input()
                    time.sleep(1)
                    continue

            # Process posts with improved stability
            print("Fetching posts...")
            sys.stdout.flush()
            time.sleep(5)  # Wait time from working version
            
            print("Verifying feed access...")
            # Initial scroll to load posts
            print("Performing initial scroll to load posts...")
            for _ in range(3):
                driver.execute_script("window.scrollBy(0, 500);")
                time.sleep(2)
            driver.execute_script("window.scrollTo(0, 0);")  # Back to top
            time.sleep(3)
            
            # Using the working version's post detection strategy
            successful_interactions = 0
            for i in range(args.interactions):
                try:
                    # Find post link and image using specific selectors that worked
                    print(f"Looking for post {i+1}...")
                    post_selectors = [
                        f"(//article//a[contains(@href, '/p/')])[{i+1}]",
                        f"(//article[contains(@class, '_aagv')])[{i+1}]",
                        f"(//div[@role='feed']//article)[{i+1}]"
                    ]
                    
                    post_element = None
                    for selector in post_selectors:
                        try:
                            post_element = WebDriverWait(driver, 5).until(
                                EC.presence_of_element_located((By.XPATH, selector))
                            )
                            print(f"Found post using selector: {selector}")
                            break
                        except:
                            continue
                    
                    if not post_element:
                        print("No post found with any selector, trying to scroll more...")
                        driver.execute_script("window.scrollBy(0, 800);")
                        time.sleep(3)
                        continue
                    
                    # Ensure post is in view
                    driver.execute_script("""
                        arguments[0].scrollIntoView({
                            behavior: 'smooth',
                            block: 'center'
                        });
                        window.scrollBy(0, -100);  // Scroll up slightly to ensure buttons are visible
                    """, post_element)
                    time.sleep(3)  # Increased wait time after scrolling
                    
                    # Try to like the post
                    try:
                        like_button = driver.find_element(By.XPATH, ".//div[contains(@class, 'x1i10hfl') and .//*[name()='svg' and @aria-label='Like']]")
                        if like_button.is_displayed():
                            driver.execute_script("arguments[0].click();", like_button)
                            print("Post liked successfully")
                            time.sleep(2)
                            
                            # Get caption first
                            caption = ""
                            try:
                                # First try to click "more" if it exists
                                try:
                                    more_button = WebDriverWait(driver, 5).until(
                                        EC.element_to_be_clickable((By.XPATH, 
                                            "(//article//span[contains(@class, 'x1lliihq') and contains(text(), 'more')])[1]"
                                        ))
                                    )
                                    driver.execute_script("arguments[0].scrollIntoView(true);", more_button)
                                    time.sleep(1)
                                    try:
                                        actions = ActionChains(driver)
                                        actions.move_to_element(more_button).click().perform()
                                    except:
                                        driver.execute_script("arguments[0].click();", more_button)
                                        print("Used JavaScript click as fallback for 'more' button")
                                    time.sleep(2)  # Wait for caption to expand
                                    print("Clicked 'more' button to reveal full caption")
                                except Exception as e:
                                    print(f"No 'more' button found or not clickable: {str(e)}")
                                
                                # Now get the full caption - try multiple selectors
                                caption_selectors = [
                                    "(//article//span[contains(@class, '_ap3a') and not(contains(@class, 'x1lliihq'))]//span[contains(@class, '_ap3a')])[1]",
                                    "(//article)[1]//div[contains(@class, 'x9f619')]//span[contains(@class, '_ap3a')]",
                                    "(//article)[1]//span[contains(@class, '_ap3a') and contains(@class, '_aaco')]"
                                ]
                                
                                for selector in caption_selectors:
                                    try:
                                        caption_element = WebDriverWait(driver, 5).until(
                                            EC.presence_of_element_located((By.XPATH, selector))
                                        )
                                        caption = caption_element.text.strip()
                                        if caption:
                                            print(f"Scraped caption: '{caption}'")
                                            break
                                    except:
                                        continue
                                
                                if not caption:
                                    print("Could not find caption with any selector")
                                    caption = "No caption found"
                            except Exception as e:
                                print(f"Caption scraping failed: {str(e)}")
                                caption = "No caption found"
                            
                            # Generate comment before trying to interact with comment field
                            print("Generating comment...")
                            comment = generate_comment(caption)
                            print(f"Generated comment: {comment}")
                            
                            if not comment:
                                print("Failed to generate comment, using fallback")
                                comment = "Amazing post! 🔥"
                            
                            # Now try to post the comment with enhanced stability
                            for attempt in range(3):
                                try:
                                    # Wait for DOM stability by checking comment field presence
                                    WebDriverWait(driver, 20).until(
                                        EC.presence_of_element_located((By.XPATH, "(//textarea[@placeholder='Add a comment…'])[1]"))
                                    )
                                    # Verify DOM stability by checking multiple times
                                    for _ in range(3):
                                        comment_fields = driver.find_elements(By.XPATH, "(//textarea[@placeholder='Add a comment…'])[1]")
                                        if len(comment_fields) == 0:
                                            raise Exception("Comment field disappeared during stability check")
                                        time.sleep(1)  # Small delay between checks
                                    
                                    comment_field = WebDriverWait(driver, 15).until(
                                        EC.element_to_be_clickable((By.XPATH, "(//textarea[@placeholder='Add a comment…'])[1]"))
                                    )
                                    driver.execute_script("arguments[0].scrollIntoView(true);", comment_field)
                                    time.sleep(2)  # Let DOM settle
                                    
                                    # Re-check if the element is still valid
                                    for retry in range(3):
                                        try:
                                            comment_field = WebDriverWait(driver, 15).until(
                                                EC.element_to_be_clickable((By.XPATH, "(//textarea[@placeholder='Add a comment…'])[1]"))
                                            )
                                            break
                                        except:
                                            print(f"Retry {retry + 1} to re-locate comment field due to potential stale element...")
                                            time.sleep(2)
                                    
                                    # Try ActionChains click first
                                    try:
                                        actions = ActionChains(driver)
                                        actions.move_to_element(comment_field).click().perform()
                                    except:
                                        # Fallback to JavaScript click
                                        driver.execute_script("arguments[0].click();", comment_field)
                                        print("Used JavaScript click as fallback for comment field")
                                    
                                    time.sleep(1)
                                    comment_field.clear()
                                    for char in comment:
                                        comment_field.send_keys(char)
                                        time.sleep(random.uniform(0.1, 0.3))
                                    
                                    comment_field.send_keys(Keys.RETURN)
                                    time.sleep(2)
                                    print(f"Comment posted: {comment}")
                                    break
                                except Exception as e:
                                    print(f"Attempt {attempt + 1} failed: {e}")
                                    if attempt == 2:
                                        with open("page_source.html", "w", encoding="utf-8") as f:
                                            f.write(driver.page_source)
                                        print("Saved page_source.html to check what went wrong.")
                                    time.sleep(2)
                    except Exception as e:
                        print(f"Like failed: {e}")
                    
                    # Scroll a bit to load more posts
                    driver.execute_script("window.scrollBy(0, 400);")
                    time.sleep(2)
                except Exception as e:
                    print(f"Could not process post {i+1}: {e}")
                    break
            
            print(f"Completed {successful_interactions} out of {args.interactions} requested interactions")
            
        except Exception as e:
            error_msg = f"Failed to process posts: {str(e)}\nStacktrace:\n{traceback.format_exc()}"
            print(json.dumps({
                "success": False,
                "error": error_msg
            }))
            sys.stdout.flush()
        finally:
            driver.quit()
            print("Browser closed successfully")
            sys.stdout.flush()
    
    except Exception as e:
        error_msg = f"Bot error: {str(e)}\nStacktrace:\n{traceback.format_exc()}"
        print(json.dumps({
            "success": False,
            "error": error_msg
        }))
        sys.stdout.flush()

if __name__ == "__main__":
    main()