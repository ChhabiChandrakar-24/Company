# Git upload और deployment

इस repository में दो deployable हिस्से हैं:

- `backend-website`: Django HRMS, API और public website एक साथ। `website` अकेले नहीं चल सकती क्योंकि वह Django settings, database और shared static files पर निर्भर है।
- `mobile`: React Native Android/iOS app।

`mobile` का अपना Git repository है और root repository उसे submodule की तरह
reference करती है। Root clone करते समय पूरा mobile source पाने के लिए:

```powershell
git clone --recurse-submodules https://github.com/ChhabiChandrakar-24/horilla.git
```

पहले से clone किया हो तो `git submodule update --init --recursive` चलाएँ।

अलग upload-ready folders बनाने के लिए repository root से चलाएँ:

```powershell
powershell -ExecutionPolicy Bypass -File .\deploy\package-git.ps1
```

Folders `artifacts/git-upload/` में बनेंगे। यह directory जानबूझकर `.gitignore` में है ताकि duplicate source current repository में commit न हो। दोनों generated folders को अलग Git repositories में upload किया जा सकता है।

## Login और local run

Local database में active usernames `admin`, `hr`, `manager` और `employee` हैं। Password database में one-way hash के रूप में रहता है, इसलिए उसे पढ़ा नहीं जा सकता। भूलने पर नया password बनाएँ:

```powershell
.\.venv\Scripts\python.exe manage.py changepassword admin
```

Port 8000 किसी और application द्वारा इस्तेमाल हो तो backend ऐसे चलाएँ:

```powershell
.\.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8001
```

फिर `http://127.0.0.1:8001/login/` खोलें। Mobile का `src/config.ts` backend के वास्तविक port/domain से match होना चाहिए।

## Design deploy के बाद क्यों बिगड़ता है

Source CSS/JS/images `static/` में Git-tracked हैं। Production server पर हर release में ये commands जरूरी हैं:

```bash
python manage.py migrate --noinput
python manage.py collectstatic --noinput
```

Web server को `/static/` से generated `staticfiles/` serve करना होगा। Repository का AWS Nginx config इसका उदाहरण देता है।

CMS से upload किए logo, favicon और section images `media/` में रहते हैं। इनमें private/user data हो सकता है, इसलिए `media/` public Git package में शामिल नहीं होता। इन्हें private S3/object storage या server backup से restore करें और `/media/` URL configure करें। Media restore किए बिना custom branding missing दिख सकती है, हालांकि default website assets उपलब्ध रहेंगे।

कभी भी `.env`, database dump, signing key, logs या employee media Git पर upload न करें। Production में `.env.dist` की copy बनाकर secrets server पर भरें।
