# GitHub Workflow Guide

## 🚀 First Time Setup (Current Device)

### 1. Install Git
Download and install: https://git-scm.com/download/win

### 2. Configure Git (First time only)
```bash
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"
```

### 3. Create GitHub Repository
1. Go to https://github.com
2. Click "+" → "New repository"
3. Name it (e.g., "mosque-dashboard")
4. Choose "Private" if you want it hidden
5. Don't initialize with README (we already have files)
6. Click "Create repository"

### 4. Push Your Code
```bash
# Navigate to your project
cd d:\energy

# Initialize git (if not done)
git init

# Add all files
git add .

# Commit
git commit -m "Initial commit - Mosque Dashboard"

# Add remote (replace with YOUR repository URL)
git remote add origin https://github.com/YOUR-USERNAME/mosque-dashboard.git

# Push to GitHub
git branch -M main
git push -u origin main
```

## 💻 Setup on Another Device

### 1. Install Git
Download from: https://git-scm.com/download

### 2. Clone the Repository
```bash
# Navigate to where you want the project
cd /path/to/your/projects

# Clone (replace with YOUR repository URL)
git clone https://github.com/YOUR-USERNAME/mosque-dashboard.git

# Enter the directory
cd mosque-dashboard
```

### 3. Setup Environment
```bash
# Install dependencies
pip install -r requirements.txt

# Create .env file
cd mosques
copy env.example .env    # Windows
# OR
cp env.example .env      # Mac/Linux

# Edit .env with your local paths
notepad .env             # Windows
# OR
nano .env               # Mac/Linux
```

### 4. Run the App
```bash
cd mosques
streamlit run app.py
```

## 🔄 Daily Workflow (After Setup)

### Before You Start Working:
```bash
# Get latest changes from GitHub
git pull
```

### After You Make Changes:
```bash
# See what you changed
git status

# Add all changes
git add .

# Commit with a message
git commit -m "Description of what you changed"

# Push to GitHub
git push
```

## 🆘 Common Scenarios

### Scenario 1: Working on Multiple Devices
**On Device A:**
```bash
# Make changes, then:
git add .
git commit -m "Added new feature"
git push
```

**On Device B:**
```bash
# Before starting work:
git pull

# Make changes, then:
git add .
git commit -m "Fixed bug"
git push
```

**Back on Device A:**
```bash
# Before starting again:
git pull  # Gets the changes from Device B
```

### Scenario 2: Check What Changed
```bash
# See what files changed
git status

# See exact changes in files
git diff

# See commit history
git log --oneline
```

### Scenario 3: Undo Mistakes
```bash
# Undo changes to a file (before commit)
git checkout -- filename.py

# Undo last commit (keeps changes)
git reset --soft HEAD~1

# Undo last commit (deletes changes - careful!)
git reset --hard HEAD~1
```

### Scenario 4: Conflicts
If you get a merge conflict:
```bash
# Pull changes
git pull

# Git will tell you which files have conflicts
# Open the files and look for:
# <<<<<<< HEAD
# your changes
# =======
# their changes
# >>>>>>> 

# Edit the file to keep what you want
# Then:
git add .
git commit -m "Resolved conflicts"
git push
```

## 📝 Best Practices

1. **Always `git pull` before starting work**
2. **Commit often** with clear messages
3. **Push regularly** (at least at end of day)
4. **Never commit sensitive data** (.env is already in .gitignore)
5. **Use descriptive commit messages**:
   - ✅ "Fixed map click bug and improved styling"
   - ❌ "updates"

## 🔐 Important Reminders

- `.env` file is in `.gitignore` - it will **NEVER** be pushed to GitHub
- `env.example` **WILL** be pushed - it's the template
- Each device needs its own `.env` file with local paths
- Data files (`.xlsx`, `.geojson`) **ARE** pushed by default
- Cache files (`.parquet`) are **NOT** pushed (in `.gitignore`)

## 🆘 Need Help?

### Check Git status:
```bash
git status
```

### See what's being tracked:
```bash
git ls-files
```

### Check if .env is ignored:
```bash
git check-ignore -v .env
# Should show: .gitignore:27:.env    .env
```

### GitHub Resources:
- Documentation: https://docs.github.com
- Git Cheat Sheet: https://education.github.com/git-cheat-sheet-education.pdf

