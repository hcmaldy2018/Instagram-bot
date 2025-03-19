import argparse
import json
import os
import sys
import time
import traceback
import requests
import random
import codecs
import subprocess
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
import asyncio

# Set UTF-8 encoding for stdout
if sys.stdout.encoding != 'utf-8':
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
if sys.stderr.encoding != 'utf-8':
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# Set up logging
def setup_logging():
    """Set up logging configuration"""
    log_filename = "bot_log.txt"  # Fixed filename
    
    # Delete existing log file if it exists
    try:
        if os.path.exists(log_filename):
            os.remove(log_filename)
    except Exception as e:
        print(f"Warning: Could not delete existing log file: {e}")
    
    # Configure file logging for technical details
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_filename, encoding='utf-8')
        ]
    )
    
    return log_filename

# Create separate loggers
technical_logger = logging.getLogger('technical')
activity_logger = logging.getLogger('activity')

def log_activity(message, include_error_details=False):
    """Log activity with timestamp"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S,%f')[:-3]
    
    # For the log file - always include full details
    logging.info(message)
    
    try:
        # For the live activity feed - filter out technical details unless specifically requested
        if not include_error_details and "Stacktrace" in message:
            # Extract just the main error message without stack trace
            main_error = message.split('\n')[0]
            if "stale element reference" in main_error:
                simplified_message = "Retrying comment posting..."
            elif "ChromeDriver only supports characters in the BMP" in main_error:
                simplified_message = "Retrying with simplified comment..."
            elif "Message:" in main_error:
                # Extract the user-friendly part of the error
                simplified_message = "Retrying due to technical issue..."
            else:
                simplified_message = "Retrying action..."
            
            # Print to console for command line usage
            print(simplified_message)
        else:
            # Print non-error messages to console
            clean_message = message.split('Stacktrace')[0].strip()
            print(clean_message)
    except Exception as e:
        # Fallback to simple console logging if anything goes wrong
        print(f"{timestamp} - {message}")

def log_technical(message, level='info'):
    """Log technical messages only to file"""
    if level == 'error':
        technical_logger.error(message)
    else:
        technical_logger.info(message)

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
        genai.configure(api_key="AIzaSyC-rDK4kRtXgZoTraV1M4HU7CjGf_BQs-c")
        model = genai.GenerativeModel('gemini-1.5-pro-latest')
        return model
    except Exception as e:
        log_activity(f"Failed to initialize Gemini: {e}")
        return None

def generate_comment(caption="", used_comments=None):
    """Generate a contextually appropriate comment using Gemini API"""
    if used_comments is None:
        used_comments = set()
    
    if not caption or caption == "No caption found":
        return generate_fallback_comment()

    try:
        # Try to use Gemini for comment generation
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
            
            Examples of good comments:
            - "Beautiful capture! 📸"
            - "Love the vibes ✨"
            - "This is stunning! 🌟"
            - "Perfect moment 🙌"
            
            Examples to avoid:
            - "DM me for collab"
            - "Check out my page"
            - "Where is this place?"
            - "I'll definitely try this"
            
            Generate only the comment, no explanations.
            """
            
            response = model.generate_content(prompt)
            comment = response.text.strip()
            
            # Clean and validate the comment
            comment = clean_text(comment)
            if len(comment) > 50:  # Reduced maximum length
                comment = comment[:47] + "..."
            
            # Additional validation to avoid unwanted patterns
            lower_comment = comment.lower()
            if any(pattern in lower_comment for pattern in [
                "dm", "follow", "check", "visit", "where", "when", "how", "?", 
                "collab", "message", "contact", "www", "http", "@", "link"
            ]):
                return generate_fallback_comment()
            
            # Check if comment is unique
            if comment.lower() not in used_comments:
                used_comments.add(comment.lower())
                log_activity(f"Generated Gemini comment: {comment}")
                return comment
            
    except Exception as e:
        log_activity(f"Gemini comment generation failed: {e}")
    
    # Fallback to template-based system if Gemini fails
    log_activity("Falling back to template-based comment generation")
    
    # Updated templates with more natural, positive comments
    templates = {
        'photo': [
            "Beautiful shot! 📸", "Stunning capture! ✨", "Love this view! 🌟", 
            "Amazing photo! 💫", "Perfect shot! 🎯", "Fantastic pic! 🙌"
        ],
        'nature': [
            "Pure beauty! 🌿", "Nature's magic! ✨", "Simply stunning! 🌸",
            "Paradise! 🌺", "So peaceful! 🍃", "Breathtaking! 🌅"
        ],
        'food': [
            "Looks amazing! 😋", "So delicious! ✨", "Perfect! 👨‍🍳",
            "Beautiful dish! 🍽️", "Yummy! 😍", "Delightful! ✨"
        ],
        'lifestyle': [
            "Love this! ✨", "Beautiful vibes! 💫", "So lovely! 🌟",
            "Perfect! ✨", "Amazing! 🙌", "Beautiful! 💫"
        ],
        'art': [
            "Beautiful work! 🎨", "So creative! ✨", "Amazing art! 🌟",
            "Stunning piece! 💫", "Beautiful! 🎨", "Love this! ✨"
        ],
        'travel': [
            "Beautiful place! 🌎", "Paradise found! ✨", "Stunning view! 🌟",
            "Perfect spot! 💫", "Beautiful! 🌅", "Amazing! ✨"
        ],
        'fitness': [
            "Amazing work! 💪", "Looking strong! 🔥", "Incredible! ✨",
            "Pure strength! 💫", "Powerful! 💪", "Inspiring! 🌟"
        ],
        'generic': [
            "Love this! ✨", "Beautiful! 🌟", "Perfect! 💫", 
            "Amazing! 🙌", "Stunning! ✨", "Fantastic! 🌟"
        ]
    }
    
    # Keywords to identify content type
    content_types = {
        'photo': ['photo', 'pic', 'picture', 'shot', 'capture', 'moment', 'photography', 'camera'],
        'nature': ['nature', 'outdoor', 'landscape', 'mountain', 'beach', 'sea', 'sky', 'sunset', 'sunrise'],
        'food': ['food', 'meal', 'dish', 'recipe', 'cooking', 'restaurant', 'delicious', 'yummy', 'tasty'],
        'lifestyle': ['lifestyle', 'life', 'style', 'fashion', 'outfit', 'ootd', 'mood', 'vibes'],
        'art': ['art', 'artist', 'creative', 'design', 'drawing', 'painting', 'sketch', 'artwork'],
        'travel': ['travel', 'trip', 'journey', 'adventure', 'explore', 'wanderlust', 'vacation', 'holiday'],
        'fitness': ['fitness', 'workout', 'gym', 'exercise', 'training', 'health', 'fit', 'strong']
    }
    
    # Detect content type from caption and hashtags
    content_scores = {ctype: 0 for ctype in content_types.keys()}
    
    # Check words in caption
    for word in caption.split():
        for ctype, keywords in content_types.items():
            if word in keywords:
                content_scores[ctype] += 1
    
    # Select content type with highest score, default to generic
    max_score = max(content_scores.values())
    if max_score > 0:
        content_type = max(content_scores.items(), key=lambda x: x[1])[0]
    else:
        content_type = 'generic'
    
    # Get template list for content type
    template_list = templates[content_type]
    
    # Generate comment
    for _ in range(10):  # Try up to 10 times to get unique comment
        comment = random.choice(template_list)
        
        if comment.lower() not in used_comments:
            used_comments.add(comment.lower())
            return comment
    
    # If all attempts to get unique comment failed, use generic
    return generate_fallback_comment()

def generate_fallback_comment(caption=""):
    """Generate a simple, safe fallback comment"""
    fallbacks = [
        "Amazing!", "Love it!", "Great!", "Perfect!",
        "Beautiful!", "Wonderful!", "Fantastic!", "Brilliant!"
    ]
    return random.choice(fallbacks)

def clean_text(text):
    """Clean text to ensure it only contains BMP characters"""
    # Replace problematic emojis with simpler alternatives
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
    
    # First replace known problematic emojis
    for key, value in emoji_map.items():
        text = text.replace(key, value)
    
    # Then filter out any remaining non-BMP characters
    return ''.join(char for char in text if ord(char) < 0x10000)

def is_emoji(char):
    """Check if a character is an emoji"""
    try:
        # Emoji ranges
        ranges = [
            (0x1F300, 0x1F9FF),  # Miscellaneous Symbols and Pictographs
            (0x2600, 0x26FF),    # Miscellaneous Symbols
            (0x2700, 0x27BF),    # Dingbats
            (0x1F600, 0x1F64F),  # Emoticons
            (0x1F680, 0x1F6FF),  # Transport and Map Symbols
            (0x2300, 0x23FF),    # Miscellaneous Technical
            (0x1F900, 0x1F9FF),  # Supplemental Symbols and Pictographs
            (0x1FA70, 0x1FAFF),  # Symbols and Pictographs Extended-A
        ]
        return any(start <= ord(char) <= end for start, end in ranges)
    except:
        return False

def is_sponsored_post(driver, post_index):
    """Check if the current post is sponsored by looking for 'Sponsored' text under account name"""
    try:
        # Get the specific article context
        article = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.XPATH, f"(//article)[{post_index}]"))
        )
        
        # Look specifically for "Sponsored" text under account name
        sponsored_text = article.find_elements(By.XPATH, 
            ".//span[text()='Sponsored']"
        )
        
        if sponsored_text and any(elem.is_displayed() for elem in sponsored_text):
            log_activity("Found sponsored post (Sponsored text under account name)")
            return True
        
        return False
    except Exception as e:
        log_technical(f"Error checking sponsored post: {e}")
        return False

def check_engagement_levels(driver, is_local_account):
    """Check if the post meets engagement criteria based on local account preference"""
    if not is_local_account:
        return True  # If not local account, accept any engagement level
    
    try:
        # Check likes count
        try:
            likes_element = driver.find_element(By.XPATH, 
                "//section//article//a[contains(@href, '/liked_by/')] | //section//article//span[contains(@class, '_aacl') and contains(@class, '_aaco')]")
            likes_text = likes_element.text.lower()
            if 'likes' in likes_text or 'like' in likes_text:
                likes_count = int(''.join(filter(str.isdigit, likes_text)))
                if likes_count > 150:
                    log_activity(f"Skipping post with {likes_count} likes (too high engagement for local account)")
                    return False
        except:
            log_activity("Could not determine likes count, assuming within limits")

        # Check comments count
        try:
            comments_element = driver.find_element(By.XPATH, 
                "//a[contains(@href, '/comments/')]//span | //span[contains(text(), ' comments') or contains(text(), ' comment')]")
            comments_text = comments_element.text.lower()
            if 'comments' in comments_text or 'comment' in comments_text:
                comments_count = int(''.join(filter(str.isdigit, comments_text)))
                if comments_count > 50:
                    log_activity(f"Skipping post with {comments_count} comments (too high engagement for local account)")
                    return False
        except:
            log_activity("Could not determine comments count, assuming within limits")

        return True
    except Exception as e:
        log_activity(f"Error checking engagement levels: {e}")
        return True  # In case of error, proceed with interaction

def get_post_identifier(driver, post_element):
    """Get a unique identifier for a post with improved reliability"""
    try:
        # Try multiple ways to get a unique identifier
        identifiers = []
        
        # Try to get post URL
        try:
            post_link = post_element.find_element(By.XPATH, ".//a[contains(@href, '/p/')]")
            if post_link:
                post_url = post_link.get_attribute("href")
                if post_url:
                    identifiers.append(post_url)
        except:
            pass
        
        # Try to get post timestamp
        try:
            timestamp = post_element.find_element(By.XPATH, ".//time").get_attribute("datetime")
            if timestamp:
                identifiers.append(timestamp)
        except:
            pass
        
        # Try to get post image source
        try:
            img = post_element.find_element(By.XPATH, ".//img")
            if img:
                src = img.get_attribute("src")
                if src:
                    identifiers.append(src)
        except:
            pass
        
        # Try to get username of the poster
        try:
            username = post_element.find_element(By.XPATH, ".//a[contains(@href, '/')]").get_attribute("href")
            if username:
                identifiers.append(username)
        except:
            pass
        
        # If we have any identifiers, combine them
        if identifiers:
            return hash("|".join(identifiers))
        
        # Last resort: use the full HTML content
        content = post_element.get_attribute("outerHTML")
        if content:
            return hash(content)
        
        return None
    except Exception as e:
        log_activity(f"Error getting post identifier: {e}")
        return None

def refresh_element(driver, element, xpath):
    """Refresh a potentially stale element"""
    try:
        if element.is_enabled():  # Check if element is still valid
            return element
    except:
        pass
    
    try:
        # Try to find element again using its xpath
        return WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, xpath))
        )
    except Exception as e:
        log_activity(f"Error refreshing element: {e}")
        return None

def handle_caught_up_message(driver):
    """Handle 'You're all caught up' message by scrolling past it"""
    try:
        caught_up = driver.find_element(By.XPATH, 
            "//div[contains(text(), 'You')]//div[contains(text(), 'caught up')] | " +
            "//span[contains(text(), 'You')]//span[contains(text(), 'caught up')]"
        )
        if caught_up.is_displayed():
            log_activity("Found 'You're all caught up' message, scrolling to load more posts...")
            # Scroll past the message
            driver.execute_script("window.scrollBy(0, 1000);")
            time.sleep(3)
            # Scroll a bit more to ensure new content loads
            driver.execute_script("window.scrollBy(0, 500);")
            time.sleep(2)
            return True
    except:
        pass
    return False

def get_caption(driver, post_element, posts_checked):
    """Get caption from post with improved accuracy"""
    try:
        # First try to click "more" if it exists
        try:
            more_button = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, 
                    f"(//article)[{posts_checked}]//span[contains(@class, 'x1lliihq') and contains(text(), 'more')]"
                ))
            )
            driver.execute_script("arguments[0].scrollIntoView(true);", more_button)
            time.sleep(1)
            driver.execute_script("arguments[0].click();", more_button)
            log_technical("Clicked 'more' button to reveal full caption")
            time.sleep(2)
        except Exception as e:
            # Only log to technical log, not activity feed
            log_technical(f"No 'more' button found or not clickable: {str(e)}")
        
        # Try to get caption using multiple selectors
        caption_selectors = [
            f"(//article)[{posts_checked}]//span[contains(@class, '_ap3a')]//span[contains(@class, '_ap3a')]",
            f"(//article)[{posts_checked}]//div[contains(@class, 'x9f619')]//span[contains(@class, '_ap3a')]",
            f"(//article)[{posts_checked}]//span[contains(@class, '_ap3a') and contains(@class, '_aaco')]"
        ]
        
        for selector in caption_selectors:
            try:
                caption_element = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.XPATH, selector))
                )
                caption = caption_element.text.strip()
                if caption:
                    log_technical(f"Scraped caption: '{caption}'")
                    return caption
            except:
                continue
        
        log_technical("Could not find caption with any selector")
        return "No caption found"
    except Exception as e:
        log_technical(f"Caption scraping failed: {str(e)}")
        return "No caption found"

def scroll_to_next_post(driver, current_post_index):
    """Scroll to ensure the next post is in view and verify it's a new post"""
    max_attempts = 3
    current_post_url = None
    
    # Get current post URL for comparison
    try:
        current_post_url = driver.find_element(By.XPATH, f"(//article)[{current_post_index}]//a[contains(@href, '/p/')]").get_attribute("href")
    except:
        pass
    
    # First, ensure we're completely out of the current post's context
    try:
        # Click on a neutral area and scroll away from current post
        driver.execute_script("""
            document.activeElement.blur();
            window.scrollBy(0, 400);
        """)
        time.sleep(2)
        
        # Press Escape key to exit any potential overlays or popups
        ActionChains(driver).send_keys(Keys.ESCAPE).perform()
        time.sleep(1)
    except Exception as e:
        log_activity(f"Warning during context exit: {e}")
    
    for attempt in range(max_attempts):
        try:
            # Try to find the next post
            next_post = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, f"(//article)[{current_post_index + 1}]"))
            )
            
            # Get next post URL
            try:
                next_post_url = next_post.find_element(By.XPATH, ".//a[contains(@href, '/p/')]").get_attribute("href")
                if current_post_url and next_post_url == current_post_url:
                    log_activity("Still on same post, scrolling more...")
                    driver.execute_script("window.scrollBy(0, 800);")
                    time.sleep(3)
                    continue
            except:
                pass
            
            # Scroll to next post
            driver.execute_script("""
                arguments[0].scrollIntoView({
                    behavior: 'smooth',
                    block: 'center'
                });
                window.scrollBy(0, -100);
            """, next_post)
            time.sleep(3)
            
            # Verify the post is visible and we can interact with it
            if next_post.is_displayed():
                # Double check we're not on a sponsored post
                if is_sponsored_post(driver, current_post_index + 1):
                    log_activity("Next post is sponsored, scrolling more...")
                    driver.execute_script("window.scrollBy(0, 800);")
                    time.sleep(3)
                    continue
                    
                return True
        except:
            log_activity(f"Attempt {attempt + 1} to find next post failed, scrolling to load more...")
            driver.execute_script("window.scrollBy(0, 800);")
            time.sleep(3)
    
    log_activity("Failed to find next post after multiple attempts")
    return False

def post_comment(driver, post_index, comment):
    """Post a comment with improved reliability"""
    max_attempts = 3
    for attempt in range(max_attempts):
        try:
            # Find and clear comment field
            comment_field = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, 
                    f"(//article)[{post_index}]//textarea[@placeholder='Add a comment…']"
                ))
            )
            
            # Clear field and focus it
            comment_field.clear()
            driver.execute_script("arguments[0].click();", comment_field)
            time.sleep(1)
            
            # Clean comment text
            cleaned_comment = clean_text(comment)
            
            # Type comment character by character with random delays
            for char in cleaned_comment:
                comment_field.send_keys(char)
                time.sleep(random.uniform(0.05, 0.2))  # Random delay between keystrokes
            
            time.sleep(random.uniform(0.5, 1.0))  # Natural pause before submitting
            
            # Submit comment
            comment_field.send_keys(Keys.RETURN)
            time.sleep(3)
            
            # Verify comment was posted
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

def verify_post_match(driver, post_index, original_url=None):
    """Simplified post verification"""
    try:
        # Verify post is present and visible
        post = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.XPATH, f"(//article)[{post_index}]"))
        )
        
        if not post.is_displayed():
            log_activity("Post not visible")
            return False
            
        # If we have an original URL, verify it matches
        if original_url:
            try:
                current_url = post.find_element(By.XPATH, ".//a[contains(@href, '/p/')]").get_attribute("href")
                if current_url and current_url != original_url:
                    log_activity("Post URL changed")
                    return False
            except:
                pass
        
        return True
    except Exception as e:
        log_technical(f"Post verification error: {e}")
        return False

def process_post(driver, post, post_index, used_comments, processed_posts, is_local_account=False):
    """Process a single post"""
    try:
        # Check if post is already liked first
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
            log_technical(f"Error checking like status: {e}")
            return False

        # Check if post is sponsored first, before any other processing
        try:
            sponsored_text = post.find_element(By.XPATH, ".//span[contains(text(), 'Sponsored')]")
            if sponsored_text and sponsored_text.is_displayed():
                log_activity("Found sponsored post (Sponsored text under account name)")
                log_activity("Skipping sponsored post")
                return False
        except:
            pass  # Not a sponsored post, continue processing

        # Get post URL for logging and verification
        try:
            post_link = post.find_element(By.XPATH, ".//a[contains(@href, '/p/')]")
            post_url = post_link.get_attribute('href')
            log_activity(f"Processing post URL: {post_url}")
        except:
            log_activity("Could not get post URL")
            post_url = None

        # Check for sponsored content first
        if is_sponsored_post(driver, post_index):
            log_activity("Skipping sponsored post")
            return False
        
        # Check engagement levels for local account mode
        if not check_engagement_levels(driver, is_local_account):
            log_activity("Skipping post due to high engagement")
            return False
        
        # Get post identifier
        post_id = get_post_identifier(driver, post)
        if post_id in processed_posts:
            log_activity("Already processed this post")
            return False
        
        # Get caption
        caption = get_caption(driver, post, post_index)
        if caption == "No caption found":
            log_activity("No caption found")
            return False
        
        # Generate comment
        comment = generate_comment(caption, used_comments)
        if not comment:
            log_activity("Failed to generate comment")
            return False
        
        # Like and comment
        try:
            # Verify we're still on the same post before interacting
            if not verify_post_match(driver, post_index, post_url):
                log_activity("Post changed during processing, skipping...")
                return False

            # Like the post
            like_button = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.XPATH, 
                    f"(//article)[{post_index}]//div[contains(@class, 'x1i10hfl') and .//*[name()='svg' and @aria-label='Like']]"
                ))
            )
            
            # Double check it's not already liked
            if "liked" not in like_button.get_attribute("class").lower():
                driver.execute_script("arguments[0].click();", like_button)
                log_activity("Post liked successfully")
                time.sleep(2)
            
            # Verify again before commenting
            if not verify_post_match(driver, post_index, post_url):
                log_activity("Post changed after liking, skipping comment...")
                return False
            
            # Post comment
            if post_comment(driver, post_index, comment):
                if post_id:
                    processed_posts.add(post_id)
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

def is_inappropriate_content(caption):
    """Check if content is inappropriate or overly negative"""
    # List of terms indicating inappropriate or negative content
    inappropriate_terms = [
        'hate', 'kill', 'death', 'violence', 'racist', 'discrimination',
        'nsfw', 'explicit', 'scam', 'spam', 'fake', 'fraud',
        'illegal', 'drugs', 'weapon', 'gambling', 'betting'
    ]
    
    caption_lower = caption.lower()
    for term in inappropriate_terms:
        if term in caption_lower:
            log_activity(f"Found inappropriate term: {term}")
            return True
    
    return False

def handle_popups(driver):
    """Handle both Save Login Info and Meta popups systematically"""
    max_attempts = 5
    
    for attempt in range(max_attempts):
        try:
            # First handle Save Login Info popup if present
            try:
                save_login_button = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[text()='Not Now']"))
                )
                if save_login_button.is_displayed():
                    driver.execute_script("arguments[0].click();", save_login_button)
                    log_activity("Clicked 'Not Now' on Save Login Info popup")
                    time.sleep(2)
            except:
                pass

            # Then handle Meta popup by clicking outside
            try:
                # First try clicking the Instagram logo
                logo = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.XPATH, "//i[contains(@class, 'instagram')]"))
                )
                actions = ActionChains(driver)
                actions.move_to_element(logo).click().perform()
                log_activity("Clicked Instagram logo to dismiss popup")
                time.sleep(2)
            except:
                try:
                    # If logo not found, click in the top-left corner of the screen
                    actions = ActionChains(driver)
                    actions.move_by_offset(10, 10).click().perform()
                    log_activity("Clicked top-left corner to dismiss popup")
                    time.sleep(2)
                except:
                    pass

            # Verify popup is gone
            try:
                popup = driver.find_element(By.CSS_SELECTOR, "._a9--")
                if not popup.is_displayed():
                    log_activity("Popup successfully dismissed")
                    return True
            except:
                log_activity("Popup successfully dismissed")
                return True

        except Exception as e:
            log_activity(f"Attempt {attempt + 1} failed: {e}")
            if attempt == max_attempts - 1:
                log_activity(f"Failed to handle popup after {max_attempts} attempts")
                return False
            time.sleep(2)
    
    return False

def login_to_instagram(driver, username, password):
    """Handle login and initial popups"""
    try:
        # Find and fill username field
        username_field = WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.NAME, "username")))
        username_field.clear()
        username_field.send_keys(username)
        log_activity("Entered username")
        
        # Find and fill password field
        password_field = WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.NAME, "password")))
        password_field.clear()
        password_field.send_keys(password)
        log_activity("Entered password")
        
        # Submit login
        password_field.send_keys(Keys.RETURN)
        log_activity("Login attempt submitted, waiting for response...")
        time.sleep(10)  # Wait for login to complete
        
        # Always try to click "Not Now" on Save Login Info page
        try:
            save_info_button = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, "//button[text()='Not Now']"))
            )
            save_info_button.click()
            log_activity("Clicked 'Not Now' on Save Login Info page")
        except:
            log_activity("No Save Login Info page found or already handled")
        
        time.sleep(2)  # Wait a moment between actions
        
        # Always try to click outside Meta popup
        try:
            action = ActionChains(driver)
            action.move_by_offset(1, 1).click().perform()
            log_activity("Clicked top-left corner to dismiss Meta popup")
            action.move_by_offset(-1, -1).perform()  # Reset mouse position
        except:
            log_activity("Could not click to dismiss Meta popup")
        
        time.sleep(2)  # Wait for any popups to clear
        
        # Verify we reached the feed
        try:
            # Initial scroll to load posts
            log_activity("Performing initial scroll to load posts...")
            driver.execute_script("window.scrollBy(0, 500);")
            time.sleep(2)
            driver.execute_script("window.scrollBy(0, 500);")
            time.sleep(2)
            driver.execute_script("window.scrollTo(0, 0);")  # Back to top
            time.sleep(3)
            
            # Verify feed access
            WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.XPATH, "//div[@role='feed'] | //article"))
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
        # Set up logging first
        log_file = setup_logging()
        log_technical(f"Log file created: {log_file}")
        
        args = parse_arguments()
        log_activity(f"Starting bot with username: {args.username}")
        
        # Initialize processed posts set
        processed_posts = set()
        used_comments = set()
        
        # Convert local_account string to boolean
        is_local_account = args.local_account.lower() == 'true'
        if is_local_account:
            log_activity("Local account mode: Will only interact with low engagement posts")
        
        # Set up Selenium
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
        time.sleep(7)

        try:
            log_activity("Attempting to log in...")
            if login_to_instagram(driver, args.username, args.password):
                log_activity("Starting to process posts...")
                
                # Process posts one by one
                successful_interactions = 0
                posts_checked = 0
                max_attempts = args.interactions * 3  # Allow more attempts to find valid posts
                
                while successful_interactions < args.interactions and posts_checked < max_attempts:
                    posts_checked += 1
                    current_post_index = posts_checked
                    
                    try:
                        # Try to find the current post
                        post = WebDriverWait(driver, 10).until(
                            EC.presence_of_element_located((By.XPATH, f"(//article)[{current_post_index}]"))
                        )
                        
                        # Ensure post is in view
                        driver.execute_script("""
                            arguments[0].scrollIntoView({
                                behavior: 'smooth',
                                block: 'center'
                            });
                        """, post)
                        time.sleep(2)
                        
                        # Process the post
                        if process_post(driver, post, current_post_index, used_comments, processed_posts, is_local_account):
                            successful_interactions += 1
                            log_activity(f"Successfully processed post {successful_interactions}/{args.interactions}")
                        else:
                            log_activity(f"Skipped or failed to process post {current_post_index}")
                        
                        # Move to next post
                        if successful_interactions < args.interactions:
                            driver.execute_script("window.scrollBy(0, 400);")
                            time.sleep(2)
                            
                    except Exception as e:
                        log_activity(f"Error processing post: {e}")
                        # Try to recover by scrolling
                        driver.execute_script("window.scrollBy(0, 400);")
                        time.sleep(2)
                
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