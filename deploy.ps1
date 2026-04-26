# ImagiText AI Auto-Deploy Script

$githubUser = Read-Host "Please enter your GitHub Username"
$repoName = "ImagiText-AI"

Write-Host "🚀 Preparing your app for GitHub..." -ForegroundColor Cyan

# Ensure git is initialized
if (!(Test-Path .git)) {
    git init
}

# Add all files
git add .

# Commit changes
git commit -m "Final production version of ImagiText AI"

# Check if origin already exists
$remoteExists = git remote | Select-String "origin"
if ($remoteExists) {
    git remote remove origin
}

# Add the remote URL
git remote add origin "https://github.com/$githubUser/$repoName.git"

Write-Host "📤 Uploading to GitHub..." -ForegroundColor Yellow
git branch -M main
git push -u origin main -f

Write-Host "✅ Done! Your code is now on GitHub." -ForegroundColor Green
Write-Host "Next step: Go to Vercel.com and import this repository!" -ForegroundColor Cyan
