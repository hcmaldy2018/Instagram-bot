# Import libraries we need
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
import time
import random
import requests
import cv2
import numpy as np
import os
import json
import argparse
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# Set UTF-8 encoding for output
sys.stdout.reconfigure(encoding='utf-8')

def parse_arguments():
    parser = argparse.ArgumentParser(description='Instagram Bot')
    parser.add_argument('--username', required=True, help='Instagram username')
    parser.add_argument('--password', required=True, help='Instagram password')
    parser.add_argument('--interactions', type=int, default=1, help='Number of interactions')
    return parser.parse_args()

# Ollama API endpoint (assuming it's running locally)
OLLAMA_API_URL = "http://localhost:11434/api/generate"

# Function to generate a comment using Ollama
def generate_comment(image_url=None, caption=""):
    if not caption:
        return "Nice!"  # Fallback if no caption
    
    # Determine if it's a video post (image_url will be None or empty)
    is_video = not image_url
    
    # Prepare context based on content type
    content_context = ""
    if not is_video:
        try:
            response = requests.get(image_url, timeout=10)
            image_path = "temp_image.jpg"
            with open(image_path, "wb") as f:
                f.write(response.content)
            
            image = cv2.imread(image_path)
            if image is None:
                raise ValueError("Failed to load image")
            
            hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
            lower_food_brown = np.array([0, 20, 20])
            upper_food_brown = np.array([30, 255, 255])
            food_mask_brown = cv2.inRange(hsv, lower_food_brown, upper_food_brown)
            lower_food_green = np.array([35, 20, 20])
            upper_food_green = np.array([85, 255, 255])
            food_mask_green = cv2.inRange(hsv, lower_food_green, upper_food_green)
            food_mask = cv2.bitwise_or(food_mask_brown, food_mask_green)
            lower_event = np.array([90, 50, 50])
            upper_event = np.array([150, 255, 255])
            event_mask = cv2.inRange(hsv, lower_event, upper_event)
            
            food_pixels = cv2.countNonZero(food_mask)
            event_pixels = cv2.countNonZero(event_mask)
            total_pixels = image.shape[0] * image.shape[1]
            food_ratio = food_pixels / total_pixels
            event_ratio = event_pixels / total_pixels
            
            if food_ratio > 0.1:
                content_context = "The image appears to show food. "
                print("Detected food in image")
            elif event_ratio > 0.05:
                content_context = "The image appears to be from an event. "
                print("Detected event-related imagery")
            
        except Exception as e:
            print(f"Image analysis failed: {e}")
        finally:
            if os.path.exists(image_path):
                os.remove(image_path)

    # Prepare prompt with more emphasis on caption
    if is_video:
        prompt = f"Generate a natural and engaging Instagram comment (under 50 characters) for a video post with caption: '{caption}'. Focus entirely on the caption content."
    else:
        prompt = f"Generate a natural and engaging Instagram comment (under 50 characters) primarily based on this caption: '{caption}'. Additional context: {content_context}"
    
    try:
        response = requests.post(OLLAMA_API_URL, json={"model": "llama3", "prompt": prompt, "stream": False})
        if response.status_code == 200:
            result = response.json()
            comment = result.get("response", "").strip()
            if comment:
                return comment[:50]  # Limit to 50 characters
        print("Ollama API call failed or returned no valid response")
    except Exception as e:
        print(f"Ollama API error: {e}")
    
    # Fallback if API fails
    return "Great post! 👍" if is_video else f"Amazing {caption.split()[0] if caption else 'post'}! 👍"

def main():
    args = parse_arguments()
    print(f"Starting bot with username: {args.username}")
    
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
        print("Entered username from UI input")
        
        password_field = WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.NAME, "password")))
        password_field.clear()
        password_field.send_keys(args.password)  # Using password from arguments
        print("Entered password from UI input")
        
        password_field.send_keys(Keys.RETURN)
        print("Login attempt submitted, waiting for response...")
        time.sleep(10)
        
        # Verify login success with a more reliable element
        WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.XPATH, "//*[contains(@aria-label, 'Instagram')] | //article")))
        print("Login successful!")
        
        # Handle Meta save login info popup with multiple selectors
        print("Checking for Meta login info popup...")
        popup_selectors = [
            "//button[text()='Not now']",  # Basic text match
            "//button[contains(text(), 'Not')]",  # Partial text match
            "//div[@role='button' and contains(text(), 'Not')]",  # Role-based button
            "//div[contains(@class, '_a9--') and contains(text(), 'Not')]",  # Class-based
            "//div[contains(@class, '_acan') and contains(text(), 'Not')]",  # Alternative class
            "//div[@role='button']//div[contains(text(), 'Not')]"  # Nested structure
        ]
        
        for selector in popup_selectors:
            try:
                popup = WebDriverWait(driver, 3).until(EC.element_to_be_clickable((By.XPATH, selector)))
                if popup and popup.is_displayed():
                    time.sleep(1)  # Brief pause before clicking
                    try:
                        # Try multiple click methods
                        try:
                            popup.click()
                        except:
                            driver.execute_script("arguments[0].click();", popup)
                        print("Dismissed Meta login info popup")
                        time.sleep(2)  # Wait after clicking
                        break
                    except Exception as e:
                        print(f"Click attempt failed for selector {selector}: {e}")
                        continue
            except:
                continue
        
    except Exception as e:
        print(f"Login failed: {e}")
        with open("page_source.html", "w", encoding="utf-8") as f:
            f.write(driver.page_source)
        print("Page source saved to page_source.html for debugging. If a CAPTCHA or error message appears, solve it manually and press Enter to continue...")
        input()

    # After login, verify feed access and start processing
    try:
        print("Verifying feed access...")
        # Wait for feed to load by looking for posts
        feed_posts = WebDriverWait(driver, 15).until(
            EC.presence_of_all_elements_located((
                By.XPATH, 
                "//article[contains(@class, '_aagv')] | //article[contains(@class, 'x1q0g3np')] | " +
                "//div[contains(@class, '_aabd')]//article | //div[contains(@class, '_ab6k')]//article"
            ))
        )
        
        if feed_posts:
            print(f"Successfully accessed main feed. Found {len(feed_posts)} posts.")
            
            # Optional: Quick single check for popups without retrying
            try:
                popup = driver.find_element(By.XPATH, "//button[text()='Not Now']")
                if popup.is_displayed():
                    popup.click()
                    print("Dismissed a popup")
                    time.sleep(1)
            except:
                print("No popups found, proceeding with feed interaction")
            
            # Start processing posts
            print("Starting to process posts...")
            try:
                num_interactions = int(sys.argv[1]) if len(sys.argv) > 1 else 1
                print(f"Starting bot with {num_interactions} interaction(s)...")
                
                # Process posts one by one
                successful_interactions = 0
                for post in feed_posts:
                    if successful_interactions >= num_interactions:
                        break
                        
                    print(f"\nProcessing post {successful_interactions + 1}/{num_interactions}")
                    
                    # Ensure post is in view
                    driver.execute_script("""
                        arguments[0].scrollIntoView({
                            behavior: 'smooth',
                            block: 'center'
                        });
                    """, post)
                    time.sleep(2)
                    
                    # Try to like the post
                    try:
                        like_button = post.find_element(By.XPATH, ".//div[contains(@class, 'x1i10hfl') and .//*[name()='svg' and @aria-label='Like']]")
                        if like_button.is_displayed():
                            driver.execute_script("arguments[0].click();", like_button)
                            print("Post liked successfully")
                            time.sleep(2)
                            
                            # Try to comment
                            try:
                                comment_field = post.find_element(By.XPATH, ".//textarea[@placeholder='Add a comment…']")
                                driver.execute_script("""
                                    arguments[0].scrollIntoView({
                                        behavior: 'smooth',
                                        block: 'center'
                                    });
                                    window.scrollBy(0, -100);
                                """, comment_field)
                                time.sleep(2)
                                
                                # Generate and post comment
                                comment = "Great post! 👍"  # Simple default comment
                                driver.execute_script("arguments[0].click();", comment_field)
                                time.sleep(1)
                                comment_field.send_keys(comment)
                                time.sleep(1)
                                comment_field.send_keys(Keys.RETURN)
                                print(f"Comment posted: {comment}")
                                
                                successful_interactions += 1
                                time.sleep(random.uniform(2, 4))
                            except Exception as e:
                                print(f"Comment failed: {e}")
                    except Exception as e:
                        print(f"Like failed: {e}")
                    
                    # Scroll a bit to load more posts if needed
                    if successful_interactions < num_interactions:
                        driver.execute_script("window.scrollBy(0, 400);")
                        time.sleep(2)
                
                print(f"Completed {successful_interactions} out of {num_interactions} requested interactions")
                
            except Exception as e:
                print(f"Error during post processing: {e}")
        else:
            print("Could not verify feed access - no posts found")
            
    except Exception as e:
        print(f"Error accessing feed: {e}")
        with open("page_source.html", "w", encoding="utf-8") as f:
            f.write(driver.page_source)
        print("Page source saved to page_source.html for debugging.")
    finally:
        print("Closing browser...")
        driver.quit()
        print("Bot finished!")

if __name__ == "__main__":
    main()