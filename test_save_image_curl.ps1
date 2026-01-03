# PowerShell script to test saving an image through the API
# Usage: .\test_save_image_curl.ps1 <token> [post_id]

param(
    [Parameter(Mandatory=$true)]
    [string]$Token,
    
    [Parameter(Mandatory=$false)]
    [string]$PostId = ""
)

$baseUrl = "http://127.0.0.1:8000/socialanywhere"

Write-Host "Testing Image Save Through API" -ForegroundColor Cyan
Write-Host "=" * 60
Write-Host ""

# Step 1: Get post ID if not provided
if (-not $PostId) {
    Write-Host "Step 1: Getting a post to update..." -ForegroundColor Yellow
    Write-Host "-" * 60
    
    try {
        $headers = @{
            "Authorization" = "Bearer $Token"
        }
        
        $postsResponse = Invoke-RestMethod -Uri "$baseUrl/api/posts?limit=5" -Method GET -Headers $headers
        $posts = $postsResponse.posts
        
        if (-not $posts -or $posts.Count -eq 0) {
            Write-Host "❌ No posts found. Please create a post first." -ForegroundColor Red
            exit 1
        }
        
        $PostId = $posts[0].id
        Write-Host "✅ Found post: $PostId" -ForegroundColor Green
        Write-Host "   Current image_url: $($posts[0].image_url)" -ForegroundColor Cyan
    } catch {
        Write-Host "❌ Error getting posts: $($_.Exception.Message)" -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "Step 1: Using provided post ID: $PostId" -ForegroundColor Yellow
    Write-Host "-" * 60
}

# Step 2: Create a test image (base64 encoded 1x1 PNG)
Write-Host ""
Write-Host "Step 2: Creating test image..." -ForegroundColor Yellow
Write-Host "-" * 60

# Minimal PNG image (1x1 purple pixel)
$pngBase64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
$dataUrl = "data:image/png;base64,$pngBase64"

Write-Host "✅ Created test image (base64 encoded)" -ForegroundColor Green

# Step 3: Upload the image
Write-Host ""
Write-Host "Step 3: Uploading image..." -ForegroundColor Yellow
Write-Host "-" * 60

try {
    $headers = @{
        "Authorization" = "Bearer $Token"
        "Content-Type" = "application/json"
    }
    
    $uploadBody = @{
        data_url = $dataUrl
        description = "Test image upload via API"
    } | ConvertTo-Json
    
    $uploadResponse = Invoke-RestMethod -Uri "$baseUrl/upload-custom-image" `
        -Method POST `
        -Headers $headers `
        -Body $uploadBody
    
    if (-not $uploadResponse.success) {
        Write-Host "❌ Upload failed: $($uploadResponse.error)" -ForegroundColor Red
        exit 1
    }
    
    $imageUrl = $uploadResponse.image_url
    if (-not $imageUrl) {
        $imageUrl = $uploadResponse.url
    }
    if (-not $imageUrl) {
        $imageUrl = $uploadResponse.image_path
    }
    
    if (-not $imageUrl) {
        Write-Host "❌ No image URL in response" -ForegroundColor Red
        Write-Host "Response: $($uploadResponse | ConvertTo-Json)" -ForegroundColor Yellow
        exit 1
    }
    
    Write-Host "✅ Image uploaded successfully" -ForegroundColor Green
    Write-Host "   Image URL: $imageUrl" -ForegroundColor Cyan
    Write-Host "   Image Path: $($uploadResponse.image_path)" -ForegroundColor Cyan
    
} catch {
    Write-Host "❌ Upload error: $($_.Exception.Message)" -ForegroundColor Red
    if ($_.ErrorDetails) {
        Write-Host "Details: $($_.ErrorDetails.Message)" -ForegroundColor Yellow
    }
    exit 1
}

# Step 4: Update the post with the image URL
Write-Host ""
Write-Host "Step 4: Updating post with image URL..." -ForegroundColor Yellow
Write-Host "-" * 60

try {
    $updateBody = @{
        image_url = $imageUrl
    } | ConvertTo-Json
    
    Write-Host "Update Payload: $updateBody" -ForegroundColor Gray
    
    $updateResponse = Invoke-RestMethod -Uri "$baseUrl/api/posts/$PostId" `
        -Method PUT `
        -Headers $headers `
        -Body $updateBody
    
    if (-not $updateResponse.success) {
        Write-Host "❌ Update failed: $($updateResponse.error)" -ForegroundColor Red
        if ($updateResponse.traceback) {
            Write-Host "Traceback: $($updateResponse.traceback)" -ForegroundColor Yellow
        }
        exit 1
    }
    
    $updatedPost = $updateResponse.post
    
    if ($updatedPost) {
        Write-Host "✅ Post updated successfully" -ForegroundColor Green
        Write-Host "   Updated image_url: $($updatedPost.image_url)" -ForegroundColor Cyan
        Write-Host "   Updated image_path: $($updatedPost.image_path)" -ForegroundColor Cyan
        Write-Host "   Post ID: $($updatedPost.id)" -ForegroundColor Cyan
        Write-Host "   Status: $($updatedPost.status)" -ForegroundColor Cyan
        
        if ($updatedPost.image_url -eq $imageUrl) {
            Write-Host ""
            Write-Host "✅ SUCCESS! Image URL matches uploaded image" -ForegroundColor Green
        } else {
            Write-Host ""
            Write-Host "⚠️ WARNING: Image URL doesn't match" -ForegroundColor Yellow
            Write-Host "   Expected: $imageUrl" -ForegroundColor Gray
            Write-Host "   Got: $($updatedPost.image_url)" -ForegroundColor Gray
        }
    } else {
        Write-Host "⚠️ Update response doesn't contain post data" -ForegroundColor Yellow
        Write-Host "Response: $($updateResponse | ConvertTo-Json)" -ForegroundColor Gray
    }
    
} catch {
    Write-Host "❌ Update error: $($_.Exception.Message)" -ForegroundColor Red
    if ($_.ErrorDetails) {
        Write-Host "Details: $($_.ErrorDetails.Message)" -ForegroundColor Yellow
    }
    exit 1
}

# Step 5: Verify by fetching the post
Write-Host ""
Write-Host "Step 5: Verifying update..." -ForegroundColor Yellow
Write-Host "-" * 60

try {
    $verifyResponse = Invoke-RestMethod -Uri "$baseUrl/api/posts/$PostId" `
        -Method GET `
        -Headers $headers
    
    $verifiedPost = $verifyResponse.post
    if (-not $verifiedPost) {
        $verifiedPost = $verifyResponse
    }
    
    Write-Host "✅ Post fetched successfully" -ForegroundColor Green
    Write-Host "   Verified image_url: $($verifiedPost.image_url)" -ForegroundColor Cyan
    Write-Host "   Verified image_path: $($verifiedPost.image_path)" -ForegroundColor Cyan
    
    if ($verifiedPost.image_url -eq $imageUrl) {
        Write-Host ""
        Write-Host "✅ VERIFICATION SUCCESSFUL! Image is saved correctly." -ForegroundColor Green
    } else {
        Write-Host ""
        Write-Host "⚠️ VERIFICATION WARNING: Image URL mismatch" -ForegroundColor Yellow
    }
    
} catch {
    Write-Host "⚠️ Verification error: $($_.Exception.Message)" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "=" * 60
Write-Host "Test completed!" -ForegroundColor Green

