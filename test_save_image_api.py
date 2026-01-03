#!/usr/bin/env python3
"""
Test script to save an image through the API
Tests the full flow: upload image -> update post with image URL

Usage:
    python test_save_image_api.py <email> <password> [post_id]
    
Or set environment variables:
    TEST_EMAIL=your@email.com
    TEST_PASSWORD=yourpassword
    TEST_POST_ID=optional-post-id
"""
import requests
import base64
import sys
import os
import json
from io import BytesIO
from PIL import Image

def test_save_image_api(email=None, password=None, post_id=None):
    """Test saving an image through the API"""
    base_url = "http://127.0.0.1:8000/socialanywhere"
    
    print("Testing Image Save Through API")
    print("=" * 60)
    
    # Get credentials from args or env
    if not email:
        email = os.getenv("TEST_EMAIL") or (sys.argv[1] if len(sys.argv) > 1 else None)
    if not password:
        password = os.getenv("TEST_PASSWORD") or (sys.argv[2] if len(sys.argv) > 2 else None)
    if not post_id:
        post_id = os.getenv("TEST_POST_ID") or (sys.argv[3] if len(sys.argv) > 3 else None)
    
    if not email or not password:
        print("❌ Error: Email and password required")
        print("\nUsage:")
        print("  python test_save_image_api.py <email> <password> [post_id]")
        print("\nOr set environment variables:")
        print("  TEST_EMAIL=your@email.com")
        print("  TEST_PASSWORD=yourpassword")
        print("  TEST_POST_ID=optional-post-id")
        return
    
    # Step 1: Get authentication token
    print("\nStep 1: Getting authentication token...")
    print("-" * 60)
    
    try:
        login_response = requests.post(
            f"{base_url}/auth/login",
            json={"email": email, "password": password}
        )
        
        if login_response.status_code != 200:
            print(f"❌ Login failed: {login_response.status_code}")
            print(f"Response: {login_response.text}")
            return
        
        login_data = login_response.json()
        token = login_data.get("access_token")
        
        if not token:
            print("❌ No token received from login")
            print(f"Response: {login_data}")
            return
        
        print(f"✅ Login successful")
        print(f"Token: {token[:50]}...")
        
    except Exception as e:
        print(f"❌ Login error: {e}")
        import traceback
        traceback.print_exc()
        return
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # Step 2: Get a post ID to update (if not provided)
    if not post_id:
        print("\nStep 2: Getting a post to update...")
        print("-" * 60)
        
        try:
            posts_response = requests.get(
                f"{base_url}/api/posts?limit=5",
                headers=headers
            )
            
            if posts_response.status_code != 200:
                print(f"❌ Failed to get posts: {posts_response.status_code}")
                print(f"Response: {posts_response.text}")
                return
            
            posts_data = posts_response.json()
            posts = posts_data.get("posts", [])
            
            if not posts:
                print("❌ No posts found. Please create a post first.")
                return
            
            post = posts[0]
            post_id = post.get("id")
            print(f"✅ Found post: {post_id}")
            print(f"   Current image_url: {post.get('image_url', 'None')}")
            print(f"   Current image_path: {post.get('image_path', 'None')}")
            
        except Exception as e:
            print(f"❌ Error getting posts: {e}")
            import traceback
            traceback.print_exc()
            return
    else:
        print(f"\nStep 2: Using provided post ID: {post_id}")
        print("-" * 60)
    
    # Step 3: Create a test image
    print("\nStep 3: Creating test image...")
    print("-" * 60)
    
    try:
        # Create a simple test image with text
        img = Image.new('RGB', (400, 300), color=(147, 51, 234))  # Purple color
        img_bytes = BytesIO()
        img.save(img_bytes, format='PNG')
        img_bytes.seek(0)
        
        # Convert to base64 data URL
        img_data = img_bytes.read()
        img_base64 = base64.b64encode(img_data).decode('utf-8')
        data_url = f"data:image/png;base64,{img_base64}"
        
        print(f"✅ Created test image (400x300, purple)")
        print(f"   Data URL length: {len(data_url)} characters")
        
    except Exception as e:
        print(f"❌ Error creating image: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Step 4: Upload the image
    print("\nStep 4: Uploading image...")
    print("-" * 60)
    
    try:
        upload_response = requests.post(
            f"{base_url}/upload-custom-image",
            headers=headers,
            json={
                "data_url": data_url,
                "description": "Test image upload via API"
            }
        )
        
        print(f"Upload Status: {upload_response.status_code}")
        
        if upload_response.status_code != 200:
            print(f"❌ Upload failed: {upload_response.status_code}")
            print(f"Response: {upload_response.text}")
            return
        
        upload_data = upload_response.json()
        print(f"Upload Response: {json.dumps(upload_data, indent=2)}")
        
        if not upload_data.get("success"):
            print(f"❌ Upload unsuccessful: {upload_data.get('error', 'Unknown error')}")
            return
        
        image_url = upload_data.get("image_url") or upload_data.get("url") or upload_data.get("image_path")
        
        if not image_url:
            print(f"❌ No image URL in response")
            print(f"Response: {upload_data}")
            return
        
        print(f"✅ Image uploaded successfully")
        print(f"   Image URL: {image_url}")
        print(f"   Image Path: {upload_data.get('image_path', 'N/A')}")
        print(f"   Filename: {upload_data.get('filename', 'N/A')}")
        
    except Exception as e:
        print(f"❌ Upload error: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Step 5: Update the post with the image URL
    print("\nStep 5: Updating post with image URL...")
    print("-" * 60)
    
    try:
        update_payload = {
            "image_url": image_url
        }
        
        print(f"Update Payload: {json.dumps(update_payload, indent=2)}")
        
        update_response = requests.put(
            f"{base_url}/api/posts/{post_id}",
            headers=headers,
            json=update_payload
        )
        
        print(f"Update Status: {update_response.status_code}")
        
        if update_response.status_code != 200:
            print(f"❌ Update failed: {update_response.status_code}")
            print(f"Response: {update_response.text}")
            return
        
        update_data = update_response.json()
        print(f"Update Response: {json.dumps(update_data, indent=2)}")
        
        if not update_data.get("success"):
            print(f"❌ Update unsuccessful: {update_data.get('error', 'Unknown error')}")
            if update_data.get("traceback"):
                print(f"\nTraceback:\n{update_data.get('traceback')}")
            return
        
        updated_post = update_data.get("post", {})
        
        if updated_post:
            print(f"✅ Post updated successfully")
            print(f"   Updated image_url: {updated_post.get('image_url', 'None')}")
            print(f"   Updated image_path: {updated_post.get('image_path', 'None')}")
            print(f"   Post ID: {updated_post.get('id', 'N/A')}")
            print(f"   Status: {updated_post.get('status', 'N/A')}")
            
            # Verify the image URL is set
            if updated_post.get('image_url') == image_url:
                print(f"\n✅ SUCCESS! Image URL matches uploaded image")
            else:
                print(f"\n⚠️ WARNING: Image URL doesn't match")
                print(f"   Expected: {image_url}")
                print(f"   Got: {updated_post.get('image_url')}")
        else:
            print(f"⚠️ Update response doesn't contain post data")
            print(f"   Response: {update_data}")
        
    except Exception as e:
        print(f"❌ Update error: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Step 6: Verify by fetching the post again
    print("\nStep 6: Verifying update by fetching post...")
    print("-" * 60)
    
    try:
        verify_response = requests.get(
            f"{base_url}/api/posts/{post_id}",
            headers=headers
        )
        
        if verify_response.status_code == 200:
            verify_data = verify_response.json()
            verified_post = verify_data.get("post", verify_data)
            
            print(f"✅ Post fetched successfully")
            print(f"   Verified image_url: {verified_post.get('image_url', 'None')}")
            print(f"   Verified image_path: {verified_post.get('image_path', 'None')}")
            
            if verified_post.get('image_url') == image_url:
                print(f"\n✅ VERIFICATION SUCCESSFUL! Image is saved correctly.")
            else:
                print(f"\n⚠️ VERIFICATION WARNING: Image URL mismatch")
                print(f"   Expected: {image_url}")
                print(f"   Got: {verified_post.get('image_url')}")
        else:
            print(f"⚠️ Could not verify (status {verify_response.status_code})")
            print(f"Response: {verify_response.text}")
            
    except Exception as e:
        print(f"⚠️ Verification error: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("Test completed!")

if __name__ == "__main__":
    test_save_image_api()
