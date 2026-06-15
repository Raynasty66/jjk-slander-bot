# JJK Slander Bot

A Discord bot that detects Jujutsu Kaisen character keywords in messages and responds with a slander meme — placing the sender's profile picture over the matched character's face using anime face detection and a JJK character classifier.

## How It Works

1. A user sends a message containing a keyword tied to a JJK character (e.g. "potential" → Fushiguro Megumi)
2. The bot fetches a random slander image for that character from Supabase
3. An anime face detector (YOLOv8) locates the character's face in the image
4. A ViT-based classifier confirms the face belongs to the correct character
5. The user's Discord profile picture is cropped into a circle and pasted over the face
6. The final image is uploaded to Supabase and sent back in the channel

## Running the Bot

```bash
pip install -r requirements.txt
python discordBot.py
```

That's it. Make sure your `.env` is configured (see below) and your `weights/` folder is populated before running.

## Setup

### 1. Environment Variables

Copy `.env.example` to `.env` and fill in your values:

```
DISCORD_BOT_TOKEN=your Discord bot token
SUPABASE_URL=your Supabase project URL
SUPABASE_STORAGE_SECRET_KEY=your Supabase service role key (not the anon key)
```

### 2. Supabase Storage Buckets

Create the following two buckets in your Supabase project under **Storage**:

| Bucket | Public | Purpose |
|--------|--------|---------|
| `slander-stuff` | No | Stores source slander images (`images/`) and user profile pictures (`profilePics/`) |
| `slander-results` | Yes | Stores final generated slander images (`slanderImages/`) |

### 3. Supabase Database Tables

Create the following tables under **Table Editor**:

#### `ImagesLocation`
| Column | Type | Notes |
|--------|------|-------|
| `id` | int8 | primary key, auto-increment |
| `imageKey` | uuid | default `gen_random_uuid()` |
| `character` | text | JJK character name |
| `imageURL` | text | source image URL |
| `postID` | text | Reddit post ID (optional) |
| `postName` | text | Reddit post title (optional) |

#### `profiles`
| Column | Type | Notes |
|--------|------|-------|
| `id` | int8 | primary key, auto-increment |
| `profileKey` | uuid | default `gen_random_uuid()` |
| `profileName` | text | Discord username |
| `accountID` | text | Discord user ID (unique) |
| `profileURL` | text | Discord avatar URL |

#### `finalResults`
| Column | Type | Notes |
|--------|------|-------|
| `id` | int8 | primary key, auto-increment |
| `finalResultKey` | uuid | default `gen_random_uuid()` |
| `profileID` | int8 | foreign key → `profiles.id` |
| `imageID` | int8 | foreign key → `ImagesLocation.id` |

### 4. Model Weights

Place the following files in a `weights/` folder:

- `jjk_classifier.ckpt` — ViT-based JJK character classifier checkpoint
- `classid_classname.csv` — maps class IDs to character names

The anime face detector (`yolov8x6_animeface.pt`) is downloaded automatically from GitHub on first run.

### 5. Uploading Slander Images

Use `upload_megumi.py` as a reference script for uploading slander images to the `ImagesLocation` table and `slander-stuff` bucket. Set the `CHARACTER` field to match the exact name used in `character_sets.json`.
