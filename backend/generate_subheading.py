"""
Generate unique subheadings from a base prompt using OpenRouter API
This module uses GPT-OSS-20B model to generate subheadings and ensures
they are semantically unique using the SemanticSimilarityChecker.
"""
import os

import requests
import json
from backend.similarity_checker_cosine import SemanticSimilarityChecker
from dotenv import load_dotenv

load_dotenv()

# OpenRouter API Configuration
OPENROUTER_API_KEY = os.getenv("OPEN_ROUTER_API_KEY")
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
# Correct model identifier for GPT-OSS-20B (free version)
# MODEL_NAME = "openai/gpt-oss-20b:free"
MODEL_NAME = "openai/gpt-5.1"
# "google/gemini-flash-1.5-8b"
# "openai/gpt-oss-20b:free"

# Initialize the similarity checker globally (persists across function calls)
similarity_checker = SemanticSimilarityChecker(threshold=0.75)


def call_openrouter_api(prompt, max_tokens=400):
    """
    Call OpenRouter API to generate text using GPT-OSS-20B model.
    
    Args:
        prompt (str): The prompt to send to the model
        max_tokens (int): Maximum tokens in the response
        
    Returns:
        str: Generated text from the model, or None if error occurs
    """
    print("Calling prmopt", prompt)
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        # "HTTP-Referer": "https://github.com/your-repo",  # Optional
        # "X-Title": "Subheading Generator"  # Optional
    }
    
    payload = {
        "model": MODEL_NAME,
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ],
        "max_tokens": max_tokens,
        "temperature": 0.8  # Higher temperature for more variety
    }
    
    try:
        print(f"Calling API with model: {MODEL_NAME}")
        response = requests.post(OPENROUTER_API_URL, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        
        # Debug: Print the full response
        print(f"API Response Status: {response.status_code}")
        
        # Check if we have the expected structure
        if 'choices' not in data or len(data['choices']) == 0:
            print(f"Unexpected API response structure: {json.dumps(data, indent=2)}")
            return None
        
        message = data['choices'][0]['message']
        
        # For reasoning models, the content might be in 'content' or 'reasoning'
        generated_text = message.get('content', '').strip()
        print(">>>> Generated text:", generated_text)
        
        # If content is empty, try to get the last reasoning detail
        if not generated_text and 'reasoning_details' in message:
            reasoning_details = message['reasoning_details']
            if reasoning_details:
                # Get the last reasoning entry which should contain the answer
                generated_text = reasoning_details[-1].get('text', '').strip()
        
        # If still empty, try the reasoning field directly
        if not generated_text and 'reasoning' in message:
            generated_text = message['reasoning'].strip()
        
        if not generated_text:
            print(f"⚠️ API returned empty content. Full response: {json.dumps(data, indent=2)}")
            return None
            
        return generated_text
    
    except requests.exceptions.RequestException as e:
        print(f"API Error: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response Status: {e.response.status_code}")
            print(f"Response: {e.response.text}")
        return None
    except (KeyError, IndexError) as e:
        print(f"Error parsing response: {e}")
        print(f"Full response data: {json.dumps(data, indent=2)}")
        return None


def generate_prompt_subheading(base_prompt, max_attempts=10):
    """
    Generate a unique subheading from a base prompt.
    
    This function calls the GPT-OSS-20B model via OpenRouter to generate a subheading
    related to the base_prompt. It ensures the subheading is semantically unique by
    comparing it against previously generated subheadings using the similarity checker.
    If a similar subheading exists, it generates a new one (up to max_attempts).
    
    Args:
        base_prompt (str): The base topic (e.g., "Machine Learning")
        max_attempts (int): Maximum number of attempts to generate a unique subheading
        
    Returns:
        str: A unique subheading (max 10 words), or None if failed after max_attempts
    """
    print(f"\n{'='*70}")
    print(f"Generating subheading for: '{base_prompt}'")
    print(f"{'='*70}")
    
    # Build the prompt for the API
    api_prompt = f"""Choose a particular topic from the broader topic {base_prompt}. STRICTLY Output ONLY the topic and NOTHING else."""
    # """STRICTLY Output only the topic. Do NOT use special character. DO NOT write anything other than the topic.
    # Example: input 'write about Machine Learning', output 'create a video regarding Unsupervised Learning'."""
    
    for attempt in range(1, max_attempts + 1):
        print(f"\n🔄 Attempt {attempt}/{max_attempts}...")
        
        # Generate subheading using OpenRouter API
        generated_text = call_openrouter_api(api_prompt)
        
        if generated_text is None:
            print("⚠️  API call failed, retrying...")
            continue
        
        # Clean up the generated text
        subheading = generated_text.strip().strip('"').strip("'")
        
        # Check if we got an empty response
        if not subheading:
            print(f"⚠️ Received empty subheading from API, retrying...")
            continue
        
        # Check word count
        word_count = len(subheading.split())
        if word_count > 10:
            print(f"⚠️  Generated subheading too long ({word_count} words): '{subheading}'")
            print("    Truncating to 10 words...")
            subheading = ' '.join(subheading.split()[:10])
        
        print(f"📝 Generated: '{subheading}' ({len(subheading.split())} words)")
        
        # Check if similar to any stored subheading
        is_similar, score, similar_to = similarity_checker.is_similar_to_any_stored(subheading)
        
        if is_similar:
            print(f"❌ REJECTED - Too similar to: '{similar_to}'")
            print(f"   Similarity score: {score:.3f}")
            # Modify the prompt to avoid similar subheadings
            api_prompt += f"\n\nAvoid topics similar to: {similar_to}"
        else:
            # Unique subheading found!
            similarity_checker.add_subheading(subheading)
            print(f"✅ SUCCESS - Unique subheading generated!")
            print(f"📊 Total stored subheadings: {len(similarity_checker.get_stored_subheadings())}")
            return subheading
    
    # Max attempts reached
    print(f"\n❌ Failed to generate unique subheading after {max_attempts} attempts")
    return None


def get_all_stored_subheadings():
    """
    Get all stored subheadings.
    
    Returns:
        list: List of all unique subheadings generated so far
    """
    return similarity_checker.get_stored_subheadings()


def clear_all_subheadings():
    """
    Clear all stored subheadings. Useful for starting fresh.
    """
    similarity_checker.clear_stored_subheadings()


# Example usage and testing
if __name__ == "__main__":
    print("\n" + "="*70)
    print("SUBHEADING GENERATOR - DEMO")
    print("="*70)
    
    # Generate unique subheadings
    print("\nGenerating 3 unique subheadings for 'Machine Learning'...\n")
    
    subheading1 = generate_prompt_subheading("write about Artificial Intelligence")
    subheading2 = generate_prompt_subheading("write about Artificial Intelligence")
    subheading3 = generate_prompt_subheading("write about Artificial Intelligence")
    
    # Each call will generate a semantically unique subheading
    
    # Display final results
    print("\n" + "="*70)
    print("FINAL RESULTS")
    print("="*70)
    print("\nGenerated subheadings:\n")
    
    if subheading1:
        print(f"1. {subheading1}")
    if subheading2:
        print(f"2. {subheading2}")
    if subheading3:
        print(f"3. {subheading3}")
    
    print("\n" + "="*70)
    print("All stored subheadings in similarity checker:")
    print("="*70)
    for i, subheading in enumerate(get_all_stored_subheadings(), 1):
        print(f"{i}. {subheading}")