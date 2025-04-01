import argparse
import json
import os
import sys
import time
import traceback
import random
import codecs
import logging
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.chrome.options import Options
import google.generativeai as genai

# Set UTF-8 encoding for stdout
if sys.stdout.encoding != 'utf-8':
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
if sys.stderr.encoding != 'utf-8':
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

def setup_logging():
    """Set up logging configuration"""
    log_filename = "bot_log.txt"
    try:
        if os.path.exists(log_filename):
            os.remove(log_filename)
    except Exception as e:
        print(f"Warning: Could not delete existing log file: {e}")
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_filename, encoding='utf-8')
        ]
    )
    return log_filename

def log_activity(message, include_error_details=False):
    """Log activity with timestamp"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S,%f')[:-3]
    logging.info(message)
    
    try:
        if not include_error_details and "Stacktrace" in message:
            main_error = message.split('\n')[0]
            if "stale element reference" in main_error:
                simplified_message = "Retrying comment posting..."
            elif "ChromeDriver only supports characters in the BMP" in main_error:
                simplified_message = "Retrying with simplified comment..."
            elif "Message:" in main_error:
                simplified_message = "Retrying due to technical issue..."
            else:
                simplified_message = "Retrying action..."
            print(simplified_message)
        else:
            clean_message = message.split('Stacktrace')[0].strip()
            print(clean_message)
    except Exception as e:
        print(f"{timestamp} - {message}")

def parse_arguments():
    parser = argparse.ArgumentParser(description='Instagram Bot Script')
    parser.add_argument('--username', required=True, help='Instagram username')
    parser.add_argument('--password', required=True, help='Instagram password')
    parser.add_argument('--interactions', type=int, default=1, help='Number of interactions')
    parser.add_argument('--local-account', type=str, default='false', help='Whether to only interact with low engagement posts')
    return parser.parse_args()

def setup_gemini():
    """Initialize Gemini API with your API key"""
    try:
        log_activity("Attempting to initialize Gemini API...")
        genai.configure(api_key="AIzaSyC-rDK4kRtXgZoTraV1M4HU7CjGf_BQs-c")
        model = genai.GenerativeModel('gemini-1.5-pro-latest')
        log_activity("Gemini API initialized successfully")
        return model
    except Exception as e:
        log_activity(f"Failed to initialize Gemini: {str(e)}")
        return None

def generate_comment(caption="", used_comments=None):
    """Generate a contextually appropriate comment using Gemini API"""
    if used_comments is None:
        used_comments = set()
    
    if not caption or caption == "No caption found":
        log_activity("No caption provided, using fallback comment")
        return generate_fallback_comment()

    try:
        model = setup_gemini()
        if model:
            prompt = f"""
            Generate a short, genuine Instagram comment for this post. 
            The comment should be positive and appreciative, but not overpromising or requiring a response.

            Post caption: "{caption}"
            
            Requirements:
            - Maximum 1 sentence
            - Include relevant emoji if appropriate
            - Sound natural and authentic
            - No questions or promises
            - No offers to use services or collaborate
            - Keep it simple and genuine
            - Maximum length: 50 characters
            - Focus on appreciation or admiration
            - No hashtags unless they're perfectly contextual
            """
            
            response = model.generate_content(prompt)
            comment = response.text.strip()
            
            comment = clean_text(comment)
            if len(comment) > 50:
                comment = comment[:47] + "..."
            
            if comment.lower() not in used_comments:
                used_comments.add(comment.lower())
                return comment
            
    except Exception as e:
        log_activity(f"Gemini comment generation failed: {str(e)}")
    
    return generate_fallback_comment()

def generate_fallback_comment():
    """Generate a simple, safe fallback comment"""
    fallbacks = [
        "Amazing!", "Love it!", "Great!", "Perfect!",
        "Beautiful!", "Wonderful!", "Fantastic!", "Brilliant!"
    ]
    return random.choice(fallbacks)

def clean_text(text):
    """Clean text to ensure it only contains BMP characters"""
    emoji_map = {
        '💪': '💯',
        '⚰️': '✨',
        '3️⃣': '3',
        '0️⃣': '0',
        '5️⃣': '5',
        '6️⃣': '6',
        '7️⃣': '7',
        '8️⃣': '8',
        '2️⃣': '2',
        '🔥': '✨',
        '🌟': '✨',
        '🙌': '👍',
        '💫': '✨'
    }
    
    for key, value in emoji_map.items():
        text = text.replace(key, value)
    
    return ''.join(char for char in text if ord(char) < 0x10000)

def post_comment(driver, post_index, comment):
    """Post a comment with improved reliability"""
    max_attempts = 3
    for attempt in range(max_attempts):
        try:
            comment_field = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, 
                    f"(//article)[{post_index}]//textarea[@placeholder='Add a comment…']"
                ))
            )
            
            comment_field.clear()
            driver.execute_script("arguments[0].click();", comment_field)
            time.sleep(1)
            
            cleaned_comment = clean_text(comment)
            
            for char in cleaned_comment:
                comment_field.send_keys(char)
                time.sleep(random.uniform(0.05, 0.2))
            
            time.sleep(random.uniform(0.5, 1.0))
            
            comment_field.send_keys(Keys.RETURN)
            time.sleep(3)
            
            if not comment_field.get_attribute('value'):
                log_activity(f"Comment posted successfully: {cleaned_comment}")
                return True
            
            raise Exception("Comment field not cleared after posting")
            
        except Exception as e:
            log_activity(f"Comment attempt {attempt + 1} failed: {str(e)}")
            if attempt == max_attempts - 1:
                return False
            time.sleep(2)
    
    return False

def process_post(driver, post, post_index, used_comments, is_local_account=False):
    """Process a single post"""
    try:
        driver.execute_script("""
            arguments[0].scrollIntoView({
                behavior: 'smooth',
                block: 'center'
            });
            window.scrollBy(0, -200);
        """, post)
        time.sleep(3)
        
        try:
            ActionChains(driver).send_keys(Keys.ESCAPE).perform()
            time.sleep(1)
        except:
            pass
        
        try:
            like_button = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.XPATH, 
                    f"(//article)[{post_index}]//div[contains(@class, 'x1i10hfl') and .//*[name()='svg' and @aria-label='Like']]"
                ))
            )
            if "liked" in like_button.get_attribute("class").lower():
                log_activity("Post already liked, skipping...")
                return False
        except Exception as e:
            log_activity(f"Error checking like status: {e}")
            return False

        try:
            caption = post.find_element(By.XPATH, ".//span[contains(@class, '_ap3a')]").text.strip()
            if not caption:
                log_activity("No caption found")
                return False
        except:
            log_activity("Could not find caption")
            return False
        
        comment = generate_comment(caption, used_comments)
        if not comment:
            log_activity("Failed to generate comment")
            return False
        
        try:
            post = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.XPATH, f"(//article)[{post_index}]"))
            )
            
            like_button = WebDriverWait(driver, 3).until(
                EC.presence_of_element_located((By.XPATH, 
                    f"(//article)[{post_index}]//div[contains(@class, 'x1i10hfl') and .//*[name()='svg' and @aria-label='Like']]"
                ))
            )
            
            if "liked" not in like_button.get_attribute("class").lower():
                driver.execute_script("arguments[0].click();", like_button)
                log_activity("Post liked successfully")
                time.sleep(2)
            
            if post_comment(driver, post_index, comment):
                return True
            else:
                log_activity("Failed to post comment")
                return False
                
        except Exception as e:
            log_activity(f"Failed to interact with post: {e}")
            return False
            
    except Exception as e:
        log_activity(f"Error processing post: {e}")
        return False
    
    return False

def login_to_instagram(driver, username, password):
    """Handle login and initial popups"""
    try:
        username_field = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.NAME, "username")))
        username_field.clear()
        for char in username:
            username_field.send_keys(char)
            time.sleep(random.uniform(0.02, 0.05))
        log_activity("Entered username")
        
        password_field = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.NAME, "password")))
        password_field.clear()
        for char in password:
            password_field.send_keys(char)
            time.sleep(random.uniform(0.02, 0.05))
        log_activity("Entered password")
        
        password_field.send_keys(Keys.RETURN)
        log_activity("Login attempt submitted, waiting for response...")
        time.sleep(5)
        
        max_attempts = 20
        for attempt in range(max_attempts):
            try:
                pop_up_button = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, 
                        "//div[@role='button' and contains(text(), 'Not now')] | " +
                        "//button[text()='Not Now'] | " +
                        "//button[normalize-space(text())='Not now'] | " +
                        "//div[contains(@class, '_a9--') and contains(@class, '_ap36')]//button[contains(text(), 'Not now')] | " +
                        "//div[contains(@class, 'x1i10hfl')]//div[text()='Not now']"
                    ))
                )
                time.sleep(1)
                driver.execute_script("arguments[0].click();", pop_up_button)
                log_activity(f"Attempt {attempt + 1}: Clicked 'Not now' button")
                time.sleep(1)
                
                try:
                    driver.find_element(By.XPATH, "//div[contains(text(), 'Save your login info')]")
                    log_activity("Popup still present, retrying...")
                    continue
                except:
                    log_activity("Popup dismissed successfully")
                break
                    
            except Exception as e:
                log_activity(f"Attempt {attempt + 1} failed: {str(e)}")
                if attempt == max_attempts - 1:
                    log_activity("Failed to handle popups after maximum attempts")
                    break
        
        try:
            action = ActionChains(driver)
            action.move_by_offset(1, 1).click().perform()
            log_activity("Clicked to dismiss Meta popup")
            action.move_by_offset(-1, -1).perform()
            time.sleep(1)
        except:
            log_activity("Could not click to dismiss Meta popup")
        
        try:
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((
                    By.XPATH,
                    "//*[contains(@aria-label, 'Instagram')] | //article | //div[@role='feed']"
                ))
            )
            log_activity("Successfully reached Instagram feed!")
            return True
                
        except Exception as e:
            log_activity(f"Failed to verify feed access: {e}")
            return False

    except Exception as e:
        log_activity(f"Login failed: {e}")
        return False

def main():
    """Main function to run the Instagram bot"""
    try:
        log_file = setup_logging()
        log_activity(f"Log file created: {log_file}")
        
        args = parse_arguments()
        log_activity(f"Starting bot with username: {args.username}")
        
        used_comments = set()
        is_local_account = args.local_account.lower() == 'true'
        if is_local_account:
            log_activity("Local account mode: Will only interact with low engagement posts")
        
        log_activity("Initializing browser...")
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
        log_activity("Browser initialized successfully.")
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        driver.execute_script("Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']})")
        driver.execute_script("Object.defineProperty(navigator, 'platform', {get: () => 'Win32'})")
        driver.get("https://www.instagram.com/")
        log_activity("Navigated to Instagram, waiting for page load...")
        time.sleep(3)

        try:
            log_activity("Attempting to log in...")
            if login_to_instagram(driver, args.username, args.password):
                log_activity("Starting to process posts...")
                
                successful_interactions = 0
                posts_checked = 0
                max_attempts = args.interactions * 3
                current_post_index = 1
                
                while successful_interactions < args.interactions:
                    if successful_interactions > 0 and successful_interactions % 3 == 0:
                        log_activity("Completed 3 interactions, refreshing page...")
                        driver.refresh()
                        time.sleep(5)
                        
                        try:
                            ActionChains(driver).send_keys(Keys.ESCAPE).perform()
                            time.sleep(1)
                        except:
                            pass
                        
                        try:
                            WebDriverWait(driver, 10).until(
                                EC.presence_of_element_located((By.XPATH, "//article | //div[@role='feed']"))
                            )
                            log_activity("Successfully refreshed and verified feed access")
                            current_post_index = 1
                            time.sleep(2)
                        except:
                            log_activity("Feed not found after refresh, attempting to log in again...")
                            if not login_to_instagram(driver, args.username, args.password):
                                log_activity("Failed to log in after refresh")
                                break
                    
                    posts_checked += 1
                    
                    try:
                        post = WebDriverWait(driver, 10).until(
                            EC.presence_of_element_located((By.XPATH, f"(//article)[{current_post_index}]"))
                        )
                        
                        if process_post(driver, post, current_post_index, used_comments, is_local_account):
                            successful_interactions += 1
                            log_activity(f"Successfully processed post {successful_interactions}/{args.interactions}")
                            
                            current_post_index += 1
                            driver.execute_script("window.scrollBy(0, 400);")
                            time.sleep(2)
                            
                            try:
                                ActionChains(driver).send_keys(Keys.ESCAPE).perform()
                                time.sleep(0.5)
                            except:
                                pass
                        else:
                            log_activity(f"Skipped or failed to process post {current_post_index}")
                            current_post_index += 1
                            driver.execute_script("window.scrollBy(0, 200);")
                            time.sleep(1)
                            
                    except Exception as e:
                        log_activity(f"Error processing post: {e}")
                        current_post_index += 1
                        driver.execute_script("window.scrollBy(0, 200);")
                        time.sleep(2)
                        
                        try:
                            ActionChains(driver).send_keys(Keys.ESCAPE).perform()
                            time.sleep(0.5)
                        except:
                            pass
                    
                    if posts_checked >= max_attempts:
                        log_activity("Reached maximum attempts limit")
                        break
                
                log_activity(f"Completed {successful_interactions} out of {args.interactions} requested interactions")
            else:
                log_activity("Login failed or could not verify feed access")
            
        except Exception as e:
            error_msg = f"Failed to process posts: {str(e)}\nStacktrace:\n{traceback.format_exc()}"
            log_activity(json.dumps({
                "success": False,
                "error": error_msg
            }))
        finally:
            driver.quit()
            log_activity("Browser closed successfully")
    
    except Exception as e:
        error_msg = f"Bot error: {str(e)}\nStacktrace:\n{traceback.format_exc()}"
        log_activity(json.dumps({
            "success": False,
            "error": error_msg
        }))

if __name__ == "__main__":
    main() 