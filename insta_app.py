import tkinter as tk
from tkinter import ttk
import subprocess
import sys
import threading
import os

# Create the main window
root = tk.Tk()
root.title("Social Media Bot")
root.geometry("800x500")

# Frame for input controls, centered with padding to move up
input_frame = tk.Frame(root)
input_frame.pack(expand=True, pady=20)  # Added padding to shift up

# Labels and entries
tk.Label(input_frame, text="Platform:").pack()
platform = ttk.Combobox(input_frame, values=["Instagram", "Facebook"], state="readonly")
platform.set("Instagram")
platform.pack()

tk.Label(input_frame, text="Username:").pack()
username_entry = tk.Entry(input_frame, width=40)
username_entry.pack()

tk.Label(input_frame, text="Password:").pack()
password_entry = tk.Entry(input_frame, width=40)
password_entry.pack()

tk.Label(input_frame, text="Number of Posts (max 20):").pack()
posts_entry = tk.Entry(input_frame, width=40)
posts_entry.pack()

# Launch button
tk.Button(input_frame, text="Launch", command=lambda: launch_bot()).pack()

# Label for the latest update (expanded to 3 lines, placed below input)
output_label = tk.Label(root, text="Status: Waiting to start...", width=50, height=3, bg="#F0F0F0", fg="black", relief=tk.SUNKEN, bd=2, anchor="nw", justify="left")
output_label.place(relx=0.5, rely=0.85, anchor="center")  # Positioned below the button

# Function to launch the bot in a separate thread and filter updates
def launch_bot():
    username = username_entry.get()
    password = password_entry.get()
    posts = posts_entry.get()
    try:
        num_posts = int(posts)
        if num_posts > 20:
            num_posts = 20  # Cap at 20
    except ValueError:
        num_posts = 1  # Default to 1 if invalid
    output_label.config(text=f"Preparing to launch bot for {username}...")

    # Run the bot script with credentials in a separate thread
    cmd = f"python -u test_caption_scraper.py {username} {password} {num_posts}"  # -u for unbuffered

    def run_bot():
        try:
            # Set encoding to UTF-8 and enable unbuffered output
            env = os.environ.copy()
            env["PYTHONUNBUFFERED"] = "1"  # Force unbuffered output
            process = subprocess.Popen(
                cmd,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding='utf-8',
                errors='replace',
                env=env
            )
            output_label.config(text=f"Attempting to log in for {username}...")
            # Read output and filter for user-relevant messages
            for line in process.stdout:
                if line:
                    if "Login successful" in line:
                        output_label.config(text="Login successful!")
                    elif "Login failed" in line:
                        output_label.config(text="Login failed: Check credentials.")
                    elif "Failed to run bot" in line:
                        output_label.config(text="Bot failed to start.")
                    elif "Started bot" in line:
                        output_label.config(text="Bot started.")
                    elif "Fetching posts" in line:
                        output_label.config(text="Fetching posts...")
                    elif "Test complete" in line:
                        output_label.config(text="Process complete.")
                    elif "Initializing ChromeDriver" in line:
                        output_label.config(text="Credentials entered.")
                    elif "Passed pop-ups" in line or "All pop-ups dismissed" in line:
                        output_label.config(text="Passed pop-ups.")
                    elif "Scraped full caption" in line:
                        # Extract the caption from the line
                        caption = line.split("Scraped full caption for post")[1].split(":")[1].strip().strip("'")
                        output_label.config(text=f"Scraping caption...\nCaption: {caption}")
                    elif "Generated comment for post" in line:
                        # Extract the comment from the line
                        comment = line.split("Generated comment for post")[1].split(":")[1].strip().strip("'")
                        # Append the comment to the current text
                        current_text = output_label.cget("text")
                        output_label.config(text=f"{current_text}\nComment: {comment}")
                    root.update()  # Force GUI update
            process.wait()  # Wait for the process to finish
            if process.returncode != 0:
                output_label.config(text="Process failed.")
        except Exception as e:
            output_label.config(text="An error occurred.")

    # Start the bot in a separate thread
    threading.Thread(target=run_bot, daemon=True).start()

# Start the app
root.mainloop()