import discord
from discord.ext import commands
from dotenv import load_dotenv
import os
import requests
import random
from supabase import create_client
import headFinder
import json
import re


load_dotenv()

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
with open("character_sets.json") as f:
      character_sets = json.load(f)

bot = commands.Bot(command_prefix="!", intents=intents)

supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_STORAGE_SECRET_KEY"))

def find_character(sentence):
    #if anything in the word has a keyword, we return that character.
    for character, keywords in character_sets.items():
        if any(keyword in sentence for keyword in keywords ):
            return character
    return None

@bot.event
async def on_message(message):
    if message.author.bot:
        return  # ignore other bots
    character = find_character(message.content.lower())
    if character is not None:
        """
        if you say potential you get agenda'd
        """
        async with message.channel.typing():
            profilePicKey,profileID = await uploadProfilePicture(message)
            #get all IDs fr that character
            
            result = supabase.table("ImagesLocation").select("id",'imageKey').eq("character",character).execute()

            #get a random image key 
            randomRow = random.choice(result.data)
            slanderImageKey = randomRow["imageKey"]
            slanderImageID = randomRow["id"]
            slanderImageURL,profilePicURL = await keyToURL(slanderImageKey,profilePicKey)

            #process image, send image
            finalImageBytes = headFinder.processImage(slanderImageURL,profilePicURL,character)
            #put final image on supabase storage
            finalURL = await sendImage(finalImageBytes,profileID,slanderImageID)

            await message.channel.send(finalURL)

    await bot.process_commands(message)  # still allow !commands to work

async def keyToURL(slanderImageKey, profilePicKey) -> list[str]:
    """
     gets slanderimage key and profile picture key, puts on s3, and returns the url for it

    """
    signedSlanderObject = supabase.storage.from_("slander-stuff").create_signed_url(f"images/{slanderImageKey}",120)
    slanderImageURL = signedSlanderObject["signedUrl"]
    signedProfileObject = supabase.storage.from_("slander-stuff").create_signed_url(f"profilePics/{profilePicKey}",120)
    profilePicURL = signedProfileObject["signedUrl"]
    return [slanderImageURL,profilePicURL]

async def uploadProfilePicture(message):
    """
    uploads account profile data + picture to slander
    """
    user = message.author
    print(message.content,user.name,user.display_avatar.url)
    #chck if profile with same picture already there 
    exisitingKey = supabase.table("profiles").select("profileKey").eq("profileURL", user.display_avatar.url).execute()
    if exisitingKey.data:
        profilePicKey = exisitingKey.data[0]["profileKey"]
    else:
        profilePicKey = None  # will be set after insert
    #get picture
    
    #add profile to table
    result = supabase.table("profiles").upsert({"profileName": user.name, "accountID": str(user.id), "profileURL":
    user.display_avatar.url}, on_conflict="accountID").execute()
    profileID = result.data[0]["id"]

    #profile picture not uploaded 
    if profilePicKey is None:
        #need to upload image 
        profilePicKey = result.data[0]["profileKey"]
        profilePicture = requests.get(user.display_avatar.url)
        profilePicBytes = profilePicture.content
        supabase.storage.from_("slander-stuff").upload(f"profilePics/{profilePicKey}", profilePicBytes, {"content-type":
  "image/jpeg"})

    return profilePicKey,profileID


async def sendImage(finalImageBytes,profileID,slanderImageID):  
    """
    puts final image into s3 and logs it. returns url to view it
    """
    #register in database
    result = supabase.table("finalResults").insert({"profileID": profileID,"imageID":slanderImageID}).execute()
    finalResultKey = result.data[0]["finalResultKey"]
    #upload to S3
    supabase.storage.from_("slander-results").upload(
      f"slanderImages/{finalResultKey}",
      finalImageBytes,
      {"content-type": "image/jpeg"}
    )
    url = supabase.storage.from_("slander-results").get_public_url(f"slanderImages/{finalResultKey}")
    return url

bot.run(os.getenv("DISCORD_BOT_TOKEN"))


