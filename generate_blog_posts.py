import os
import json
import base64
import requests
import pandas as pd
from datetime import datetime
import re # For sanitizing filenames
import hashlib # For creating unique hashes of CSV rows
import markdown # For converting Markdown to HTML

# --- Configuration (Pulled from GitHub Actions Environment Variables) ---
GITHUB_REPO_OWNER = os.environ.get("GITHUB_REPO_OWNER")
GITHUB_REPO_NAME = os.environ.get("GITHUB_REPO_NAME")
GITHUB_BRANCH = os.environ.get("GITHUB_BRANCH")
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")

# --- API Endpoints ---
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
IMAGEN_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/imagen-3.0-generate-002:predict"

# --- File Paths ---
PROCESSED_POSTS_FILE = "processed_posts.txt" # File to keep track of processed CSV rows
CSV_FILE_NAME = "blog.csv" # Specifically targets your 'blog.csv' file

# --- Helper Functions ---

def sanitize_filename(text):
    """
    Converts a given text string into a URL-friendly and filename-safe format.
    Removes special characters, replaces spaces with hyphens, and limits length.
    """
    text = text.lower()
    # Remove non-alphanumeric characters except spaces and hyphens
    text = re.sub(r'[^a-z0-9\s-]', '', text)
    # Replace one or more spaces with a single hyphen
    text = re.sub(r'\s+', '-', text)
    # Remove leading/trailing hyphens
    text = text.strip('-')
    # Limit length to avoid excessively long filenames, adjust as needed
    return text[:60]

def remove_emojis(text):
    """Removes emojis from a string."""
    # This regex matches common emoji unicode ranges
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"  # emoticons
        "\U0001F300-\U0001F5FF"  # symbols & pictographs
        "\U0001F680-\U0001F6FF"  # transport & map symbols
        "\U0001F1E0-\U0001F1FF"  # flags (iOS)
        "\U00002702-\U000027B0"
        "\U000024C2-\U0001F251"
        "]+", flags=re.UNICODE
    )
    return emoji_pattern.sub(r'', text)

def get_row_hash(row):
    """
    Generates a unique hash for a CSV row based on key content (excluding 'Time').
    This helps in identifying if a row has already been processed.
    """
    # Using 'Platform', 'Text', and 'Hyperlink' for uniqueness since 'Time' is removed
    unique_string = f"{row.get('Platform', '')}-{row.get('Text', '')}-{row.get('Hyperlink', '')}"
    return hashlib.sha256(unique_string.encode('utf-8')).hexdigest()

def load_processed_posts():
    """Loads the set of hashes for already processed posts from the tracking file."""
    if os.path.exists(PROCESSED_POSTS_FILE):
        with open(PROCESSED_POSTS_FILE, 'r', encoding='utf-8') as f:
            return set(line.strip() for line in f if line.strip())
    return set()

def save_processed_post(row_hash):
    """Adds a new post hash to the tracking file."""
    with open(PROCESSED_POSTS_FILE, 'a', encoding='utf-8') as f:
        f.write(row_hash + '\n')

def call_gemini_api(prompt_text):
    """
    Calls the Google Gemini API (gemini-2.0-flash) to generate text content.
    Returns the generated text or None if an error occurs.
    """
    headers = {'Content-Type': 'application/json'}
    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt_text}]}],
        "generationConfig": {
            "temperature": 0.7,
            "topP": 0.95,
            "topK": 40,
            "maxOutputTokens": 1500, # Increased max output tokens for longer articles
        }
    }
    try:
        response = requests.post(f"{GEMINI_API_URL}?key={GOOGLE_API_KEY}", headers=headers, json=payload)
        response.raise_for_status()
        result = response.json()
        if result.get("candidates") and result["candidates"][0].get("content") and result["candidates"][0]["content"].get("parts"):
            return result["candidates"][0]["content"]["parts"][0]["text"]
        else:
            print(f"Gemini API response missing content: {result}")
            return None
    except requests.exceptions.RequestException as e:
        print(f"Error calling Gemini API: {e}")
        return None

def call_imagen_api(prompt_text):
    """
    Calls the Google Imagen API (imagen-3.0-generate-002) to generate an image.
    Returns the base64 encoded image data or None if an error occurs.
    """
    headers = {'Content-Type': 'application/json'}
    payload = {
        "instances": {"prompt": prompt_text},
        "parameters": {"sampleCount": 1}
    }
    try:
        response = requests.post(f"{IMAGEN_API_URL}?key={GOOGLE_API_KEY}", headers=headers, json=payload)
        response.raise_for_status()
        result = response.json()
        if result.get("predictions") and result["predictions"][0].get("bytesBase64Encoded"):
            return result["predictions"][0]["bytesBase64Encoded"]
        else:
            print(f"Imagen API response missing image data: {result}")
            return None
    except requests.exceptions.RequestException as e:
        print(f"Error calling Imagen API: {e}")
        return None

def generate_blog_post_html(title, content, image_url, affiliate_link, author="Codestrym Staff", date=None):
    """
    Generates the complete HTML content for a single blog post page,
    including a prominent affiliate link button.
    """
    if date is None:
        date = datetime.now().strftime("%B %d, %Y")

    # Corrected base_public_path for GitHub Pages project sites
    base_public_path = f"https://{GITHUB_REPO_OWNER}.github.io/{GITHUB_REPO_NAME}"

    display_affiliate_link = affiliate_link if affiliate_link and affiliate_link.startswith('http') else '#'

    # Convert Markdown content to HTML
    html_content = markdown.markdown(content)

    html_template = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <!-- Tailwind CSS CDN for styling -->
    <script src="https://cdn.tailwindcss.com"></script>
    <!-- Google Fonts - Inter for consistent typography -->
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        body {{
            font-family: 'Inter', sans-serif;
            background-color: #f8fafc;
            line-height: 1.6;
            color: #333;
        }}
        .blog-content h1, .blog-content h2, .blog-content h3 {{
            margin-top: 1.5em;
            margin-bottom: 0.5em;
            font-weight: 600;
        }}
        .blog-content p {{
            margin-bottom: 1em;
        }}
        .blog-content ul, .blog-content ol {{
            margin-left: 1.5em;
            margin-bottom: 1em;
            list-style-type: disc;
        }}
        .blog-content ol {{
            list-style-type: decimal;
        }}
        .affiliate-button-container {{
            margin-top: 2.5rem; /* More space above the button */
            margin-bottom: 2.5rem; /* More space below the button */
            text-align: center;
        }}
        .affiliate-button {{
            display: inline-block;
            background-color: #ef4444; /* Red color for prominence */
            color: white;
            padding: 1rem 2rem; /* Larger padding */
            border-radius: 0.75rem; /* More rounded corners */
            font-size: 1.25rem; /* Larger font size */
            font-weight: 700; /* Bold text */
            text-decoration: none;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1); /* Subtle shadow */
            transition: background-color 0.3s ease, transform 0.2s ease;
        }}
        .affiliate-button:hover {{
            background-color: #dc2626; /* Darker red on hover */
            transform: translateY(-2px); /* Slight lift effect */
        }}
        .affiliate-button:active {{
            transform: translateY(0); /* Press down effect */
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        }}
    </style>
</head>
<body class="flex flex-col min-h-screen">
    <!-- Header Section - Consistent with your blog.html structure -->
    <header class="bg-white shadow-md py-4 px-6 md:px-10 lg:px-16">
        <div class="container mx-auto flex justify-between items-center">
            <h1 style="font-size: 20px;">
                <span style="color: black;">C</span>
                <span style="color: black;">o</span>
                <span style="color: black;">d</span>
                <span style="color: black;">e</span>
                <span style="color: red;">S</span>
                <span style="color: green;">t</span>
                <span style="color: purple;">r</span>
                <span style="color: orange;">y</span>
                <span style="color: blue;">m</span>
            </h1>
            <nav>
                <ul class="flex space-x-4">
                    <li><a href="{base_public_path}/index.html" class="text-gray-600 hover:text-blue-600 font-medium transition duration-300">Home</a></li>
                    <li><a href="{base_public_path}/blog.html" class="text-blue-600 hover:text-blue-700 font-medium transition duration-300">Blog</a></li>
                    <li><a href="#" class="text-gray-600 hover:text-blue-600 font-medium transition duration-300">About</a></li>
                    <li><a href="#" class="text-gray-600 hover:text-blue-600 font-medium transition duration-300">Contact</a></li>
                </ul>
            </nav>
        </div>
    </header>

    <!-- Main Content Area for the single blog post -->
    <main class="flex-grow container mx-auto px-4 py-8 md:py-12 max-w-3xl">
        <article class="bg-white rounded-xl shadow-lg p-8">
            <h1 class="text-4xl font-extrabold text-gray-900 mb-4">{title}</h1>
            <div class="text-gray-500 text-sm mb-6">
                <span>By : {author}</span> &bull; <span>{date}</span>
            </div>
            <img src="{image_url}" alt="{title} image" class="w-full rounded-lg mb-8 object-cover max-h-96">
            <div class="blog-content text-gray-700 text-lg">
                {html_content}
            </div>
            
            <div class="affiliate-button-container">
                <a href="{display_affiliate_link}" target="_blank" rel="noopener noreferrer" class="affiliate-button">
                    Click Here for the Best Deal!
                </a>
            </div>

            <div class="mt-8 text-center">
                <a href="{base_public_path}/blog.html" class="inline-block bg-blue-600 text-white px-6 py-3 rounded-lg hover:bg-blue-700 transition duration-300 font-medium">Back to Blog</a>
            </div>
        </article>
    </main>

    <!-- Footer Section - Consistent with your blog.html structure -->
    <footer class="bg-gray-800 text-white py-6 px-4 md:px-10 lg:px-16 mt-8">
        <div class="container mx-auto text-center text-sm">
            <p>&copy; {datetime.now().year} Codestrym. All rights reserved.</p> <!-- Corrected text here -->
            <p class="mt-2">
                <a href="#" class="text-gray-400 hover:text-white transition duration-300">Privacy Policy</a> |
                <a href="#" class="text-gray-400 hover:text-white transition duration-300">Terms of Service</a>
            </p>
        </div>
    </footer>
</body>
</html>
    """
    return html_template

def update_blog_index(new_post_info):
    """
    Reads the main blog.html file, inserts a new blog post card,
    and updates the file locally within the GitHub Actions runner.
    This updated file will then be committed back to the repository.
    """
    blog_index_path = "blog.html"

    try:
        with open(blog_index_path, 'r', encoding='utf-8') as f:
            blog_content = f.read()
    except FileNotFoundError:
        print(f"Error: {blog_index_path} not found. Please ensure it exists in the repository root.")
        return False

    # --- IMPORTANT CHANGES HERE: Author, and button layout ---
    new_card_html = f"""
            <!-- Automated Blog Post Card - {new_post_info['title']} -->
            <div class="bg-white rounded-xl shadow-lg hover:shadow-xl transition-shadow duration-300 overflow-hidden">
                <img src="{new_post_info['image_url']}" alt="{new_post_info['title']} image" class="w-full h-48 object-cover">
                <div class="p-6 flex flex-col"> <!-- Added flex flex-col to make content area a flex container -->
                    <h2 class="text-xl font-semibold text-gray-800 mb-2">{new_post_info['title']}</h2>
                    <p class="text-gray-600 text-sm mb-4 flex-grow">{new_post_info['summary']}</p> <!-- Added flex-grow to push content down -->
                    <div class="flex items-center text-gray-500 text-xs mb-4">
                        <span class="mr-3">By : {new_post_info['author']}</span>
                        <span>{new_post_info['date']}</span>
                    </div>
                    
                    <div class="flex justify-center space-x-4 mt-4">
                        <a href="{new_post_info['affiliate_link']}" target="_blank" rel="noopener noreferrer" class="inline-block bg-red-500 hover:bg-red-600 text-white font-bold py-2 px-4 rounded-lg text-sm transition duration-300">
                            Shop Now!
                        </a>
                        <a href="{new_post_info['post_url']}" class="inline-block bg-blue-600 text-white px-5 py-2 rounded-lg hover:bg-blue-700 transition duration-300 font-medium">Read More</a>
                    </div>
                </div>
            </div>
            <!-- End Automated Blog Post Card -->
    """

    insertion_point = '        </div>\n    </main>'

    if insertion_point in blog_content:
        updated_content = blog_content.replace(insertion_point, new_card_html + insertion_point, 1)
        with open(blog_index_path, 'w', encoding='utf-8') as f:
            f.write(updated_content)
        print(f"Successfully updated {blog_index_path} locally.")
        return True
    else:
        print(f"Could not find insertion point in {blog_index_path}. Manual update may be needed.")
        return False

# --- Main Script Logic ---

def main():
    if not GOOGLE_API_KEY:
        print("Error: GOOGLE_API_KEY environment variable not set. Please add it as a GitHub Secret.")
        return

    if not GITHUB_REPO_OWNER or not GITHUB_REPO_NAME or not GITHUB_BRANCH:
        print("Error: GitHub repository details not fully configured in environment variables.")
        return

    csv_file_path = CSV_FILE_NAME # Use the specific CSV file name
    try:
        df = pd.read_csv(csv_file_path)
    except FileNotFoundError:
        print(f"Error: CSV file '{csv_file_path}' not found. Please ensure it's in the repository root.")
        return
    except Exception as e:
        print(f"Error reading CSV file: {e}")
        return

    processed_posts_hashes = load_processed_posts()
    newly_processed_hashes = set()

    posts_to_process_in_this_run = []

    # Process all rows in blog.csv, as time-based filtering is removed
    for index, row in df.iterrows():
        row_hash = get_row_hash(row)
        if row_hash not in processed_posts_hashes:
            posts_to_process_in_this_run.append((index, row, row_hash))
        else:
            print(f"Skipping row {index} (already processed).")

    if not posts_to_process_in_this_run:
        print("No new posts found in blog.csv or all posts already processed.")
        return

    print(f"Found {len(posts_to_process_in_this_run)} new post(s) to process from {CSV_FILE_NAME}.")

    for index, row, row_hash in posts_to_process_in_this_run:
        post_text = row.get('Text', '')
        image_category = row.get('images', '').strip('/')
        affiliate_link = row.get('Hyperlink', '#') # Get the affiliate link

        if not post_text:
            print(f"Skipping row {index} due to missing 'Text' content.")
            continue
        
        keyword_for_ai = image_category if image_category else post_text.split('.')[0].strip()

        print(f"\nProcessing new row {index}: Social Text='{post_text}', AI Keyword='{keyword_for_ai}'")

        # 1. Generate Blog Post Text
        # Refined prompt to avoid "Summary:" prefix and encourage Markdown for structure
        text_prompt = f"Write a comprehensive and engaging blog post about '{keyword_for_ai}' based on the idea: '{post_text}'. The post should include an introduction, 2-3 main sections with clear Markdown headings (e.g., '## Section Title'), and a conclusion. Ensure the content flows naturally with paragraphs. The tone should be informative and slightly enthusiastic. Provide a concise summary (1-2 sentences) at the very beginning of the response, *without* explicitly labeling it 'Summary:'. Do not use emojis or excessive special characters like asterisks or hashtags within the main body of the text, only for Markdown formatting."
        generated_text_with_summary = call_gemini_api(prompt_text)

        if not generated_text_with_summary:
            print(f"Failed to generate blog post text for row {index}. Skipping.")
            continue

        # Extract summary and full content
        summary_end_index = generated_text_with_summary.find('\n\n')
        if summary_end_index != -1:
            summary = generated_text_with_summary[:summary_end_index].strip()
            full_content = generated_text_with_summary[summary_end_index:].strip()
        else:
            summary = generated_text_with_summary[:150].strip() + "..."
            full_content = generated_text_with_summary.strip()
        
        # Post-process: Remove emojis from full content
        full_content = remove_emojis(full_content)
        summary = remove_emojis(summary)

        # 2. Generate Image
        image_prompt = f"A vibrant and engaging image representing '{keyword_for_ai}'. Focus on concepts related to {keyword_for_ai}."
        generated_image_base64 = call_imagen_api(image_prompt)

        if not generated_image_base64:
            print(f"Failed to generate image for row {index}. Skipping.")
            continue

        # 3. Prepare file names and paths
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        sanitized_title = sanitize_filename(keyword_for_ai)
        post_filename_relative = f"posts/{timestamp}-{sanitized_title}.html"
        image_filename_relative = f"images/{timestamp}-{sanitized_title}.png"

        os.makedirs(os.path.dirname(post_filename_relative), exist_ok=True)
        os.makedirs(os.path.dirname(image_filename_relative), exist_ok=True)

        # Corrected base_public_path for GitHub Pages project sites
        base_public_path = f"https://{GITHUB_REPO_OWNER}.github.io/{GITHUB_REPO_NAME}"
        image_public_url = f"{base_public_path}/{image_filename_relative}"
        post_public_url = f"{base_public_path}/{post_filename_relative}"

        # 4. Save the generated image locally
        try:
            with open(image_filename_relative, 'wb') as f:
                f.write(base64.b64decode(generated_image_base64))
            print(f"Image saved locally: {image_filename_relative}")
        except Exception as e:
            print(f"Error saving image locally {image_filename_relative}: {e}")
            continue

        # 5. Create the new blog post HTML file content
        blog_post_html_content = generate_blog_post_html(
            title=keyword_for_ai.replace('-', ' ').title(),
            content=full_content, # This content will now be Markdown and converted to HTML
            image_url=image_public_url,
            affiliate_link=affiliate_link, # Pass the affiliate link to the full post HTML
            author="Codestrym Staff", # Explicitly set author for full post
            date=datetime.now().strftime("%B %d, %Y")
        )

        # 6. Save the new blog post HTML file locally
        try:
            with open(post_filename_relative, 'w', encoding='utf-8') as f:
                f.write(blog_post_html_content)
            print(f"Blog post HTML saved locally: {post_filename_relative}")
        except Exception as e:
            print(f"Error saving blog post HTML locally {post_filename_relative}: {e}")
            continue

        # 7. Update blog.html index locally
        new_post_info = {
            "title": keyword_for_ai.replace('-', ' ').title(),
            "summary": summary,
            "image_url": image_public_url,
            "post_url": post_public_url,
            "affiliate_link": affiliate_link, # Pass the affiliate link to the index update
            "author": "Codestrym Staff", # Explicitly set author for snippet
            "date": datetime.now().strftime("%B %d, %Y")
        }
        if not update_blog_index(new_post_info):
            print(f"Warning: Failed to update blog.html for post '{keyword_for_ai}'.")
        
        newly_processed_hashes.add(row_hash)

    if newly_processed_hashes:
        print(f"\nSaving {len(newly_processed_hashes)} newly processed post hashes to {PROCESSED_POSTS_FILE}...")
        for h in newly_processed_hashes:
            save_processed_post(h)
    else:
        print("\nNo new posts were processed in this run.")

    print("\nBlog post generation and local updates complete. The GitHub Actions 'Commit and push changes' step will now push these files to your repository.")

if __name__ == "__main__":
    main()
